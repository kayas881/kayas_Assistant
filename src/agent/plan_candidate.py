from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class PlanCandidate:
    """A single candidate plan with cost/risk metrics for ranking."""
    
    # Core plan
    actions: List[Dict[str, Any]]  # List of {"tool": "name", "args": {...}}
    strategy_name: str  # e.g., "direct_api", "browser_automation", "fallback_filesystem"
    
    # Metrics for ranking
    risk_score: float = 0.0  # 0.0 = safe, 1.0 = risky (manual actions, CAPTCHA, etc.)
    step_count: int = 0
    estimated_time_sec: float = 0.0  # rough estimate
    confidence: float = 0.5  # preference model score or heuristic confidence
    
    # Optional metadata
    raw_llm_output: str = ""
    prompt_used: str = ""
    
    def __post_init__(self):
        if self.step_count == 0:
            self.step_count = len(self.actions)
    
    def overall_score(self) -> float:
        """Compute a combined score for ranking. Higher is better."""
        # Balance: high confidence, low risk, fewer steps
        # Normalize: confidence [0-1], risk [0-1], steps typically [1-10]
        step_penalty = min(1.0, self.step_count / 10.0)
        return (
            self.confidence * 2.0 
            - self.risk_score * 1.5 
            - step_penalty * 0.5
        )


def compute_risk_score(actions: List[Dict[str, Any]]) -> float:
    """Estimate risk based on tool usage patterns."""
    risk = 0.0
    risky_tools = {
        "browser.run_steps": 0.3,  # CAPTCHA risk
        "desktop.run_steps": 0.2,  # manual UI risk
        "uia.click_button": 0.15,
        "process.kill_process": 0.4,
        "filesystem.delete_file": 0.3,
    }
    for action in actions:
        tool = action.get("tool", "")
        risk += risky_tools.get(tool, 0.05)  # baseline risk for any action
    return min(1.0, risk)


def estimate_time(actions: List[Dict[str, Any]]) -> float:
    """Rough time estimate in seconds."""
    time_map = {
        "web.fetch": 2.0,
        "browser.run_steps": 5.0,
        "desktop.run_steps": 3.0,
        "process.run_command": 1.0,
        "filesystem.create_file": 0.1,
        "email.send": 2.0,
        "llm.generate": 3.0,
    }
    total = 0.0
    for action in actions:
        tool = action.get("tool", "")
        total += time_map.get(tool, 0.5)
    return total
