from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .llm import LLM
from .actions import Action, Router, parse_actions
from .config import react_max_steps, react_beam_width
from ..training.preference_model import score_plan


REACT_SYSTEM = (
    "You are a ReAct agent. You reason step-by-step, then act using JSON tool calls, then observe the result, and repeat.\n"
    "At each turn, emit ONLY JSON with either:\n"
    "{\"thought\": string, \"actions\": [{\"tool\": string, \"args\": object}]} OR {\"finish\": string}.\n"
    "Be concise, pick minimal actions, and avoid repeating failed steps."
)


@dataclass
class ReactResult:
    final_text: str
    actions_taken: List[Dict]
    raw_traces: List[str]


class ReactAgent:
    def __init__(self, llm: LLM, router: Router):
        self.llm = llm
        self.router = router

    def _prompt(self, goal: str, history: List[Tuple[str, Dict]]) -> str:
        # History is [(observation_text, last_action_result_dict), ...]
        obs_lines: List[str] = []
        for i, (thought, obs) in enumerate(history[-5:]):
            obs_lines.append(f"Step {i+1} Thought: {thought}")
            if obs:
                try:
                    obs_lines.append("Observation: " + json.dumps(obs)[:800])
                except Exception:
                    obs_lines.append("Observation: [unserializable]")
        ctx = "\n".join(obs_lines)
        return f"Goal: {goal}\n{ctx}\nNext JSON:"

    def run(self, goal: str, max_steps: Optional[int] = None, beam_width: Optional[int] = None) -> ReactResult:
        max_steps = max_steps or react_max_steps()
        beam_width = beam_width or react_beam_width()
        traces: List[str] = []
        history: List[Tuple[str, Dict]] = []
        actions_taken: List[Dict] = []

        for step in range(max_steps):
            prompt = self._prompt(goal, history)
            raw = self.llm.generate(prompt, system=REACT_SYSTEM, temperature=0.2)
            traces.append(raw)
            # parse JSON dict; allow action lists
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
            if isinstance(data, dict) and "finish" in data:
                return ReactResult(final_text=str(data.get("finish", "")), actions_taken=actions_taken, raw_traces=traces)

            cand_actions: List[Action] = []
            thought = data.get("thought", "") if isinstance(data, dict) else ""
            if isinstance(data, dict) and isinstance(data.get("actions"), list):
                for item in data["actions"]:
                    if not isinstance(item, dict):
                        continue
                    tool = item.get("tool")
                    args = item.get("args", {})
                    if isinstance(tool, str) and isinstance(args, dict):
                        cand_actions.append(Action(tool=tool, args=args))
            if not cand_actions:
                # no-op: try a search as a default exploratory step
                cand_actions = [Action(tool="local.search", args={"query": goal[:128]})]

            # Simple beam: score each action plan with preference model and pick top-1
            scored: List[Tuple[float, Action]] = []
            for a in cand_actions:
                try:
                    s = score_plan(prompt, json.dumps({"tool": a.tool, "args": a.args}))
                except Exception:
                    s = 0.5
                scored.append((s, a))
            scored.sort(key=lambda x: -x[0])
            best_actions = [a for _, a in scored[:max(1, min(beam_width, len(scored)))]]

            # Execute selected action(s) sequentially this turn (usually one)
            last_obs: Dict = {}
            for a in best_actions:
                res = self.router.dispatch(a)
                actions_taken.append({"tool": a.tool, "args": a.args, "result": res})
                # minimal self-correction: sanitize filename on error
                if isinstance(res, dict) and res.get("error") and a.tool.startswith("filesystem.") and "filename" in a.args:
                    err = str(res.get("error", "")).lower()
                    if any(x in err for x in ["invalid", "illegal", "file name"]):
                        fname = a.args.get("filename", "notes.txt")
                        fname = re.sub(r'[<>:"/\\|?*]', "_", fname)
                        a.args["filename"] = fname or "notes.txt"
                        res = self.router.dispatch(a)
                        actions_taken.append({"tool": a.tool, "args": a.args, "result": res, "retry": True})
                last_obs = res

            # Save thought + observation into history for the next step
            history.append((thought, last_obs if isinstance(last_obs, dict) else {}))

        return ReactResult(final_text="Reached step limit.", actions_taken=actions_taken, raw_traces=traces)
