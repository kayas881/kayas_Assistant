"""Evidence collection from web sources."""
from __future__ import annotations

from typing import List, Optional
from urllib.parse import urlparse

from .evidence import Evidence, EvidenceChunk


class EvidenceCollector:
    """Collect and structure evidence from web sources."""
    
    def __init__(self, web_executor):
        """
        Args:
            web_executor: Instance of WebExecutor with search/fetch/extract methods
        """
        self.web = web_executor
    
    def collect_from_query(
        self, 
        query: str, 
        max_sources: int = 5
    ) -> List[Evidence]:
        """Execute search query and collect evidence.
        
        Args:
            query: Search query
            max_sources: Maximum number of sources to collect
        
        Returns:
            List of Evidence objects
        """
        # Search
        search_response = self.web.search(query)
        
        if not search_response or not search_response.get("success"):
            return []
        
        search_results = search_response.get("results", [])
        if not search_results:
            return []
        
        # Collect evidence from top results
        evidence_list = []
        
        for result in search_results[:max_sources]:
            url = result.get("url", "")
            title = result.get("title", "Unknown")
            snippet = result.get("snippet", "")
            
            if not url:
                continue
            
            # Extract domain
            domain = self._extract_domain(url)
            
            # Fetch and extract content
            try:
                extracted = ""

                # Prefer readability-style extraction
                extracted_res = self.web.extract_main_text(url)
                if isinstance(extracted_res, dict) and extracted_res.get("success"):
                    extracted = (extracted_res.get("main_text") or "").strip()

                # Fallback to fetch excerpt if extraction failed
                if not extracted:
                    fetch_res = self.web.fetch(url)
                    if isinstance(fetch_res, dict) and fetch_res.get("success"):
                        extracted = (fetch_res.get("excerpt") or "").strip()

                if not extracted:
                    continue
                
                # Create evidence object
                evidence = Evidence(
                    url=url,
                    title=title,
                    domain=domain,
                    snippet=snippet,
                    total_words=len(extracted.split()),
                    extraction_success=True
                )
                
                # Break into chunks (simple approach: split by double newline)
                chunks = self._create_chunks(extracted, url, title, domain)
                evidence.chunks = chunks
                
                evidence_list.append(evidence)
                
            except Exception as e:
                # Skip sources that failed to fetch/extract
                continue
        
        return evidence_list
    
    def collect_from_queries(
        self,
        queries: List[str],
        max_sources_per_query: int = 4
    ) -> List[Evidence]:
        """Collect evidence from multiple queries.
        
        Deduplicates by URL.
        """
        all_evidence = []
        seen_urls = set()
        
        for query in queries:
            evidence_list = self.collect_from_query(query, max_sources_per_query)
            
            for ev in evidence_list:
                if ev.url not in seen_urls:
                    all_evidence.append(ev)
                    seen_urls.add(ev.url)
        
        return all_evidence
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc or ""
        except:
            return ""
    
    def _create_chunks(
        self,
        text: str,
        url: str,
        title: str,
        domain: str
    ) -> List[EvidenceChunk]:
        """Break text into semantic chunks."""
        # Simple chunking by paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        chunks = []
        for i, para in enumerate(paragraphs):
            word_count = len(para.split())
            
            # Skip very short paragraphs
            if word_count < 20:
                continue
            
            # Classify content type
            is_official_doc = self._is_official_doc(domain)
            is_tutorial = self._is_tutorial(para, title)
            is_blog = self._is_blog(domain)
            
            chunk = EvidenceChunk(
                text=para,
                source_url=url,
                source_title=title,
                domain=domain,
                chunk_index=i,
                word_count=word_count,
                is_official_doc=is_official_doc,
                is_tutorial=is_tutorial,
                is_blog=is_blog
            )
            chunks.append(chunk)
        
        return chunks
    
    def _is_official_doc(self, domain: str) -> bool:
        """Check if domain is official documentation."""
        doc_indicators = [
            "docs.",
            "documentation",
            ".readthedocs.",
            "python.org",
            "djangoproject.com",
            "palletsprojects.com",  # Flask
            "fastapi.tiangolo.com",
        ]
        return any(ind in domain.lower() for ind in doc_indicators)
    
    def _is_tutorial(self, text: str, title: str) -> bool:
        """Check if content is tutorial-style."""
        tutorial_keywords = [
            "tutorial",
            "guide",
            "how to",
            "step by step",
            "getting started",
            "beginner",
        ]
        combined = (text[:500] + " " + title).lower()
        return any(kw in combined for kw in tutorial_keywords)
    
    def _is_blog(self, domain: str) -> bool:
        """Check if domain is a blog."""
        blog_indicators = [
            "blog",
            "medium.com",
            "dev.to",
            "hashnode",
            "substack",
        ]
        return any(ind in domain.lower() for ind in blog_indicators)
