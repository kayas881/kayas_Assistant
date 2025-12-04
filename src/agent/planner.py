from __future__ import annotations

from typing import List, Tuple
import json
from urllib.parse import quote_plus
import re

from .llm import LLM
from .config import preferred_search_base, default_notes_filename
from .actions import parse_actions
from .plan_candidate import PlanCandidate, compute_risk_score, estimate_time
from ..training.preference_model import score_plan


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
        # Heuristic: read Notepad content for "what's on my screen"/define/read/summarize intents
        g_screen = goal.lower()
        if ("notepad" in g_screen) and (
            "what is on my screen" in g_screen or
            "what's on my screen" in g_screen or
            "define" in g_screen or
            "read" in g_screen or
            "summarize" in g_screen
        ):
            heuristic = [
                {"tool": "uia.read_text", "args": {"window_title": "Notepad"}}
            ]
            raw = json.dumps(heuristic)
            print("[Planner] Using Notepad read heuristic -> uia.read_text Notepad")
            return heuristic, raw, prompt

        # Heuristic: open Notepad, type, and save as <filename>.txt
        g = goal.lower()
        if ("notepad" in g) and ("write" in g or "type" in g) and ("save" in g) and (".txt" in g):
            # Extract the text to type (before 'save')
            mtxt = re.search(r"(?:write|type)\s+(.+?)(?:\s+and\s+save|\s+then\s+save|\s+save|$)", goal, re.IGNORECASE)
            text_to_type = None
            if mtxt:
                text_to_type = mtxt.group(1).strip().strip('"').strip("'")
            # Extract filename after 'save ... as'
            mfile = re.search(r"save(?:\s+it|\s+this)?(?:\s+as)?\s+([\w.\- ]+\.txt)\b", goal, re.IGNORECASE)
            filename = (mfile.group(1).strip() if mfile else "notes.txt")
            type_text = text_to_type or "hello"
            heuristic = [
                {"tool": "process.start_program", "args": {"program": "notepad.exe", "background": True}},
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 1200}}], "stop_on_error": True}},
                {"tool": "uia.type_text", "args": {"window_title": "Untitled - Notepad", "text": type_text}},
                {"tool": "desktop.run_steps", "args": {"steps": [
                    {"action": "hotkey", "args": {"keys": ["ctrl", "s"]}},
                    {"action": "sleep", "args": {"ms": 600}},
                    {"action": "write", "args": {"text": filename}},
                    {"action": "sleep", "args": {"ms": 300}},
                    {"action": "hotkey", "args": {"keys": ["enter"]}}
                ], "stop_on_error": True}}
            ]
            raw = json.dumps(heuristic)
            print(f"[Planner] Using Notepad save heuristic -> filename: {filename}")
            return heuristic, raw, prompt

        # Heuristic: open Notepad and type some text
        # Only use this for simple typing WITHOUT save/close instructions
        has_save = "save" in g or "save as" in g or "close" in g
        if ("notepad" in g) and ("write" in g or "type" in g) and not has_save:
            # Extract the text to type after the word write/type
            # Stop extraction at common follow-up words like "and save", "then save", etc.
            mtxt = re.search(r"(?:write|type)\s+(.+?)(?:\s+and\s+|\s+then\s+|$)", goal, re.IGNORECASE)
            text_to_type = None
            if mtxt:
                text_to_type = mtxt.group(1).strip().strip('"').strip("'")
            # Build a two-step plan: start notepad, then type into it
            # Notepad window commonly titled 'Untitled - Notepad' on fresh instance
            type_text = text_to_type or "hello"
            heuristic = [
                {"tool": "process.start_program", "args": {"program": "notepad.exe", "background": True}},
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 1200}}], "stop_on_error": True}},
                {"tool": "uia.type_text", "args": {"window_title": "Untitled - Notepad", "text": type_text}}
            ]
            raw = json.dumps(heuristic)
            return heuristic, raw, prompt

        # Heuristic: explicit file write with exact text to a path
        # Detect phrases like: "Write to path artifacts/hf_test.txt the exact text: hello" or
        # "Write to file 'artifacts/hf_test.txt' content: 'hello'"
        # BUT skip if this looks like a Notepad UI automation task
        g_lower = goal.lower()
        is_notepad_ui_task = "notepad" in g_lower and ("open" in g_lower or "start" in g_lower or "launch" in g_lower)
        if any(k in g_lower for k in ["write", "create"]) and (".txt" in g_lower or "/" in goal or "\\" in goal) and not is_notepad_ui_task:
            # Try to extract filename
            filename = None
            mq = re.search(r"'([^']+)'|\"([^\"]+)\"", goal)
            if mq:
                cand = mq.group(1) or mq.group(2)
                # prefer candidates that look like paths or have an extension
                if any(ch in cand for ch in ["/", "\\"]) or re.search(r"\.[A-Za-z0-9]{1,6}$", cand):
                    filename = cand
            if not filename:
                mpath = re.search(r"(?:path|file|filename|as)\s+([\w.\-]+\.[A-Za-z0-9]{1,6})\b", goal, re.IGNORECASE)
                if mpath:
                    filename = mpath.group(1).strip()
            if not filename:
                # fallback: simple word.ext pattern
                mext = re.search(r"\b([\w.\-]+\.[A-Za-z0-9]{1,6})\b", goal)
                if mext:
                    filename = mext.group(1).strip()

            # Extract exact content if specified
            content = None
            # Look for explicit markers like "content:", "text:", or quoted strings
            mcontent = re.search(r"(?i)(exact\s+text|text|content)\s*:\s*(.*)$", goal)
            if mcontent:
                content_raw = mcontent.group(2)
                # Stop at common boundary hints
                for stopper in ["Do not", "Don't", "Only", "No other", "and then", "then "]:
                    idx = content_raw.find(stopper)
                    if idx != -1:
                        content_raw = content_raw[:idx]
                        break
                content_raw = content_raw.strip().strip()
                # Strip surrounding quotes if present
                if (content_raw.startswith("'") and "'" in content_raw[1:]):
                    content = content_raw.strip()
                    content = content[1:content.rfind("'")]
                elif (content_raw.startswith('"') and '"' in content_raw[1:]):
                    content = content_raw.strip()
                    content = content[1:content.rfind('"')]
                else:
                    # Keep trailing punctuation
                    content = content_raw.strip().rstrip()
            
            # Also try to extract quoted content anywhere in the goal
            # Patterns: write 'text' to file, create file with 'text', etc.
            if not content:
                # Try single quotes
                mquote = re.search(r"'([^']+)'", goal)
                if mquote:
                    content = mquote.group(1)
                else:
                    # Try double quotes
                    mquote2 = re.search(r'"([^"]+)"', goal)
                    if mquote2:
                        content = mquote2.group(1)

            if filename and content is not None:
                heuristic = [{"tool": "filesystem.create_file", "args": {"filename": filename, "content": content}}]
                raw = json.dumps(heuristic)
                print(f"[Planner] Using file-write heuristic: {filename}")
                return heuristic, raw, prompt
            elif filename:
                print(f"[Planner] Found filename '{filename}' but no explicit content; falling through to LLM")

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
        has_followup = any(word in g for word in ["write", "type", "click", "select", "fill", "enter", "submit", "search"])
        
        if simple_open and not has_followup:
            # Extract program name
            program = "chrome.exe" if "chrome" in g else "firefox.exe" if "firefox" in g else "msedge.exe" if "edge" in g else "notepad.exe" if "notepad" in g else "code.exe" if "vscode" in g else "spotify.exe" if "spotify" in g else "slack.exe" if "slack" in g else "chrome.exe"
            
            # If also mentions search/google, open browser with search URL directly (no automation to avoid CAPTCHA)
            if "search" in g or "google" in g:
                search_query = re.sub(r'\b(open|start|launch|chrome|firefox|edge|browser|and|then|for|search|google)\b', '', g, flags=re.IGNORECASE).strip()
                if search_query:
                    search_url = f"https://www.google.com/search?q={quote_plus(search_query)}"
                else:
                    # No query provided; open Google homepage to allow the user to type
                    search_url = "https://www.google.com/"
                heuristic = [{"tool": "process.start_program", "args": {"program": program, "args": [search_url], "background": True}}]
            else:
                heuristic = [{"tool": "process.start_program", "args": {"program": program, "background": True}}]
            
            raw = json.dumps(heuristic)
            return heuristic, raw, prompt

        # Heuristic: web search with browser automation when explicitly mentioned
        if ("search" in g) and any(word in g for word in ["open", "chrome", "firefox", "edge", "browser"]):
            # Build a robust Playwright flow using browser.run_steps
            query_match = re.search(r"search\s+(for\s+)?(.+?)(?:\.|,|;|$)", goal, flags=re.IGNORECASE)
            query = query_match.group(2).strip() if query_match else goal
            steps = [
                {"action": "goto", "args": {"url": "https://www.google.com"}},
                {"action": "wait_for_selector", "args": {"selector": 'input[name="q"]', "state": "visible"}},
                {"action": "fill", "args": {"selector": 'input[name="q"]', "value": query}},
                {"action": "press", "args": {"selector": 'input[name="q"]', "key": "Enter"}},
                {"action": "wait_for_selector", "args": {"selector": "#search", "state": "visible"}},
                {"action": "extract_text", "args": {"selector": "#search", "all": False}},
            ]
            heuristic = [{"tool": "browser.run_steps", "args": {"steps": steps, "headless": True, "stop_on_error": True}}]
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

        print(f"[Planner] No heuristic matched; invoking LLM for structured planning")
        raw = llm.generate(prompt, system=STRUCTURED_SYSTEM, temperature=0.1)
        print(f"[Planner] LLM returned: {raw[:200]}...")
        actions = parse_actions(raw)
        print(f"[Planner] Parsed {len(actions)} actions")
        return [a.__dict__ for a in actions], raw, prompt
    except Exception as e:
        print(f"[Planner] Structured planning failed: {type(e).__name__}: {e}")
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


def plan_candidates(llm: LLM, goal: str, k: int = 3, reuse_filename: str | None = None, feedback_hints: str = "") -> List[PlanCandidate]:
    """
    Generate k candidate plans for the goal, ranked by overall_score().
    
    Returns a list of PlanCandidate sorted by descending overall_score (best first).
    """
    candidates: List[PlanCandidate] = []
    
    # Strategy 1: Heuristic-based plan (fast, high confidence if applicable)
    heuristic_actions, heuristic_raw, heuristic_prompt = plan_structured(llm, goal, reuse_filename, feedback_hints)
    if heuristic_actions:
        # Check if this was a heuristic (by checking for debug print marker or simple heuristic patterns)
        is_heuristic = any(
            action.get("tool", "").startswith(("process.start_program", "filesystem.create_file"))
            for action in heuristic_actions
        ) and len(heuristic_actions) <= 5
        
        risk = compute_risk_score(heuristic_actions)
        time_est = estimate_time(heuristic_actions)
        
        # Try to score with preference model
        try:
            pref_score = score_plan(heuristic_prompt, heuristic_raw)
            # Boost heuristic scores since they're precisely matched
            if is_heuristic and pref_score < 0.7:
                pref_score = max(0.7, pref_score)
        except Exception:
            pref_score = 0.75 if is_heuristic else 0.5
        
        candidates.append(PlanCandidate(
            actions=heuristic_actions,
            strategy_name="heuristic" if is_heuristic else "llm_primary",
            risk_score=risk,
            step_count=len(heuristic_actions),
            estimated_time_sec=time_est,
            confidence=pref_score,
            raw_llm_output=heuristic_raw,
            prompt_used=heuristic_prompt,
        ))
    
    # Strategy 2: Alternative LLM plan with higher temperature (more creative/risky)
    if k > 1:
        alt_prompt = f"{goal}\n\nProvide an alternative approach using different tools or methods."
        try:
            alt_system = STRUCTURED_SYSTEM + "\nGenerate a different strategy than the most obvious one."
            alt_raw = llm.generate(alt_prompt, system=alt_system, temperature=0.3)
            alt_actions_obj = parse_actions(alt_raw)
            alt_actions = [a.__dict__ for a in alt_actions_obj]
            
            if alt_actions and alt_actions != heuristic_actions:
                risk_alt = compute_risk_score(alt_actions)
                time_alt = estimate_time(alt_actions)
                try:
                    pref_alt = score_plan(alt_prompt, alt_raw)
                except Exception:
                    pref_alt = 0.4
                
                candidates.append(PlanCandidate(
                    actions=alt_actions,
                    strategy_name="llm_alternative",
                    risk_score=risk_alt,
                    step_count=len(alt_actions),
                    estimated_time_sec=time_alt,
                    confidence=pref_alt,
                    raw_llm_output=alt_raw,
                    prompt_used=alt_prompt,
                ))
        except Exception as e:
            print(f"[Planner] Alternative plan generation failed: {e}")
    
    # Strategy 3: Conservative fallback (filesystem-only for safe execution)
    # Only use as last resort - lower confidence so primary plans are tried first
    if k > 2:
        # Build a simple filesystem-based plan
        try:
            fallback_actions = [
                {"tool": "web.fetch", "args": {"url": f"https://www.google.com/search?q={quote_plus(goal)}"}},
                {"tool": "filesystem.create_file", "args": {"filename": reuse_filename or "notes.txt", "content": f"Goal: {goal}\n\nPlease check the fetched content."}}
            ]
            risk_fb = compute_risk_score(fallback_actions)
            time_fb = estimate_time(fallback_actions)
            
            candidates.append(PlanCandidate(
                actions=fallback_actions,
                strategy_name="conservative_fallback",
                risk_score=risk_fb,
                step_count=len(fallback_actions),
                estimated_time_sec=time_fb,
                confidence=0.3,  # Low confidence - only use as fallback
                raw_llm_output="",
                prompt_used="",
            ))
        except Exception:
            pass
    
    # Rank by overall_score (descending)
    candidates.sort(key=lambda c: c.overall_score(), reverse=True)
    
    print(f"[Planner] Generated {len(candidates)} candidate plans:")
    for i, cand in enumerate(candidates):
        print(f"  {i+1}. {cand.strategy_name}: {cand.step_count} steps, risk={cand.risk_score:.2f}, conf={cand.confidence:.2f}, score={cand.overall_score():.2f}")
    
    return candidates[:k]
