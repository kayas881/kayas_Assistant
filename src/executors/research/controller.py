"""Main research controller - orchestrates iterative evidence-based research."""
from __future__ import annotations

from typing import Dict, Any, Optional

from .evidence import EvidenceStore
from .query_planner import QueryPlanner
from .collector import EvidenceCollector
from .claims import ClaimBuilder, ClaimVerifier
from .synthesizer import AnswerSynthesizer


class ResearchController:
    """Orchestrate iterative research pipeline."""
    
    def __init__(self, web_executor, planner_llm, synthesis_llm=None):
        """
        Args:
            web_executor: WebExecutor instance for search/fetch/extract
            planner_llm: Fast LLM for query planning / gap spotting
            synthesis_llm: Stronger LLM for claim extraction / final synthesis
        """
        self.web = web_executor
        self.planner_llm = planner_llm
        self.synthesis_llm = synthesis_llm or planner_llm
        
        # Initialize components
        self.query_planner = QueryPlanner(self.planner_llm)
        self.collector = EvidenceCollector(web_executor)
        self.claim_builder = ClaimBuilder(self.synthesis_llm)
        self.claim_verifier = ClaimVerifier(self.planner_llm)
        self.synthesizer = AnswerSynthesizer(self.synthesis_llm)
    
    def research(
        self,
        question: str,
        max_iterations: int = 3,
        sources_per_query: int = 4
    ) -> Dict[str, Any]:
        """Execute full iterative research pipeline.
        
        Pipeline:
        1. Generate initial queries
        2. Collect evidence (iteration 1)
        3. For each iteration (2-3 times):
           - Analyze gaps in current evidence
           - Generate follow-up queries
           - Collect more evidence
        4. Extract claims from all evidence
        5. Verify claims (cross-check, confidence scoring)
        6. Synthesize final answer
        
        Args:
            question: Research question
            max_iterations: Max refinement iterations (default 3)
            sources_per_query: Sources to collect per query (default 4)
        
        Returns:
            {
                "answer": str,
                "sources": List[Dict],
                "confidence_breakdown": List[Dict],
                "overall_confidence": float,
                "iterations": int,
                "total_sources": int,
                "research_log": List[str]  # What happened each iteration
            }
        """
        evidence_store = EvidenceStore()
        research_log = []
        
        # ===== ITERATION 1: Initial queries =====
        print(f"\n[ResearchController] Starting research: {question}")
        
        initial_queries = self.query_planner.generate_initial_queries(question)
        research_log.append(f"Initial queries: {', '.join(initial_queries)}")
        print(f"[Iteration 1] Queries: {initial_queries}")
        
        # Collect evidence
        evidence_batch = self.collector.collect_from_queries(
            initial_queries,
            max_sources_per_query=sources_per_query
        )
        
        for ev in evidence_batch:
            evidence_store.add(ev)
        
        research_log.append(f"Iteration 1: Collected {len(evidence_batch)} sources")
        print(f"[Iteration 1] Collected {len(evidence_batch)} sources, {evidence_store.total_words()} words")
        
        # ===== ITERATIONS 2-N: Iterative refinement =====
        for iteration in range(2, max_iterations + 1):
            # Analyze gaps (skip for now - Ollama hangs on long prompts)
            # TODO: Re-enable when we can handle timeouts
            research_log.append(f"Iteration {iteration}: Skipped (gap analysis disabled)")
            print(f"[Iteration {iteration}] Skipped (gap analysis disabled)")
            break
        
        # ===== CLAIM EXTRACTION & VERIFICATION =====
        print("\n[Claims] Extracting atomic claims...")
        claims = self.claim_builder.extract_claims(evidence_store)
        research_log.append(f"Extracted {len(claims)} claims")
        print(f"[Claims] Extracted {len(claims)} claims")
        
        print("[Claims] Verifying claims...")
        verified_claims = self.claim_verifier.verify_claims(claims, evidence_store)
        
        high_conf = sum(1 for c in verified_claims if c.confidence >= 0.6)
        research_log.append(f"Verified claims: {len(verified_claims)} total, {high_conf} high-confidence")
        print(f"[Claims] Verified: {len(verified_claims)} total, {high_conf} high-confidence")
        
        # ===== SYNTHESIS =====
        print("\n[Synthesis] Generating final answer...")
        result = self.synthesizer.synthesize(
            question,
            verified_claims,
            evidence_store
        )
        
        # Add metadata
        result["iterations"] = iteration if iteration <= max_iterations else max_iterations
        result["total_sources"] = evidence_store.total_sources()
        result["research_log"] = research_log
        
        print(f"[Synthesis] Complete! {result['total_sources']} sources, confidence: {result['overall_confidence']}")
        
        return result
