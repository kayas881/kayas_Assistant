"""Query planning for iterative research."""
from __future__ import annotations

from typing import List, Dict, Any
from .evidence import EvidenceStore


class QueryPlanner:
    """Plan and refine search queries."""
    
    def __init__(self, llm):
        self.llm = llm
    
    def generate_initial_queries(self, question: str) -> List[str]:
        """Generate 2-3 initial search queries for a question."""
        prompt = f"""Task: Generate 3 web search queries.

Topic: {question}

Output format:
1. query one
2. query two
3. query three

Max 8 words per query.

Queries:"""
        
        try:
            response = self.llm.generate(prompt, temperature=0.7)
            
            # Parse queries
            queries = []
            for line in response.strip().split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    query = line.lstrip("0123456789.-) \t")
                    if query and len(query) > 5:
                        queries.append(query)
            
            # Fallback if parsing failed
            if not queries:
                queries = [question]
            
            return queries[:3]
        
        except Exception as e:
            print(f"[QueryPlanner] Initial query generation failed: {e}")
            # Fallback: use original question as query
            return [question]
    
    def analyze_gaps(
        self, 
        question: str,
        evidence_store: EvidenceStore
    ) -> Dict[str, Any]:
        """Analyze what's missing, unclear, or conflicting in current evidence.
        
        Returns:
            {
                "unclear": ["aspect 1", "aspect 2", ...],
                "missing": ["topic 1", "topic 2", ...],
                "conflicts": ["conflict 1", ...],
                "has_gaps": bool
            }
        """
        if not evidence_store.get_all():
            return {
                "unclear": [],
                "missing": [question],
                "conflicts": [],
                "has_gaps": True
            }
        
        # Summarize current evidence
        evidence_summary = []
        for i, ev in enumerate(evidence_store.get_all()[:8], 1):
            snippet = ev.get_full_text()[:400]
            evidence_summary.append(f"[{i}] {ev.title}: {snippet}")
        
        combined = "\n".join(evidence_summary)
        
        prompt = f"""Task: Find gaps in research.

Question: {question}

Evidence:
{combined}

List what's:
UNCLEAR:
- item

MISSING:
- item

CONFLICTS:
- item

Analysis:"""
        
        try:
            response = self.llm.generate(prompt, temperature=0.5)
            
            # Parse response
            unclear = []
            missing = []
            conflicts = []
            
            current_section = None
            for line in response.strip().split("\n"):
                line = line.strip()
                
                if "UNCLEAR:" in line.upper():
                    current_section = "unclear"
                elif "MISSING:" in line.upper():
                    current_section = "missing"
                elif "CONFLICTS:" in line.upper() or "CONFLICT:" in line.upper():
                    current_section = "conflicts"
                elif line.startswith("-") or line.startswith("•"):
                    item = line.lstrip("-• \t")
                    if item:
                        if current_section == "unclear":
                            unclear.append(item)
                        elif current_section == "missing":
                            missing.append(item)
                        elif current_section == "conflicts":
                            conflicts.append(item)
            
            has_gaps = bool(unclear or missing or conflicts)
            
            return {
                "unclear": unclear,
                "missing": missing,
                "conflicts": conflicts,
                "has_gaps": has_gaps
            }
        
        except Exception as e:
            print(f"[QueryPlanner] Gap analysis failed: {e}")
            return {
                "unclear": [],
                "missing": [],
                "conflicts": [],
                "has_gaps": False
            }
    
    def generate_followup_queries(
        self,
        question: str,
        gap_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate 2-3 follow-up queries based on gap analysis."""
        unclear = gap_analysis.get("unclear", [])
        missing = gap_analysis.get("missing", [])
        conflicts = gap_analysis.get("conflicts", [])
        
        if not (unclear or missing or conflicts):
            return []
        
        # Build prompt
        gaps_text = []
        if unclear:
            gaps_text.append("UNCLEAR:\n" + "\n".join(f"- {u}" for u in unclear))
        if missing:
            gaps_text.append("MISSING:\n" + "\n".join(f"- {m}" for m in missing))
        if conflicts:
            gaps_text.append("CONFLICTS:\n" + "\n".join(f"- {c}" for c in conflicts))
        
        prompt = f"""Task: Generate follow-up search queries.

Topic: {question}

Gaps:
{chr(10).join(gaps_text)}

Output:
1. query one
2. query two
3. query three

Max 8 words each.

Queries:"""
        
        try:
            response = self.llm.generate(prompt, temperature=0.7)
            
            # Parse queries
            queries = []
            for line in response.strip().split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    query = line.lstrip("0123456789.-) \t")
                    if query and len(query) > 5:
                        queries.append(query)
            
            return queries[:3]
        
        except Exception as e:
            print(f"[QueryPlanner] Follow-up generation failed: {e}")
            return []
