"""Answer synthesis from verified claims."""
from __future__ import annotations

from typing import List, Dict, Any

from .claims import Claim
from .evidence import EvidenceStore


class AnswerSynthesizer:
    """Synthesize final answer from verified claims."""
    
    def __init__(self, llm):
        self.llm = llm
    
    def synthesize(
        self,
        question: str,
        verified_claims: List[Claim],
        evidence_store: EvidenceStore
    ) -> Dict[str, Any]:
        """Generate comprehensive answer with citations and confidence.
        
        Returns:
            {
                "answer": str,  # Main answer with [n] citations
                "sources": List[Dict],  # Source metadata
                "confidence_breakdown": List[Dict],  # Per-claim confidence
                "overall_confidence": float
            }
        """
        if not verified_claims:
            return {
                "answer": "No verified claims found to answer this question.",
                "sources": [],
                "confidence_breakdown": [],
                "overall_confidence": 0.0
            }
        
        # Filter to high-confidence claims
        high_conf_claims = [c for c in verified_claims if c.confidence >= 0.4]
        
        if not high_conf_claims:
            high_conf_claims = verified_claims[:5]  # Take top 5 if all are low
        
        # Build synthesis prompt
        claims_text = []
        for i, claim in enumerate(high_conf_claims[:15], 1):
            conf_label = self._confidence_label(claim.confidence)
            claims_text.append(
                f"{i}. {claim.text} "
                f"[confidence: {conf_label}, sources: {claim.total_support()}]"
            )
        
        prompt = f"""Task: Answer question using claims.

Question: {question}

Claims:
{chr(10).join(claims_text)}

Write 2-3 paragraph answer.
Use LOW confidence claims with "some sources suggest".

Answer:"""
        
        try:
            answer = self.llm.generate(prompt, temperature=0.5)
            
            # Build sources list
            all_evidence = evidence_store.get_all()
            sources = []
            for i, ev in enumerate(all_evidence, 1):
                sources.append({
                    "id": i,
                    "title": ev.title,
                    "url": ev.url,
                    "domain": ev.domain,
                    "quality": round(ev.quality_score(), 2)
                })
            
            # Build confidence breakdown
            breakdown = []
            for claim in high_conf_claims:
                breakdown.append({
                    "claim": claim.text,
                    "confidence": round(claim.confidence, 2),
                    "support_count": claim.total_support(),
                    "high_quality": claim.high_quality_support,
                    "conflicts": len(claim.conflicting_sources)
                })
            
            # Calculate overall confidence
            if high_conf_claims:
                overall_conf = sum(c.confidence for c in high_conf_claims) / len(high_conf_claims)
            else:
                overall_conf = 0.0
            
            return {
                "answer": answer.strip(),
                "sources": sources,
                "confidence_breakdown": breakdown,
                "overall_confidence": round(overall_conf, 2)
            }
        
        except Exception as e:
            print(f"[AnswerSynthesizer] Synthesis failed: {e}")
            return {
                "answer": f"Failed to synthesize answer: {e}",
                "sources": [],
                "confidence_breakdown": [],
                "overall_confidence": 0.0
            }
    
    def _confidence_label(self, score: float) -> str:
        """Convert numeric confidence to label."""
        if score >= 0.7:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
