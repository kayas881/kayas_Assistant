from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Tuple

from .config import default_delete_action


RISKY_PREFIXES = {
    "filesystem.delete_file": "Deleting files is destructive.",
    "email.send": "Sending emails can have external effects.",
}


@dataclass
class SafetyDecision:
    allowed: bool
    needs_confirmation: bool
    reason: str = ""
    alternatives: Dict[str, Any] | None = None


class SafetyPolicy:
    def assess(self, tool: str, args: Dict[str, Any]) -> SafetyDecision:
        # Default safe
        for prefix, reason in RISKY_PREFIXES.items():
            if tool.startswith(prefix):
                # Offer an alternative where applicable
                alts: Dict[str, Any] = {}
                if tool == "filesystem.delete_file":
                    # Propose archive instead of delete
                    alts = {
                        "suggestion": "filesystem.archive_file",
                        "args": {k: v for k, v in args.items() if k in ("filename",)},
                    }
                    # If user prefers archive, we can mark it as allowed (auto-choice)
                    if default_delete_action() == "archive":
                        return SafetyDecision(allowed=False, needs_confirmation=True, reason=reason, alternatives=alts)
                return SafetyDecision(allowed=False, needs_confirmation=True, reason=reason, alternatives=alts or None)
        return SafetyDecision(allowed=True, needs_confirmation=False)
