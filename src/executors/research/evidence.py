"""Evidence storage and management."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class EvidenceChunk:
    """A chunk of text extracted from a source."""
    text: str
    source_url: str
    source_title: str
    domain: str
    chunk_index: int
    word_count: int
    
    # Metadata
    is_official_doc: bool = False
    is_tutorial: bool = False
    is_blog: bool = False
    published_date: Optional[str] = None
    
    def quality_score(self) -> float:
        """Source quality score (0.0-1.0)."""
        score = 0.5  # baseline
        
        # Official docs are high quality
        if self.is_official_doc:
            score += 0.4
        # Tutorials are good
        elif self.is_tutorial:
            score += 0.3
        # Blogs are okay
        elif self.is_blog:
            score += 0.1
        
        # High-quality domains
        trusted_domains = [
            "realpython.com",
            "fastapi.tiangolo.com",
            "docs.djangoproject.com",
            "flask.palletsprojects.com",
            "python.org",
            "readthedocs.io",
        ]
        if any(d in self.domain for d in trusted_domains):
            score += 0.2
        
        # Penalty for very short content
        if self.word_count < 50:
            score -= 0.2
        
        return max(0.0, min(1.0, score))


@dataclass
class Evidence:
    """Complete evidence from a single source."""
    url: str
    title: str
    domain: str
    chunks: List[EvidenceChunk] = field(default_factory=list)
    snippet: str = ""
    
    # Extraction metadata
    total_words: int = 0
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    extraction_success: bool = True
    extraction_error: Optional[str] = None
    
    def quality_score(self) -> float:
        """Average quality across chunks."""
        if not self.chunks:
            return 0.0
        return sum(c.quality_score() for c in self.chunks) / len(self.chunks)
    
    def get_full_text(self) -> str:
        """Concatenate all chunks."""
        return "\n\n".join(c.text for c in self.chunks)


class EvidenceStore:
    """Store and query evidence."""
    
    def __init__(self):
        self.evidence: List[Evidence] = []
        self._url_index: Dict[str, Evidence] = {}
    
    def add(self, evidence: Evidence) -> None:
        """Add evidence to the store."""
        self.evidence.append(evidence)
        self._url_index[evidence.url] = evidence
    
    def get_by_url(self, url: str) -> Optional[Evidence]:
        """Retrieve evidence by URL."""
        return self._url_index.get(url)
    
    def get_all(self) -> List[Evidence]:
        """Get all evidence."""
        return self.evidence
    
    def get_high_quality(self, min_score: float = 0.6) -> List[Evidence]:
        """Get high-quality evidence only."""
        return [e for e in self.evidence if e.quality_score() >= min_score]
    
    def total_sources(self) -> int:
        """Count total sources."""
        return len(self.evidence)
    
    def total_words(self) -> int:
        """Count total words across all evidence."""
        return sum(e.total_words for e in self.evidence)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "total_sources": self.total_sources(),
            "total_words": self.total_words(),
            "evidence": [
                {
                    "url": e.url,
                    "title": e.title,
                    "domain": e.domain,
                    "quality_score": e.quality_score(),
                    "chunks": len(e.chunks),
                    "words": e.total_words,
                }
                for e in self.evidence
            ],
        }
