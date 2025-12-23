"""Claims extraction and verification."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .evidence import EvidenceStore, Evidence


@dataclass
class Claim:
    """An atomic factual claim."""
    text: str
    supporting_sources: List[str] = field(default_factory=list)  # URLs
    conflicting_sources: List[str] = field(default_factory=list)  # URLs
    confidence: float = 0.0
    
    # Source quality breakdown
    high_quality_support: int = 0
    medium_quality_support: int = 0
    low_quality_support: int = 0
    
    def total_support(self) -> int:
        """Total supporting sources."""
        return len(self.supporting_sources)
    
    def has_conflict(self) -> bool:
        """Whether claim has conflicting evidence."""
        return len(self.conflicting_sources) > 0


class ClaimBuilder:
    """Extract atomic claims from evidence."""
    
    def __init__(self, llm):
        self.llm = llm
    
    def extract_claims(self, evidence_store: EvidenceStore) -> List[Claim]:
        """Extract claims from all evidence.
        
        Uses LLM to break down evidence into atomic factual statements.
        """
        if not evidence_store.get_all():
            return []
        
        # Collect all high-quality evidence text
        evidence_items = evidence_store.get_high_quality(min_score=0.5)
        if not evidence_items:
            evidence_items = evidence_store.get_all()
        
        # Build prompt for claim extraction
        evidence_texts = []
        for i, ev in enumerate(evidence_items[:10], 1):  # Limit to top 10
            evidence_texts.append(f"[Source {i}] {ev.title} ({ev.domain}):\n{ev.get_full_text()[:800]}")
        
        combined = "\n\n".join(evidence_texts)
        
        prompt = f"""Task: Extract factual claims.

Evidence:
{combined}

Output:
1. claim one
2. claim two
3. claim three

Claims:"""
        
        try:
            response = self.llm.generate(prompt, temperature=0.3)
            
            # Parse claims from response
            claims = []
            for line in response.strip().split("\n"):
                line = line.strip()
                # Match numbered items
                if line and (line[0].isdigit() or line.startswith("-") or line.startswith("•")):
                    # Remove numbering/bullets
                    claim_text = line.lstrip("0123456789.-•) \t")
                    if claim_text and len(claim_text) > 10:
                        claims.append(Claim(text=claim_text))
            
            return claims
        except Exception as e:
            print(f"[ClaimBuilder] Extraction failed: {e}")
            return []


class ClaimVerifier:
    """Verify claims against evidence."""
    
    def __init__(self, llm):
        self.llm = llm
    
    def verify_claims(
        self, 
        claims: List[Claim], 
        evidence_store: EvidenceStore
    ) -> List[Claim]:
        """Cross-check claims against evidence and calculate confidence.
        
        For each claim:
        1. Count supporting sources
        2. Detect conflicting sources
        3. Assess source quality
        4. Calculate confidence score
        """
        verified_claims = []
        
        all_evidence = evidence_store.get_all()
        
        for claim in claims:
            # For each claim, check which sources support it
            supporting = []
            conflicting = []
            high_q = 0
            med_q = 0
            low_q = 0
            
            for ev in all_evidence:
                support_status = self._check_support(claim.text, ev)
                
                if support_status == "support":
                    supporting.append(ev.url)
                    # Track quality
                    score = ev.quality_score()
                    if score >= 0.7:
                        high_q += 1
                    elif score >= 0.5:
                        med_q += 1
                    else:
                        low_q += 1
                elif support_status == "conflict":
                    conflicting.append(ev.url)
            
            # Calculate confidence
            # Formula: (high*1.0 + med*0.6 + low*0.3) / total_sources
            total_sources = len(all_evidence)
            if total_sources > 0:
                weighted_support = (high_q * 1.0) + (med_q * 0.6) + (low_q * 0.3)
                confidence = min(1.0, weighted_support / total_sources)
            else:
                confidence = 0.0
            
            # Penalty for conflicts
            if conflicting:
                confidence *= 0.7
            
            claim.supporting_sources = supporting
            claim.conflicting_sources = conflicting
            claim.high_quality_support = high_q
            claim.medium_quality_support = med_q
            claim.low_quality_support = low_q
            claim.confidence = confidence
            
            verified_claims.append(claim)
        
        # Sort by confidence (highest first)
        verified_claims.sort(key=lambda c: c.confidence, reverse=True)
        
        return verified_claims
    
    def _check_support(self, claim_text: str, evidence: Evidence) -> str:
        """Check if evidence supports, conflicts, or is neutral to claim.
        
        Returns: "support", "conflict", or "neutral"
        """
        # Simple heuristic: check if key words from claim appear in evidence
        # In production, would use LLM or embeddings for better accuracy
        
        claim_lower = claim_text.lower()
        evidence_text = evidence.get_full_text().lower()
        
        # Extract key terms (very simple approach)
        claim_words = set(claim_lower.split())
        # Remove common words
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "for", "to", "of", "in", "on", "at"}
        claim_words -= stopwords
        
        if not claim_words:
            return "neutral"
        
        # Count matching words
        matches = sum(1 for word in claim_words if word in evidence_text)
        match_ratio = matches / len(claim_words)
        
        if match_ratio >= 0.5:  # At least half the keywords present
            return "support"
        elif match_ratio >= 0.2:  # Some keywords but not enough
            return "neutral"
        else:
            return "neutral"
