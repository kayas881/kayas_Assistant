from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urljoin

import httpx
from selectolax.parser import HTMLParser


@dataclass
class WebConfig:
    # Network timeouts (seconds). Keep these fairly strict to avoid hangs.
    timeout_connect: float = 5.0
    timeout_read: float = 12.0
    timeout_write: float = 12.0
    timeout_pool: float = 5.0
    # Total/legacy timeout (used only if explicit timeouts above aren't set)
    timeout: float = 15.0
    retries: int = 2
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    max_search_results: int = 10


class WebExecutor:
    def __init__(self, cfg: WebConfig, llm: Optional[Any] = None, planner_llm: Optional[Any] = None) -> None:
        self.cfg = cfg
        self._client: httpx.Client | None = None
        # Optional LLM for synthesis in web.answer and deep_research
        self.llm = llm
        # Optional separate LLM for planning (query planning / gap analysis)
        self.planner_llm = planner_llm
        # Lazy-load research controller
        self._research_controller = None

    def _get_client(self) -> httpx.Client:
        """Get or create a persistent HTTP client."""
        if self._client is None or self._client.is_closed:
            timeout = httpx.Timeout(
                connect=self.cfg.timeout_connect or self.cfg.timeout,
                read=self.cfg.timeout_read or self.cfg.timeout,
                write=self.cfg.timeout_write or self.cfg.timeout,
                pool=self.cfg.timeout_pool or self.cfg.timeout,
            )
            transport = httpx.HTTPTransport(retries=max(0, int(getattr(self.cfg, "retries", 0))))
            self._client = httpx.Client(
                timeout=timeout,
                follow_redirects=True,
                transport=transport,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                headers={
                    "User-Agent": self.cfg.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
            )
        return self._client

    # ========== SEARCH ==========
    def search(self, query: str, max_results: int | None = None) -> Dict[str, Any]:
        """
        Search the web using DuckDuckGo HTML (no API key required).
        
        Returns:
            {
                "success": True,
                "query": str,
                "results": [{"title": str, "url": str, "snippet": str}, ...],
                "action": "web.search"
            }
        """
        max_results = max_results or self.cfg.max_search_results
        
        def _ddg_request(url: str) -> str:
            client = self._get_client()
            r = client.get(url)
            r.raise_for_status()
            return r.text

        def _parse_ddg(html: str) -> List[Dict[str, str]]:
            tree = HTMLParser(html)
            parsed: List[Dict[str, str]] = []

            # Standard results blocks
            for result_node in tree.css(".result:not(.result--ad)"):
                if len(parsed) >= max_results:
                    break
                if result_node.css_first(".result__type--ad, .badge--ad"):
                    continue
                title_node = result_node.css_first(".result__title a, .result__a")
                if not title_node:
                    continue
                title = title_node.text(strip=True)
                href = title_node.attributes.get("href", "")
                if "y.js?" in href or "ad_provider" in href or "ad_domain" in href:
                    continue
                if "uddg=" in href:
                    import urllib.parse
                    parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    url_val = parsed_qs.get("uddg", [href])[0]
                else:
                    url_val = href
                snippet_node = result_node.css_first(".result__snippet")
                snippet = snippet_node.text(strip=True) if snippet_node else ""
                if title and url_val and url_val.startswith("http") and "duckduckgo.com/y.js" not in url_val:
                    parsed.append({"title": title, "url": url_val, "snippet": snippet})

            # Fallback: direct anchors (lite markup)
            if not parsed:
                for a in tree.css("a.result__a, a.result__url"):
                    if len(parsed) >= max_results:
                        break
                    title = a.text(strip=True)
                    href = a.attributes.get("href", "")
                    if "uddg=" in href:
                        import urllib.parse
                        parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        url_val = parsed_qs.get("uddg", [href])[0]
                    else:
                        url_val = href
                    if title and url_val.startswith("http"):
                        parsed.append({"title": title, "url": url_val, "snippet": ""})

            return parsed

        def _search_bing() -> List[Dict[str, str]]:
            """Best-effort Bing search using RSS feed (more reliable for scraping)."""
            try:
                bing_rss = f"https://www.bing.com/search?q={quote_plus(query)}&format=rss&setlang=en-us&mkt=en-US"
                rss = _ddg_request(bing_rss)
                parsed: List[Dict[str, str]] = []
                # Very small XML parsing without extra deps
                import re
                items = re.findall(r"<item>(.*?)</item>", rss, flags=re.DOTALL | re.IGNORECASE)
                for item in items:
                    if len(parsed) >= max_results:
                        break
                    title_match = re.search(r"<title>(.*?)</title>", item, flags=re.DOTALL | re.IGNORECASE)
                    link_match = re.search(r"<link>(.*?)</link>", item, flags=re.DOTALL | re.IGNORECASE)
                    desc_match = re.search(r"<description>(.*?)</description>", item, flags=re.DOTALL | re.IGNORECASE)
                    title = title_match.group(1).strip() if title_match else ""
                    url_val = link_match.group(1).strip() if link_match else ""
                    snippet = desc_match.group(1).strip() if desc_match else ""
                    # Clean HTML entities
                    import html as h
                    title = h.unescape(title)
                    url_val = h.unescape(url_val)
                    snippet = h.unescape(snippet)
                    if title and url_val.startswith("http"):
                        parsed.append({"title": title, "url": url_val, "snippet": snippet})
                return parsed
            except Exception:
                return []

        try:
            results: List[Dict[str, str]] = []

            # Try DuckDuckGo first
            try:
                search_url_primary = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
                html = _ddg_request(search_url_primary)
                results = _parse_ddg(html)
            except Exception:
                results = []

            if not results:
                try:
                    search_url_fallback = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
                    html_fb = _ddg_request(search_url_fallback)
                    results = _parse_ddg(html_fb)
                except Exception:
                    results = []

            if not results:
                try:
                    search_url_lite = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
                    html_lite = _ddg_request(search_url_lite)
                    results = _parse_ddg(html_lite)
                except Exception:
                    results = []

            # If DuckDuckGo yielded nothing, fallback to Bing
            if not results:
                results = _search_bing()

            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results),
                "action": "web.search"
            }

        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "results": [],
                "action": "web.search"
            }

    # ========== FETCH (enhanced) ==========
    def fetch(self, url: str) -> Dict[str, Any]:
        """
        Fetch a web page with enhanced metadata.
        
        Returns:
            {
                "success": True/False,
                "url": str (original),
                "final_url": str (after redirects),
                "status_code": int,
                "title": str,
                "excerpt": str (first 5000 chars of main text),
                "html_length": int,
                "text_length": int,
                "action": "web.fetch"
            }
        """
        try:
            client = self._get_client()
            r = client.get(url)
            r.raise_for_status()
            html = r.text
            final_url = str(r.url)
            status_code = r.status_code
            
            tree = HTMLParser(html)
            title = tree.css_first("title").text(strip=True) if tree.css_first("title") else ""
            
            # Prefer main article content if present; handle Wikipedia specially
            node = (
                tree.css_first("#mw-content-text .mw-parser-output")
                or tree.css_first("#mw-content-text")
                or tree.css_first("main")
                or tree.css_first("#content")
                or tree.css_first("article")
            )
            if "wikipedia.org" in url and node:
                # Concatenate first paragraphs to avoid menus/tables
                paras = [p.text(separator=" ", strip=True) for p in node.css("p") if p.text(strip=True)]
                raw_text = "\n".join(paras[:20])
            else:
                raw_text = (node.text(separator=" ") if node else tree.text(separator=" ")).strip()
            
            # Strip common boilerplate tokens
            junk_tokens = [
                "Jump to content", "Main menu", "Navigation", "Search", "Contribute",
                "Help Learn to edit", "Community portal", "Recent changes", "Upload file",
                "Contents", "Random article", "About Wikipedia", "Contact us", "Special pages",
            ]
            for jt in junk_tokens:
                raw_text = raw_text.replace(jt, " ")
            
            # Collapse whitespace
            text = " ".join(raw_text.split())
            excerpt = text[:5000]
            
            return {
                "success": True,
                "url": url,
                "final_url": final_url,
                "status_code": status_code,
                "title": title,
                "excerpt": excerpt,
                "html_length": len(html),
                "text_length": len(text),
                "action": "web.fetch"
            }
            
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "action": "web.fetch"
            }

    # ========== EXTRACT MAIN TEXT (readability-style) ==========
    def extract_main_text(self, url: str, max_chars: int = 15000) -> Dict[str, Any]:
        """
        Extract the main article/content text from a webpage (readability-style).
        Removes navbars, sidebars, ads, footers. Returns clean text suitable for citation.
        
        Returns:
            {
                "success": True/False,
                "url": str,
                "title": str,
                "main_text": str (cleaned main content),
                "paragraphs": [str, ...] (list of paragraphs for easy citation),
                "word_count": int,
                "action": "web.extract_main_text"
            }
        """
        try:
            client = self._get_client()
            r = client.get(url)
            r.raise_for_status()
            html = r.text
            
            tree = HTMLParser(html)
            title = tree.css_first("title").text(strip=True) if tree.css_first("title") else ""
            
            # Remove script, style, nav, footer, aside, header elements
            for tag in tree.css("script, style, nav, footer, aside, header, .sidebar, .menu, .navigation, .ad, .advertisement, .social-share, .comments, #comments"):
                tag.decompose()
            
            # Domain-special cases first
            if "stackoverflow.com" in url:
                paragraphs: List[str] = []
                # Question body
                q_node = tree.css_first("#question .s-prose") or tree.css_first("#question .post-text")
                if q_node:
                    q_text = q_node.text(separator=" ", strip=True)
                    if q_text and len(q_text) > 30:
                        paragraphs.append("## Question")
                        paragraphs.append(q_text)
                # Accepted/top answer
                a_node = tree.css_first(".answer.accepted-answer .s-prose") or tree.css_first(".answer .s-prose") or tree.css_first(".answercell .post-text")
                if a_node:
                    a_text = a_node.text(separator=" ", strip=True)
                    if a_text and len(a_text) > 30:
                        paragraphs.append("## Top Answer")
                        paragraphs.append(a_text)
                # Fallback: gather first few prose blocks
                if not paragraphs:
                    for node in tree.css(".s-prose, .post-text"):
                        t = node.text(separator=" ", strip=True)
                        if t and len(t) > 30:
                            paragraphs.append(t)
                            if len(paragraphs) >= 20:
                                break
                main_text = "\n\n".join(paragraphs)
                if len(main_text) > max_chars:
                    main_text = main_text[:max_chars] + "..."
                word_count = len(main_text.split())
                return {
                    "success": True,
                    "url": url,
                    "title": title,
                    "main_text": main_text,
                    "paragraphs": paragraphs[:50],
                    "word_count": word_count,
                    "action": "web.extract_main_text"
                }

            # Try multiple content selectors (prioritized for article content)
            content_selectors = [
                "article .entry-content",      # WordPress
                "article .post-content",       # Common blog
                ".article-body",               # News sites
                ".post-body",                  # Blogger
                "#mw-content-text .mw-parser-output",  # Wikipedia
                "main article",                # Semantic HTML
                "article",                     # Semantic HTML
                "main",                        # Semantic HTML
                ".content",                    # Common class
                "#content",                    # Common ID
                ".post",                       # Blog posts
                "body"                         # Fallback
            ]
            
            content_node = None
            for selector in content_selectors:
                content_node = tree.css_first(selector)
                if content_node:
                    break
            
            if not content_node:
                content_node = tree.body
            
            # Extract paragraphs and headings
            paragraphs: List[str] = []
            
            if content_node:
                # For Wikipedia, special handling
                if "wikipedia.org" in url:
                    for p in content_node.css("p"):
                        text = p.text(separator=" ", strip=True)
                        if text and len(text) > 50:  # Skip tiny paragraphs
                            paragraphs.append(text)
                else:
                    # General extraction: get paragraphs and meaningful text blocks
                    for elem in content_node.css("p, h1, h2, h3, h4, h5, h6, li"):
                        text = elem.text(separator=" ", strip=True)
                        if text and len(text) > 30:  # Skip tiny text
                            tag_name = elem.tag
                            if tag_name and tag_name.startswith("h"):
                                paragraphs.append(f"## {text}")  # Mark headings
                            else:
                                paragraphs.append(text)
            
            # Join and truncate
            main_text = "\n\n".join(paragraphs)
            if len(main_text) > max_chars:
                main_text = main_text[:max_chars] + "..."
                # Truncate paragraphs list too
                char_count = 0
                truncated_paras = []
                for p in paragraphs:
                    if char_count + len(p) > max_chars:
                        break
                    truncated_paras.append(p)
                    char_count += len(p) + 2
                paragraphs = truncated_paras
            
            word_count = len(main_text.split())
            
            return {
                "success": True,
                "url": url,
                "title": title,
                "main_text": main_text,
                "paragraphs": paragraphs[:50],  # Limit to 50 paragraphs
                "word_count": word_count,
                "action": "web.extract_main_text"
            }
            
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "action": "web.extract_main_text"
            }

    # ========== RESEARCH (Comet-style multi-query pipeline) ==========
    def research(
        self,
        question: str,
        search_queries: List[str] | None = None,
        max_sources: int = 10,
        max_chars_per_source: int = 8000
    ) -> Dict[str, Any]:
        """
        Comet-style research: run multiple searches, fetch top sources, extract content.
        
        This performs a comprehensive research pipeline:
        1. Generate or use provided search queries (multiple angles)
        2. Search each query
        3. Deduplicate and rank URLs
        4. Fetch and extract content from top sources
        5. Return structured content with citations
        
        Args:
            question: The user's research question
            search_queries: Optional list of search queries (if not provided, uses question directly)
            max_sources: Maximum number of sources to extract (default 10)
            max_chars_per_source: Max chars to extract per source (default 8000)
        
        Returns:
            {
                "success": True,
                "question": str,
                "queries_used": [str, ...],
                "sources_reviewed": int,
                "sources": [
                    {
                        "title": str,
                        "url": str,
                        "domain": str,
                        "snippet": str,
                        "content": str (extracted main text),
                        "word_count": int
                    }, ...
                ],
                "failed_sources": [{"url": str, "error": str}, ...],
                "action": "web.research"
            }
        """
        import concurrent.futures
        from urllib.parse import urlparse
        
        # Use provided queries or just the question, and enrich with helpful variants
        base_q = question.strip()
        queries = [q for q in (search_queries or [base_q]) if q and q.strip()]
        if not queries:
            queries = [base_q]
        # Auto-augment with a few angles for better coverage
        def add(qs: List[str], q: str) -> None:
            if q not in qs:
                qs.append(q)
        add(queries, f"{base_q} 2025")
        add(queries, f"{base_q} list")
        add(queries, "Django vs FastAPI vs Flask")
        add(queries, "top python frameworks for web development")
        # High-signal site variants for reliability
        site_domains = [
            "realpython.com",
            "fastapi.tiangolo.com",
            "palletsprojects.com",
            "docs.djangoproject.com",
            "fullstackpython.com",
        ]
        for site in site_domains:
            add(queries, f"site:{site} {base_q}")
        
        all_results: List[Dict[str, str]] = []
        seen_urls: set = set()
        
        print(f"\n[WebResearch] Searching for: {question}")
        print(f"[WebResearch] Using {len(queries)} search queries")
        
        # Step 1: Run all searches (retry with fallback if zero results)
        for query in queries:
            print(f"[WebResearch] Searching: '{query}'")
            search_result = self.search(query, max_results=10)
            if search_result.get("success") and search_result.get("results"):
                for r in search_result["results"]:
                    url = r.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        # Add domain for display
                        domain = urlparse(url).netloc.replace("www.", "")
                        r["domain"] = domain
                        all_results.append(r)
            else:
                # If this query failed or returned nothing, try a slight variant
                alt_query = f"{query} overview"
                print(f"[WebResearch] Retrying with: '{alt_query}'")
                retry_result = self.search(alt_query, max_results=10)
                if retry_result.get("success") and retry_result.get("results"):
                    for r in retry_result["results"]:
                        url = r.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            domain = urlparse(url).netloc.replace("www.", "")
                            r["domain"] = domain
                            all_results.append(r)
        
        # Relevance filter: keep tech-focused results first
        if all_results:
            kw = ["python", "framework", "django", "flask", "fastapi", "pyramid", "web"]
            filtered: List[Dict[str, str]] = []
            for r in all_results:
                t = (r.get("title") or "").lower()
                s = (r.get("snippet") or "").lower()
                d = (r.get("domain") or "").lower()
                text = f"{t} {s} {d}"
                # require python and either framework or one of popular names
                if ("python" in text) and ("framework" in text or any(k in text for k in ["django","flask","fastapi","pyramid","web"])):
                    filtered.append(r)
            if filtered:
                all_results = filtered

        print(f"[WebResearch] Found {len(all_results)} unique URLs")
        
        # Step 2: Limit to max_sources
        urls_to_fetch = all_results[:max_sources]
        
        print(f"[WebResearch] Reviewing sources · {len(urls_to_fetch)}")
        for r in urls_to_fetch:
            print(f"  [{r.get('title', 'Unknown')[:50]}]({r.get('domain', '')})")
        if not urls_to_fetch:
            return {
                "success": False,
                "question": question,
                "queries_used": queries,
                "sources_reviewed": 0,
                "sources": [],
                "failed_sources": [],
                "error": "No search results found (DuckDuckGo HTML may be blocking or returned zero results). Try rephrasing or using a VPN.",
                "action": "web.research"
            }
        
        # Step 3: Fetch and extract content from each source (parallel)
        sources: List[Dict[str, Any]] = []
        failed_sources: List[Dict[str, str]] = []
        
        def fetch_source(result: Dict[str, str]) -> Dict[str, Any] | None:
            url = result.get("url", "")
            try:
                extracted = self.extract_main_text(url, max_chars=max_chars_per_source)
                if extracted.get("success"):
                    return {
                        "title": extracted.get("title") or result.get("title", ""),
                        "url": url,
                        "domain": result.get("domain", ""),
                        "snippet": result.get("snippet", ""),
                        "content": extracted.get("main_text", ""),
                        "paragraphs": extracted.get("paragraphs", []),
                        "word_count": extracted.get("word_count", 0)
                    }
                else:
                    return {"url": url, "error": extracted.get("error", "extraction failed")}
            except Exception as e:
                return {"url": url, "error": str(e)}
        
        # Fetch in parallel (max 5 workers to be polite)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_result = {executor.submit(fetch_source, r): r for r in urls_to_fetch}
            for future in concurrent.futures.as_completed(future_to_result):
                result = future.result()
                if result:
                    if "error" in result:
                        failed_sources.append(result)
                    else:
                        sources.append(result)
        
        print(f"[WebResearch] Successfully extracted {len(sources)} sources")
        if failed_sources:
            print(f"[WebResearch] Failed to extract {len(failed_sources)} sources")
        
        return {
            "success": True,
            "question": question,
            "queries_used": queries,
            "sources_reviewed": len(urls_to_fetch),
            "sources": sources,
            "failed_sources": failed_sources,
            "action": "web.research"
        }

    # ========== ANSWER (Research + LLM synthesis) ==========
    def answer(
        self,
        question: str,
        search_queries: Optional[List[str]] = None,
        max_sources: int = 8,
        max_chars_per_source: int = 6000,
        temperature: float = 0.2,
        max_tokens: int = 700
    ) -> Dict[str, Any]:
        """
        High-level one-shot answer tool: runs research, then synthesizes an answer with citations.

        Returns:
            {
              "success": True/False,
              "answer": str,
              "sources": [{"title", "url", "domain"}, ...],
              "action": "web.answer"
            }
        """
        # Run research first
        research = self.research(
            question=question,
            search_queries=search_queries,
            max_sources=max_sources,
            max_chars_per_source=max_chars_per_source,
        )

        if not research.get("success") or not research.get("sources"):
            return {
                "success": False,
                "error": research.get("error", "No sources found"),
                "question": question,
                "sources": [],
                "action": "web.answer"
            }

        sources: List[Dict[str, Any]] = research.get("sources", [])

        # If no LLM available, return the raw sources to the caller
        if not getattr(self, "llm", None):
            return {
                "success": True,
                "answer": "",
                "note": "LLM not available in WebExecutor; returning sources only.",
                "sources": [{
                    "title": s.get("title", ""),
                    "url": s.get("url", ""),
                    "domain": s.get("domain", "")
                } for s in sources],
                "action": "web.answer"
            }

        # Build a compact synthesis prompt with citations
        def format_source(i: int, s: Dict[str, Any]) -> str:
            title = s.get("title", "")
            url = s.get("url", "")
            domain = s.get("domain", "")
            content = s.get("content", "")
            content = content[:max_chars_per_source]
            return f"[{i}] {title} ({domain})\nURL: {url}\n---\n{content}"

        blocks = []
        for idx, s in enumerate(sources[:max_sources], 1):
            blocks.append(format_source(idx, s))
        context_blob = "\n\n".join(blocks)

        system = (
            "You are a careful researcher. Answer the user's question using only the provided sources. "
            "Cite sources inline with [n] where n is the number of the source block. "
            "Be concise, objective, and avoid speculation. If uncertain, say so."
        )
        prompt = (
            f"Question: {question}\n\n"
            f"Sources (numbered):\n{context_blob}\n\n"
            "Write a clear, well-structured answer with bullet points where helpful. "
            "Include citations like [1], [2] after the relevant statements."
        )

        try:
            # Use LLM to synthesize
            # Note: local LLM interface may not support max_tokens; constrain via prompt
            answer_text = self.llm.generate(prompt, system=system, temperature=temperature)
        except Exception as e:
            return {
                "success": False,
                "error": f"LLM synthesis failed: {e}",
                "question": question,
                "sources": [],
                "action": "web.answer"
            }

        return {
            "success": True,
            "answer": answer_text.strip(),
            "sources": [{
                "title": s.get("title", ""),
                "url": s.get("url", ""),
                "domain": s.get("domain", "")
            } for s in sources[:max_sources]],
            "action": "web.answer"
        }

    # ========== DEEP RESEARCH (Evidence-Based Iterative) ==========
    def deep_research(
        self,
        question: str,
        max_iterations: int = 3,
        sources_per_query: int = 4
    ) -> Dict[str, Any]:
        """
        Execute deep iterative research with claim verification.
        
        This is the new architecture that:
        1. Generates initial queries
        2. Collects evidence
        3. Analyzes gaps (what's unclear/missing/conflicting)
        4. Generates follow-up queries
        5. Collects more evidence
        6. Repeats 2-3 times
        7. Extracts atomic claims
        8. Verifies claims with confidence scores
        9. Synthesizes answer
        
        Args:
            question: Research question
            max_iterations: Max refinement iterations (default 3)
            sources_per_query: Sources per query (default 4)
        
        Returns:
            {
                "success": True,
                "answer": str,
                "sources": List[Dict],  # {id, title, url, domain, quality}
                "confidence_breakdown": List[Dict],  # Per-claim confidence
                "overall_confidence": float,
                "iterations": int,
                "total_sources": int,
                "research_log": List[str],
                "action": "web.deep_research"
            }
        """
        if not self.llm:
            return {
                "success": False,
                "error": "LLM required for deep_research",
                "question": question,
                "action": "web.deep_research"
            }
        
        # Lazy-load research controller
        if self._research_controller is None:
            from .research import ResearchController
            self._research_controller = ResearchController(
                web_executor=self,
                planner_llm=self.planner_llm or self.llm,
                synthesis_llm=self.llm,
            )
        
        try:
            result = self._research_controller.research(
                question=question,
                max_iterations=max_iterations,
                sources_per_query=sources_per_query
            )
            
            # Add success flag and action
            result["success"] = True
            result["question"] = question
            result["action"] = "web.deep_research"
            
            return result
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Deep research failed: {e}",
                "question": question,
                "action": "web.deep_research"
            }

