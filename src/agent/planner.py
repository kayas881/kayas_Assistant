from __future__ import annotations

from typing import List, Tuple
import json
from urllib.parse import quote_plus
import re

from .llm import LLM
from .config import preferred_search_base, default_notes_filename
from .actions import parse_actions


PLANNER_SYSTEM = (
    "You are a concise planner. Given a user's goal, produce a numbered list of 2-6 atomic steps that a simple executor can perform. "
    "Prefer filesystem actions like create file, write content. Keep steps terse."
)


def parse_steps(text: str) -> List[str]:
    steps: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Accept formats like '1. do X', '- do X', '• do X', or plain sentences
        if line[0].isdigit():
            line = line.split(".", 1)[-1].strip()
        elif line.startswith(('-', '*', '•')):
            line = line[1:].strip()
        steps.append(line)
    # Deduplicate while preserving order
    dedup: List[str] = []
    seen = set()
    for s in steps:
        if s not in seen:
            dedup.append(s)
            seen.add(s)
    return dedup[:8]


class Planner:
    def __init__(self, llm: LLM):
        self.llm = llm

    def plan(self, goal: str) -> List[str]:
        # Heuristic fast-path for notes requests
        g = goal.lower()
        if "note" in g or "notes" in g:
            return [
                "Create a notes file named 'freelancing-notes.txt'",
                "Write a concise summary of freelancing basics into the file",
            ]
        prompt = f"Goal: {goal}\nProduce 2-6 numbered steps."
        raw = self.llm.generate(prompt, system=PLANNER_SYSTEM, temperature=0.2)
        steps = parse_steps(raw)
        if not steps:
            steps = ["Create a file describing the goal", "Write a short summary into it"]
        return steps


STRUCTURED_SYSTEM = (
    "You are a planner that emits ONLY JSON representing tool calls. "
    "Schema: either a single object {\"tool\": string, \"args\": object} or a list of such objects. "
    "Available tools: \n"
    "- filesystem.create_file {filename, content?}\n"
    "- filesystem.append_file {filename, content}\n"
    "- web.fetch {url}\n"
    "- email.send {to, subject, body}\n"
    "- local.search {query}\n"
    "- calendar.list_events {calendar_id?, max_results?, days_ahead?}\n"
    "- calendar.create_event {summary, start_time, end_time, description?, location?}\n"
    "- calendar.delete_event {event_id, calendar_id?}\n"
    "- calendar.find_free_time {duration_minutes?, days_ahead?, start_hour?, end_hour?}\n"
    "- slack.send_message {channel, text, thread_ts?}\n"
    "- slack.list_channels {types?, limit?}\n"
    "- slack.get_user_info {user_id}\n"
    "- slack.search_messages {query, count?}\n"
    "- slack.set_status {text, emoji?, expiration?}\n"
    "- spotify.search_music {query, search_type?, limit?}\n"
    "- spotify.play_track {track_uri, device_id?}\n"
        "- spotify.play_query {query, device_id?}\\n"
    "- spotify.get_current_playing {}\n"
    "- spotify.pause_playback {device_id?}\n"
    "- spotify.resume_playback {device_id?}\n"
    "- spotify.get_user_playlists {limit?}\n"
    "- spotify.create_playlist {name, description?, public?}\n"
    "- spotify.add_tracks_to_playlist {playlist_id, track_uris}\n"
    "- browser.run_steps {steps, headless?, base_url?, stop_on_error?} (steps: [{action, args} where action in [goto, click, fill, type, press, wait_for_selector, wait, extract_text, screenshot])\n"
    "- desktop.run_steps {steps, stop_on_error?} (steps: actions [sleep, move_to, click, double_click, write, hotkey, screenshot, locate_on_screen, click_image, ocr_region])\n"
    "Rules: prefer minimal steps; don't repeat work; use append_file not create if file already exists (if told)."
)


def plan_structured(llm: LLM, goal: str, reuse_filename: str | None = None, feedback_hints: str = "") -> Tuple[List[dict], str, str]:
    hint = f"A file named {reuse_filename} already exists; avoid recreating it and use append_file if you need to add content.\n" if reuse_filename else ""
    fb = f"User preferences and corrections (guidance):\n{feedback_hints}\n" if feedback_hints else ""
    prompt = f"Goal: {goal}\n{hint}{fb}Emit JSON tool calls only, no extra text."
    try:
        # Heuristic: if the goal contains a direct URL, fetch it
        url_match = re.search(r"https?://\S+", goal)
        if url_match:
            u = url_match.group(0).rstrip(').,;')
            heuristic = [{"tool": "web.fetch", "args": {"url": u}}]
            raw = json.dumps(heuristic)
            return heuristic, raw, prompt

        # Heuristic: if the user asks to search or mentions Google/Bing etc., issue a web.fetch to a search URL
        g = goal.lower()
        if ("search" in g) or ("google" in g) or ("bing" in g) or ("duckduckgo" in g) or ("brave" in g):
            # Build a simple Google search URL; include full goal as query for robustness
            url = preferred_search_base() + quote_plus(goal)
            heuristic = [{"tool": "web.fetch", "args": {"url": url}}]
            raw = json.dumps(heuristic)
            return heuristic, raw, prompt

        # Heuristic: delete a file -> let tools handle it (safety can intercept)
        if ("delete" in g or "remove" in g) and "file" in g:
            filename = None
            # Try to extract a quoted filename
            m = re.search(r"'([^']+)'|\"([^\"]+)\"", goal)
            if m:
                filename = m.group(1) or m.group(2)
            if not filename:
                # Try to capture a path-like token after the word 'file'
                m2 = re.search(r"file\s+([\w./\\-]+)", goal, re.IGNORECASE)
                if m2:
                    filename = m2.group(1)
            filename = filename or default_notes_filename()
            heuristic = [{"tool": "filesystem.delete_file", "args": {"filename": filename}}]
            raw = json.dumps(heuristic)
            return heuristic, raw, prompt

        raw = llm.generate(prompt, system=STRUCTURED_SYSTEM, temperature=0.1)
        actions = parse_actions(raw)
        return [a.__dict__ for a in actions], raw, prompt
    except Exception:
        return [], "", prompt


def estimate_confidence(raw_structured: str) -> float:
    # Very simple heuristic: longer valid JSON -> higher confidence
    try:
        data = json.loads(raw_structured)
        if isinstance(data, list):
            return min(1.0, 0.3 + 0.2 * len(data))
        if isinstance(data, dict):
            return 0.5
        return 0.2
    except Exception:
        return 0.0
