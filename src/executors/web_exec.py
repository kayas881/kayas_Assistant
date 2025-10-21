from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import httpx
from selectolax.parser import HTMLParser


@dataclass
class WebConfig:
    timeout: float = 15.0
    user_agent: str = "Mozilla/5.0 (compatible; KayasBot/1.0)"


class WebExecutor:
    def __init__(self, cfg: WebConfig) -> None:
        self.cfg = cfg

    def fetch(self, url: str) -> Dict:
        headers = {"User-Agent": self.cfg.user_agent}
        with httpx.Client(timeout=self.cfg.timeout, follow_redirects=True, headers=headers) as client:
            r = client.get(url)
            r.raise_for_status()
            html = r.text
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
            # Concatenate first paragraphs to avoid menus/tables; preserve spacing around inline elements
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
        return {"url": url, "title": title, "excerpt": excerpt}
