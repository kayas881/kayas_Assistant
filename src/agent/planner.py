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
    "You are a JSON-only planner. Respond with VALID JSON ONLY. No explanations, no markdown, no extra text.\n\n"
    "Output format: either a single object {\"tool\": \"name\", \"args\": {...}} or an array of such objects.\n\n"
    "Example valid response:\n"
    "[{\"tool\": \"web.fetch\", \"args\": {\"url\": \"https://google.com/search?q=freelancing+trends\"}}, "
    "{\"tool\": \"filesystem.create_file\", \"args\": {\"filename\": \"notes.txt\", \"content\": \"Summary here\"}}]\n\n"
    "Example for opening program and typing:\n"
    "[{\"tool\": \"process.start_program\", \"args\": {\"program\": \"notepad.exe\", \"background\": true}}, "
    "{\"tool\": \"uia.type_text\", \"args\": {\"window_title\": \"Notepad\", \"text\": \"hello world\"}}]\n\n"
    "Available tools:\n"
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
    "- spotify.play_query {query, device_id?}\n"
    "- spotify.get_current_playing {}\n"
    "- spotify.pause_playback {device_id?}\n"
    "- spotify.resume_playback {device_id?}\n"
    "- spotify.get_user_playlists {limit?}\n"
    "- spotify.create_playlist {name, description?, public?}\n"
    "- spotify.add_tracks_to_playlist {playlist_id, track_uris}\n"
    "- browser.run_steps {steps, headless?, base_url?, stop_on_error?} (steps: [{action, args} where action in [goto, click, fill, type, press, wait_for_selector, wait, extract_text, screenshot])\n"
    "- desktop.run_steps {steps, stop_on_error?} (steps: actions [sleep, move_to, click, double_click, write, hotkey, screenshot, locate_on_screen, click_image, ocr_region, locate_by_text])\n"
    "- process.run_command {command, timeout?, shell?, working_dir?}\n"
    "- process.start_program {program, args?, background?, process_id?}\n"
    "- process.kill_process {process_id?, pid?, name?}\n"
    "- process.list_processes {filter_name?}\n"
    "- process.get_system_info {}\n"
    "- clipboard.copy_text {text, add_to_history?}\n"
    "- clipboard.paste_text {}\n"
    "- clipboard.copy_image {image_path?, add_to_history?}\n"
    "- clipboard.paste_image {save_path?}\n"
    "- clipboard.get_history {limit?}\n"
    "- clipboard.clear_history {}\n"
    "- network.http_request {url, method?, headers?, data?, json?, params?, timeout?}\n"
    "- network.download_file {url, save_path, chunk_size?, show_progress?}\n"
    "- network.upload_file {url, file_path, field_name?, additional_data?}\n"
    "- network.get_url_info {url}\n"
    "- network.check_connectivity {hosts?}\n"
    "- filewatcher.watch_directory {path, watch_id?}\n"
    "- filewatcher.stop_watching {watch_id}\n"
    "- filewatcher.get_active_watches {}\n"
    "- filewatcher.get_event_log {watch_id?, limit?}\n"
    "- filewatcher.clear_event_log {}\n"
    "- llm.generate {prompt, system?, temperature?, max_tokens?}\n"
    "- llm.chat {messages, system?, temperature?, max_tokens?}\n"
    "- llm.summarize {text, max_length?}\n"
    "- llm.chain_of_thought {problem, steps?}\n"
    "- llm.few_shot_learning {examples, query}\n"
    "- llm.embeddings {texts}\n"
    "Phase 1: UI Automation (Layer A - Windows native APIs):\n"
    "- uia.find_window {title?, class_name?, process_id?, best_match?}\n"
    "- uia.list_windows {}\n"
    "- uia.click_button {window_title, button_text?, button_id?, button_class?}\n"
    "- uia.type_text {window_title, text, control_id?, control_type?}\n"
    "- uia.read_text {window_title, control_id?}\n"
    "- uia.get_menu_items {window_title}\n"
    "- uia.click_menu_item {window_title, menu_path}\n"
    "- uia.focus_window {window_title}\n"
    "- uia.close_window {window_title}\n"
    "- uia.get_control_tree {window_title}\n"
    "Phase 1: OCR (Layer D - visual fallback):\n"
    "- ocr.find_text {text, region?, case_sensitive?}\n"
    "- ocr.click_text {text, region?, button?, clicks?}\n"
    "- ocr.read_screen {region?}\n"
    "- ocr.wait_for_text {text, timeout?, region?}\n"
    "- ocr.get_text_near {x, y, radius?}\n"
    "- ocr.find_buttons {region?}\n"
    "Phase 1: Computer Vision (Layer C - image/template matching):\n"
    "- cv.find_image {template_path, confidence?, region?, multi_match?}\n"
    "- cv.click_image {template_path, confidence?, region?, button?, clicks?}\n"
    "- cv.wait_for_image {template_path, timeout?, confidence?, region?}\n"
    "- cv.find_by_feature {template_path, region?, min_matches?}\n"
    "- cv.find_by_color {color_range, region?, min_area?}\n"
    "- cv.screenshot {filename, region?}\n"
    "Phase 1: Perception Engine (smart tools - try all layers automatically):\n"
    "- perception.smart_click {target, context?}\n"
    "- perception.smart_type {text, context?}\n"
    "- perception.smart_read {context?}\n"
    "- perception.find_element {description, context?}\n"
    "- perception.get_capabilities {}\n"
    "Rules: prefer minimal steps; don't repeat work; use append_file not create if file already exists (if told). "
    "For UI interactions, prefer perception.* tools as they try multiple methods automatically. "
    "Use cv.* tools when you have a template image to match."
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

        # Heuristic: open/start a program (browser, app, etc.)
        # Only use this heuristic if it's a SIMPLE open command without complex follow-up actions
        g = goal.lower()
        simple_open = ("open" in g or "start" in g or "launch" in g) and any(app in g for app in ["chrome", "firefox", "edge", "browser", "notepad", "vscode", "spotify", "slack"])
        has_followup = any(word in g for word in ["write", "type", "click", "select", "fill", "enter", "submit"])
        
        if simple_open and not has_followup:
            # Extract program name
            program = "chrome.exe" if "chrome" in g else "firefox.exe" if "firefox" in g else "msedge.exe" if "edge" in g else "notepad.exe" if "notepad" in g else "code.exe" if "vscode" in g else "spotify.exe" if "spotify" in g else "slack.exe" if "slack" in g else "chrome.exe"
            
            # If also mentions search/google, open browser with search URL directly (no automation to avoid CAPTCHA)
            if "search" in g or "google" in g:
                search_query = re.sub(r'\b(open|start|launch|chrome|firefox|edge|browser|and|then|for|search|google)\b', '', g, flags=re.IGNORECASE).strip()
                if search_query:
                    search_url = f"https://www.google.com/search?q={quote_plus(search_query)}"
                    heuristic = [{"tool": "process.start_program", "args": {"program": program, "args": [search_url], "background": True}}]
                else:
                    heuristic = [{"tool": "process.start_program", "args": {"program": program, "background": True}}]
            else:
                heuristic = [{"tool": "process.start_program", "args": {"program": program, "background": True}}]
            
            raw = json.dumps(heuristic)
            return heuristic, raw, prompt

        # Heuristic: web search (only if NOT opening a browser)
        if ("search" in g or "trends" in g or "latest" in g) and not any(word in g for word in ["open", "chrome", "firefox", "browser"]):
            # Build a search URL
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
