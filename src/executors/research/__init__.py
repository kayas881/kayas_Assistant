"""
Iterative evidence-based research system.

Architecture:
- QueryPlanner: generates initial + follow-up queries
- EvidenceCollector: search/fetch/extract pipeline
- EvidenceStore: structured evidence with metadata
- ClaimBuilder: extracts atomic claims from evidence
- ClaimVerifier: cross-checks claims across sources
- AnswerSynthesizer: generates final answer with citations
- ResearchController: orchestrates the full pipeline
"""

from .controller import ResearchController
from .evidence import EvidenceStore, Evidence, EvidenceChunk
from .claims import ClaimBuilder, ClaimVerifier, Claim
from .query_planner import QueryPlanner
from .collector import EvidenceCollector
from .synthesizer import AnswerSynthesizer

__all__ = [
    "ResearchController",
    "EvidenceStore",
    "Evidence",
    "EvidenceChunk",
    "ClaimBuilder",
    "ClaimVerifier",
    "Claim",
    "QueryPlanner",
    "EvidenceCollector",
    "AnswerSynthesizer",
]
