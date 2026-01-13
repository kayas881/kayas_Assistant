from __future__ import annotations

from typing import List, Tuple
import json
from urllib.parse import quote_plus
import re
from pathlib import Path

from .llm import LLM
from .config import preferred_search_base, default_notes_filename
from .actions import parse_actions
from .plan_candidate import PlanCandidate, compute_risk_score, estimate_time
from ..training.preference_model import score_plan
from .personality import get_planner_prompt


PLANNER_SYSTEM = get_planner_prompt()


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
    "[{\"tool\": \"web.answer\", \"args\": {\"question\": \"best Python web frameworks\", \"search_queries\": [\"best Python web frameworks 2025\", \"Django vs FastAPI comparison\"], \"max_sources\": 8}}]\n\n"
    "Example for opening program and typing:\n"
    "[{\"tool\": \"process.start_program\", \"args\": {\"program\": \"notepad.exe\", \"background\": true}}, "
    "{\"tool\": \"uia.type_text\", \"args\": {\"window_title\": \"Notepad\", \"text\": \"hello world\"}}]\n\n"
    "Available tools:\n"
    "- filesystem.create_file {filename, content?}\n"
    "- filesystem.create_folder {path}\n"
    "- filesystem.rename {path, new_name}\n"
    "- filesystem.append_file {filename, content}\n"
    "WEB RESEARCH (Comet-style - use for ANY question requiring web information):\n"
    "- web.deep_research {question, max_iterations?, sources_per_query?} (BEST: iterative evidence-based research with claim verification and confidence scoring)\n"
    "- web.answer {question, search_queries?, max_sources?, temperature?, max_tokens?} (ONE-STEP: runs research + synthesizes a final answer with inline citations)\n"
    "- web.research {question, search_queries?, max_sources?} (returns extracted sources and content for manual synthesis)\n"
    "  - Provide search_queries array with 2-3 different search angles for comprehensive research\n"
    "  - Returns sources with title, url, domain, content ready for citation\n"
    "- web.search {query, max_results?} (simple search, returns [{title, url, snippet}, ...])\n"
    "- web.fetch {url} (fetch single page)\n"
    "- web.extract_main_text {url, max_chars?} (extract article text from single URL)\n"
    "For question-shaped requests (what/why/how/best/compare): Prefer web.deep_research for comprehensive answers with confidence scoring, or web.answer for faster results.\n"
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
    "- browser.open_chrome_profile {profile_name, chrome_path?, background?} (use this to open Chrome with a specific profile instead of perception clicks)\n"
    "- app.open_spotify {path?, flags?, background?} (launch Spotify deterministically before media controls)\n"
    "- messaging.send_to_contact {name, message, web_url?, headless?, stop_on_error?} (preferred over perception for quick messaging)\n"
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
    "WhatsApp Web automation (session-persistent, scan QR once):\n"
    "- whatsapp.initialize {} (opens browser and navigates to WhatsApp Web; shows QR if not logged in)\n"
    "- whatsapp.send_message {contact, message} (send a text message to a contact or group by name)\n"
    "- whatsapp.read_messages {contact, limit?} (read recent messages from a chat)\n"
    "- whatsapp.get_unread_chats {} (list all chats with unread messages)\n"
    "- whatsapp.send_image {contact, image_path, caption?} (send an image with optional caption)\n"
    "- whatsapp.send_video {contact, video_path, caption?} (send a video with optional caption)\n"
    "- whatsapp.send_document {contact, file_path, caption?} (send any file/document)\n"
    "- whatsapp.get_all_chats {limit?} (list all visible chats with preview)\n"
    "- whatsapp.get_chat_info {contact} (get info about a contact or group)\n"
    "- whatsapp.get_contact_info {contact} (get detailed contact info including about/status)\n"
    "- whatsapp.get_last_seen {contact} (check if contact is online or last seen time)\n"
    "- whatsapp.mark_as_read {contact} (mark a chat as read)\n"
    "- whatsapp.mute_chat {contact, duration?} (mute notifications: '8 hours', '1 week', 'always')\n"
    "- whatsapp.unmute_chat {contact} (unmute notifications)\n"
    "- whatsapp.archive_chat {contact} (archive a chat)\n"
    "- whatsapp.pin_chat {contact} (pin a chat to top)\n"
    "- whatsapp.unpin_chat {contact} (unpin a chat)\n"
    "- whatsapp.clear_chat {contact, keep_starred?} (clear chat history)\n"
    "- whatsapp.delete_chat {contact} (delete a chat completely)\n"
    "- whatsapp.block_contact {contact} (block a contact)\n"
    "- whatsapp.unblock_contact {contact} (unblock a contact)\n"
    "- whatsapp.forward_message {from_contact, to_contact, message_index?} (forward a message)\n"
    "- whatsapp.reply_to_message {contact, reply_text, message_index?} (reply to a specific message)\n"
    "- whatsapp.delete_message {contact, message_index?, for_everyone?} (delete a sent message)\n"
    "- whatsapp.star_message {contact, message_index?} (star/unstar a message)\n"
    "- whatsapp.search_messages {query, contact?} (search for messages globally or in a chat)\n"
    "- whatsapp.create_group {group_name, members} (create a new group with members list)\n"
    "- whatsapp.add_to_group {group_name, members} (add members to existing group)\n"
    "- whatsapp.leave_group {group_name} (leave a group)\n"
    "- whatsapp.send_location {contact} (share current location)\n"
    "- whatsapp.send_contact {to_contact, share_contact} (share a contact with someone)\n"
    "- whatsapp.screenshot {filename?} (screenshot current WhatsApp Web state)\n"
    "- whatsapp.close {} (close the browser)\n"
    "File Explorer automation (Windows Explorer control):\n"
    "- explorer.open {path?} (open File Explorer, optionally at a path)\n"
    "- explorer.navigate {path} (navigate current explorer to a path)\n"
    "- explorer.close {} (close explorer window)\n"
    "- explorer.create_folder {name, path?} (create a new folder)\n"
    "- explorer.create_file {name, file_type?, path?} (create new file via context menu)\n"
    "- explorer.select_file {name} (select a file/folder by name)\n"
    "- explorer.select_all {} (select all items)\n"
    "- explorer.copy {} (copy selected items)\n"
    "- explorer.cut {} (cut selected items)\n"
    "- explorer.paste {} (paste from clipboard)\n"
    "- explorer.rename {old_name, new_name} (rename a file/folder)\n"
    "- explorer.delete {name?, permanent?} (delete selected/named item)\n"
    "- explorer.open_file {name} (open file with default app)\n"
    "- explorer.properties {name?} (show properties dialog)\n"
    "- explorer.back {} (navigate back)\n"
    "- explorer.forward {} (navigate forward)\n"
    "- explorer.up {} (go to parent folder)\n"
    "- explorer.refresh {} (refresh current view)\n"
    "- explorer.set_view {mode} (details, list, tiles, large_icons, etc.)\n"
    "- explorer.search {query, path?} (search for files)\n"
    "- explorer.quick_access {} (go to Quick Access)\n"
    "- explorer.this_pc {} (go to This PC)\n"
    "- explorer.desktop {} (go to Desktop folder)\n"
    "- explorer.documents {} (go to Documents)\n"
    "- explorer.downloads {} (go to Downloads)\n"
    "- explorer.pictures {} (go to Pictures)\n"
    "- explorer.recycle_bin {} (go to Recycle Bin)\n"
    "- explorer.copy_path {name?} (copy path to clipboard)\n"
    "- explorer.open_terminal {path?} (open terminal here)\n"
    "- explorer.undo {} (undo last action)\n"
    "- explorer.list {path} (list folder contents directly, no UI)\n"
    "- explorer.file_info {path} (get file/folder info directly)\n"
    "- explorer.move {source, destination} (move file/folder directly)\n"
    "- explorer.copy_file {source, destination} (copy file/folder directly)\n"
    "- explorer.delete_direct {path, permanent?} (delete directly, no UI)\n"
    "Rules: prefer minimal steps; don't repeat work; use append_file not create if file already exists (if told). "
    "Prefer smart-default tools for known apps (Chrome profiles, Spotify launch, messaging) before using perception.* or generic clicks. "
    "For WhatsApp tasks, use whatsapp.* tools directly - they are more reliable than browser automation. "
    "For UI interactions not covered by smart defaults, prefer perception.* tools as they try multiple methods automatically. "
    "Use cv.* tools when you have a template image to match."
)


def plan_structured(llm: LLM, goal: str, reuse_filename: str | None = None, feedback_hints: str = "") -> Tuple[List[dict], str, str]:
    hint = f"A file named {reuse_filename} already exists; avoid recreating it and use append_file if you need to add content.\n" if reuse_filename else ""
    fb = f"User preferences and corrections (guidance):\n{feedback_hints}\n" if feedback_hints else ""
    prompt = f"Goal: {goal}\n{hint}{fb}Emit JSON tool calls only, no extra text."
    try:
        g = goal.lower()
        # Smart defaults heuristics -------------------------------------------------
        
        # ========== WHATSAPP SEND MESSAGE (early check - works without 'whatsapp' keyword) ==========
        # Pattern: "send message to X saying Y" or "message X saying Y" or "send message on whatsapp to X saying Y"
        if ("send" in g or "message" in g) and ("saying" in g or "that" in g or "with" in g):
            # Parse: "send message to Contact saying message" or "message Contact saying text"
            # Also handle "send message on whatsapp to X saying Y" by removing "on whatsapp" first
            goal_cleaned = re.sub(r"\s+on\s+whatsapp", "", goal, flags=re.IGNORECASE)
            send_match = re.search(r"(?:send\s+)?(?:a\s+)?(?:message|msg|text)\s+(?:to\s+)?([A-Za-z][A-Za-z0-9_\s]*?)\s+(?:saying|that|with)\s+(.+)$", goal_cleaned, re.IGNORECASE)
            if send_match:
                contact = send_match.group(1).strip()
                message = send_match.group(2).strip().strip('"').strip("'")
                # Remove "my friend" prefix if present
                contact = re.sub(r"^(?:my\s+)?(?:friend\s+|buddy\s+|mate\s+)?", "", contact, flags=re.IGNORECASE).strip()
                if contact and message:
                    heuristic = [{"tool": "whatsapp.send_message", "args": {"contact": contact, "message": message}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp send message heuristic -> {contact}: {message}")
                    return heuristic, raw, prompt
        
        # ========== WHATSAPP REPLY (early check - works without 'whatsapp' keyword) ==========
        # Pattern: "reply to X saying Y" or "tell X Y"
        if "reply" in g or "tell" in g:
            # Try: "reply to Contact saying message" or "tell Contact message"
            reply_match = re.search(r"(?:reply|tell)\s+(?:to\s+)?([A-Za-z][A-Za-z0-9_\s]*?)(?:\s+(?:saying|that|with|:)\s+|\s+)(.+)$", goal, re.IGNORECASE)
            if reply_match:
                contact = reply_match.group(1).strip()
                reply_text = reply_match.group(2).strip().strip('"').strip("'")
                if contact and reply_text:
                    heuristic = [{"tool": "whatsapp.reply_to_message", "args": {"contact": contact, "reply_text": reply_text}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp reply heuristic -> {contact}: {reply_text}")
                    return heuristic, raw, prompt
        
        # ========== WHATSAPP SEARCH (early check - 'search for X in Contact on whatsapp') ==========
        # Pattern: "search for query in contact on whatsapp"
        if ("search" in g or "find" in g) and "whatsapp" in g and " in " in g:
            search_match = re.search(r"(?:search\s+(?:for\s+)?|find\s+)(.+?)\s+(?:in|from)\s+([A-Za-z][A-Za-z0-9_\s]*?)(?:\s+on\s+whatsapp)?$", goal, re.IGNORECASE)
            if search_match:
                query = search_match.group(1).strip().strip('"').strip("'")
                contact = search_match.group(2).strip()
                if query and contact:
                    heuristic = [{"tool": "whatsapp.search_messages", "args": {"query": query, "contact": contact}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp search heuristic -> '{query}' in {contact}")
                    return heuristic, raw, prompt
        
        if ("chrome" in g) and ("profile" in g):
            mprof = re.search(r"profile\s+(?:named|called)?\s*([\w\- ]+)", goal, re.IGNORECASE)
            profile_name = mprof.group(1).strip() if mprof else "Default"
            # Map friendly names to actual Chrome profile directories
            profile_map = {
                "kayas": "profile 2",
                "kayas profile": "profile 2",
                "kayass": "profile 2",
            }
            key = profile_name.lower()
            if key in profile_map:
                profile_name = profile_map[key]
            heuristic = [{"tool": "browser.open_chrome_profile", "args": {"profile_name": profile_name}}]
            raw = json.dumps(heuristic)
            print(f"[Planner] Using chrome profile heuristic -> {profile_name}")
            return heuristic, raw, prompt

        if "spotify" in g and ("play" in g or "start" in g or "open" in g):
            mtrack = re.search(r"play\s+([\w ']+)", goal, re.IGNORECASE)
            query = mtrack.group(1).strip() if mtrack else ""
            heuristic = [
                {"tool": "app.open_spotify", "args": {}},
                {"tool": "spotify.play_query", "args": {"query": query or "music"}},
            ]
            raw = json.dumps(heuristic)
            print("[Planner] Using Spotify heuristic")
            return heuristic, raw, prompt

        # ========== QUESTION-SHAPED QUERIES → WEB.DEEP_RESEARCH ==========
        # If the goal is likely a question, route to deep_research for iterative evidence-based research
        # BUT skip if it looks like a WhatsApp reply (already handled above)
        is_whatsapp_reply = ("reply" in g or "tell" in g) and ("saying" in g or "that" in g or "with" in g)
        q_like = (
            not is_whatsapp_reply and (
                g.strip().endswith("?") or
                bool(re.match(r"^(what|why|how|which|who|when|where|best|top|compare|alternatives|pros and cons)\b", g)) or
                ("compare" in g or " vs " in g)
            )
        )
        if q_like:
            # Use deep_research for comprehensive, confidence-scored answers
            base = goal.strip().rstrip("?.! ")
            heuristic = [{"tool": "web.deep_research", "args": {"question": base, "max_iterations": 3, "sources_per_query": 4}}]
            raw = json.dumps(heuristic)
            print(f"[Planner] Using web.deep_research heuristic -> {base}")
            return heuristic, raw, prompt

        # ========== SEARCH HEURISTICS (before explorer navigation to avoid conflicts) ==========
        # Heuristic: search intent - distinguish between local file/folder search vs web search
        search_match = re.search(r"(?:search for|search about|find|lookup)\s+(.+)", goal, re.IGNORECASE)
        if search_match:
            query_raw = search_match.group(1).strip()
            
            # Check if this is a local file/folder search (has location hints like "in D drive", "in Desktop", etc.)
            local_search_indicators = [
                r"\bin\s+([A-Za-z])\s+drive\b",  # "in D drive"
                r"\bin\s+([A-Za-z]):\b",  # "in D:"
                r"\bin\s+(desktop|downloads|documents|pictures|music|videos)\b",  # known folders
                r"\bfolder\b",  # mentions folder
                r"\bfile\b",  # mentions file
            ]
            
            is_local_search = any(re.search(pattern, query_raw, re.IGNORECASE) for pattern in local_search_indicators)
            
            if is_local_search:
                # Extract search query and location
                query_clean = query_raw
                location_hint = None
                
                # Extract location from patterns like "in D drive", "in Desktop", etc.
                drive_match = re.search(r"\bin\s+([A-Za-z])\s+drive\b", query_clean, re.IGNORECASE)
                if drive_match:
                    location_hint = f"{drive_match.group(1).upper()}:\\"
                    query_clean = re.sub(r"\bin\s+([A-Za-z])\s+drive\b", "", query_clean, flags=re.IGNORECASE).strip()
                else:
                    folder_match = re.search(r"\bin\s+(desktop|downloads|documents|pictures|music|videos)\b", query_clean, re.IGNORECASE)
                    if folder_match:
                        location_hint = folder_match.group(1)
                        query_clean = re.sub(r"\bin\s+(desktop|downloads|documents|pictures|music|videos)\b", "", query_clean, flags=re.IGNORECASE).strip()
                
                # Clean up query
                query_clean = query_clean.replace(" folder", "").replace(" file", "").strip()
                
                # Use explorer.find_items which supports location-based searching
                heuristic = [{"tool": "explorer.find_items", "args": {"query": query_clean, "location": location_hint}}]
                raw = json.dumps(heuristic)
                print(f"[Planner] Using explorer.find_items heuristic -> {query_clean} in {location_hint or 'current dir'}")
                return heuristic, raw, prompt
            
            # Otherwise, it's a web research - use Comet-style pipeline
            should_save = "save" in goal.lower() or "notepad" in goal.lower() or "file" in goal.lower()
            # Truncate at common follow-ups
            query_raw = re.split(r"\s+and\s+save|\s+then\s+save|\s+and\s+summarize|\s+save\b", query_raw, maxsplit=1)[0].strip()
            # Remove trailing punctuation/quotes
            query_raw = query_raw.strip("\"' .,")
            
            # Use web.research for comprehensive search with multiple queries
            # Generate a couple of search query variants for better coverage
            search_queries = [query_raw]
            # Add a variant if the query is complex enough
            if len(query_raw.split()) >= 3:
                search_queries.append(f"{query_raw} explained")
            
            heuristic = [{"tool": "web.research", "args": {"question": query_raw, "search_queries": search_queries, "max_sources": 8}}]
            
            # If user wants to save, append a file creation step with a descriptive filename
            if should_save:
                safe_query = re.sub(r"[^a-z0-9_\-]", "_", query_raw.lower())[:50]
                heuristic.append({
                    "tool": "filesystem.create_file",
                    "args": {
                        "filename": f"{safe_query}_results.txt",
                        "content": f"Research results for '{query_raw}' - content will be filled after extraction"
                    }
                })
            raw = json.dumps(heuristic)
            print(f"[Planner] Using web.research heuristic -> {query_raw}" + (" (with save)" if should_save else ""))
            return heuristic, raw, prompt

        # ========== FILE EXPLORER HEURISTICS (early match before LLM fallback) ==========
        explorer_keywords = ["explorer", "file explorer", "folder", "directory", "files", "this pc", "my computer"]
        is_explorer_intent = any(kw in g for kw in explorer_keywords)
        
        # Open specific folders (downloads, documents, desktop, etc.)
        # Do NOT let navigation heuristics steal create-folder, delete, open-file, copy, or move requests.
        # Also exclude if there's a file extension mentioned (e.g., ".pdf", ".docx")
        has_file_extension = bool(re.search(r"\.\w{2,4}\b", goal))  # matches .pdf, .docx, .txt, etc.
        if (is_explorer_intent or any(word in g for word in ["open", "go to", "show", "navigate"])) and "create" not in g and "make" not in g and ("delete" not in g and "remove" not in g) and "copy" not in g and "move" not in g and not has_file_extension and not (("open" in g or "launch" in g) and (" in " in g)):
            # Quick access locations - check these FIRST
            if "download" in g:
                heuristic = [{"tool": "explorer.downloads", "args": {}}]
                raw = json.dumps(heuristic)
                print("[Planner] Using Explorer downloads heuristic")
                return heuristic, raw, prompt
            
            if "document" in g and "send" not in g:  # avoid matching "send document"
                heuristic = [{"tool": "explorer.documents", "args": {}}]
                raw = json.dumps(heuristic)
                print("[Planner] Using Explorer documents heuristic")
                return heuristic, raw, prompt
            
            if "desktop" in g and "folder" in g:
                heuristic = [{"tool": "explorer.desktop", "args": {}}]
                raw = json.dumps(heuristic)
                print("[Planner] Using Explorer desktop heuristic")
                return heuristic, raw, prompt
            
            if "picture" in g or "photo" in g:
                heuristic = [{"tool": "explorer.pictures", "args": {}}]
                raw = json.dumps(heuristic)
                print("[Planner] Using Explorer pictures heuristic")
                return heuristic, raw, prompt
            
            if "music" in g:
                heuristic = [{"tool": "explorer.music", "args": {}}]
                raw = json.dumps(heuristic)
                print("[Planner] Using Explorer music heuristic")
                return heuristic, raw, prompt
            
            if "video" in g and "send" not in g:  # avoid matching "send video"
                heuristic = [{"tool": "explorer.videos", "args": {}}]
                raw = json.dumps(heuristic)
                print("[Planner] Using Explorer videos heuristic")
                return heuristic, raw, prompt
            
            if "recycle" in g or "trash" in g or "bin" in g:
                heuristic = [{"tool": "explorer.recycle_bin", "args": {}}]
                raw = json.dumps(heuristic)
                print("[Planner] Using Explorer recycle bin heuristic")
                return heuristic, raw, prompt
            
            if "quick access" in g:
                heuristic = [{"tool": "explorer.quick_access", "args": {}}]
                raw = json.dumps(heuristic)
                print("[Planner] Using Explorer quick access heuristic")
                return heuristic, raw, prompt
            
            if "this pc" in g or "my computer" in g:
                heuristic = [{"tool": "explorer.this_pc", "args": {}}]
                raw = json.dumps(heuristic)
                print("[Planner] Using Explorer this pc heuristic")
                return heuristic, raw, prompt
            
            # Open specific path (e.g., "open C:\Users\..." or "go to D:\Projects")
            path_match = re.search(r'(?:open|go to|navigate to|show)\s+([A-Za-z]:\\[^\s]+|[A-Za-z]:/[^\s]+)', goal, re.IGNORECASE)
            if path_match:
                path = path_match.group(1).strip()
                heuristic = [{"tool": "explorer.open", "args": {"path": path}}]
                raw = json.dumps(heuristic)
                print(f"[Planner] Using Explorer open path heuristic -> {path}")
                return heuristic, raw, prompt
            
            # Generic "open file explorer" or "open explorer"
            if "explorer" in g and any(word in g for word in ["open", "start", "launch"]):
                heuristic = [{"tool": "explorer.open", "args": {}}]
                raw = json.dumps(heuristic)
                print("[Planner] Using Explorer open heuristic")
                return heuristic, raw, prompt

        # Create-folder heuristic
        # - If the user specifies an absolute Windows path (e.g., "in C:\\Users"), create it there via explorer.
        # - Otherwise, create it under the artifacts root via filesystem.
        if ("create" in g or "make" in g) and ("folder" in g or "directory" in g):
            # Optional trailing location: allow drive letters (:) and backslashes.
            in_match = re.search(r"\b(?:in|inside|under)\s+([A-Za-z0-9_./\\:\- ]+)$", goal, re.IGNORECASE)
            subpath = in_match.group(1).strip().strip("\"'") if in_match else ""
            goal_no_loc = goal[: in_match.start()].strip() if in_match else goal

            folder_name: str | None = None
            # Prefer explicit quoted names.
            m = re.search(
                r"\b(?:folder|directory)\b\s*(?:named|called)?\s*[\"']([^\"']+)[\"']\s*$",
                goal_no_loc,
                re.IGNORECASE,
            )
            if m:
                folder_name = m.group(1).strip()
            if not folder_name:
                # Unquoted single-token names.
                m = re.search(
                    r"\b(?:folder|directory)\b\s*(?:named|called)?\s*([A-Za-z0-9_.\-]+)\s*$",
                    goal_no_loc,
                    re.IGNORECASE,
                )
                if m:
                    folder_name = m.group(1).strip()
            if not folder_name:
                # Fallback: "named X" / "called X"
                m = re.search(r"\b(?:named|called)\s+[\"']?([^\"']+)[\"']?\s*$", goal_no_loc, re.IGNORECASE)
                if m:
                    folder_name = m.group(1).strip()

            folder_name = (folder_name or "New Folder").strip(" .\t\n\r")

            # Absolute destination: create directly there.
            subpath_norm = subpath.strip()
            is_absolute_dest = bool(re.match(r"^[A-Za-z]:[\\/]", subpath_norm)) or subpath_norm.startswith("\\\\")
            known_locations = {
                "desktop",
                "downloads",
                "documents",
                "pictures",
                "music",
                "videos",
            }
            is_known_location = subpath_norm.lower() in known_locations

            if subpath_norm and (is_absolute_dest or is_known_location):
                heuristic = [{"tool": "explorer.create_folder", "args": {"name": folder_name, "path": subpath_norm}}]
                raw = json.dumps(heuristic)
                print(f"[Planner] Using explorer.create_folder heuristic -> {subpath_norm}\\{folder_name}")
                return heuristic, raw, prompt

            # Relative destination: interpret as artifacts subpath.
            rel_path = folder_name if not subpath_norm else str(Path(subpath_norm) / folder_name)
            heuristic = [{"tool": "filesystem.create_folder", "args": {"path": rel_path}}]
            raw = json.dumps(heuristic)
            print(f"[Planner] Using filesystem.create_folder heuristic -> {rel_path}")
            return heuristic, raw, prompt

        # Rename heuristic (files or folders). If an absolute or known location is provided, use explorer.rename; otherwise use filesystem.rename under artifacts.
        if "rename" in g and " to " in g:
            # Extract old/new names (prefer quoted).
            rename_match = re.search(r"rename\s+[\"']([^\"']+)[\"']\s+to\s+[\"']([^\"']+)[\"']", goal, re.IGNORECASE)
            if not rename_match:
                rename_match = re.search(r"rename\s+([^\s]+)\s+to\s+([^\s]+)", goal, re.IGNORECASE)
            if rename_match:
                old_name = rename_match.group(1).strip().strip(" .\t\n\r")
                new_name = rename_match.group(2).strip().strip(" .\t\n\r")
            else:
                old_name, new_name = "", ""

            # Optional location or search hint
            # Match more carefully to avoid capturing the old_name as part of the location
            in_match = re.search(r"\b(?:in|inside|under)\s+([A-Za-z](?:\s+drive|:[\\/]?.*|[A-Za-z_.\- ]*))$", goal, re.IGNORECASE)
            subpath = in_match.group(1).strip().strip("\"'") if in_match else ""

            subpath_norm = subpath.strip()
            # Check if it's a drive letter (search hint) like "D drive", "C drive", "D:"
            drive_match = re.match(r"^([A-Za-z])(?:\s+drive|:?[\\/]?)$", subpath_norm, re.IGNORECASE)
            if drive_match:
                # Search hint: treat as drive root search
                drive = drive_match.group(1).upper()
                search_hint = f"{drive}:\\"
                heuristic = [{"tool": "explorer.rename", "args": {"old_name": old_name, "new_name": new_name, "search_hint": search_hint}}]
                raw = json.dumps(heuristic)
                print(f"[Planner] Using explorer.rename with search -> {old_name} in {search_hint}")
                return heuristic, raw, prompt

            is_absolute_dest = bool(re.match(r"^[A-Za-z]:[\\/]", subpath_norm)) or subpath_norm.startswith("\\\\")
            known_locations = {"desktop", "downloads", "documents", "pictures", "music", "videos"}
            is_known_location = subpath_norm.lower() in known_locations

            if old_name and (is_absolute_dest or is_known_location):
                # Could be a direct path or a search hint
                # If it looks like a full path with subfolders, use it as-is
                # Otherwise treat it as search hint
                if "\\" in subpath_norm or "/" in subpath_norm:
                    # Likely a specific path, try direct first, then search
                    src_path = str(Path(subpath_norm) / old_name) if subpath_norm else old_name
                    heuristic = [{"tool": "explorer.rename", "args": {"old_name": src_path, "new_name": new_name}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using explorer.rename heuristic -> {src_path} -> {new_name}")
                    return heuristic, raw, prompt
                else:
                    # Single-word location like "Documents" - use as search hint
                    heuristic = [{"tool": "explorer.rename", "args": {"old_name": old_name, "new_name": new_name, "search_hint": subpath_norm}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using explorer.rename with search -> {old_name} in {subpath_norm}")
                    return heuristic, raw, prompt

            if old_name:
                # Relative/pathless: use filesystem under artifacts
                rel_path = str(Path(subpath_norm) / old_name) if subpath_norm else old_name
                heuristic = [{"tool": "filesystem.rename", "args": {"path": rel_path, "new_name": new_name}}]
                raw = json.dumps(heuristic)
                print(f"[Planner] Using filesystem.rename heuristic -> {rel_path} -> {new_name}")
                return heuristic, raw, prompt

        # Delete/Open with search hints
        if ("delete" in g or "remove" in g) and " in " in g:
            # Check for "permanently" flag
            permanent_flag = bool(re.search(r"\bpermanently?\b", goal, re.IGNORECASE))
            # Remove the flag from the goal for parsing
            goal_no_flag = re.sub(r"\s+permanently?\s*", " ", goal, flags=re.IGNORECASE).strip()
            delete_match = re.search(r"(?:delete|remove)\s+[\"']?([^\"']+?)[\"']?\s+(?:in|inside|under|from)", goal_no_flag, re.IGNORECASE)
            item = delete_match.group(1).strip() if delete_match else ""
            in_match = re.search(r"\b(?:in|inside|under|from)\s+([A-Za-z](?:\s+drive|:[\\/ ]?.*|[A-Za-z_\.\- ]*))$", goal, re.IGNORECASE)
            location = in_match.group(1).strip().strip("\"'") if in_match else ""
            location_norm = location.strip()

            if item:
                drive_match = re.match(r"^([A-Za-z])(?:\s+drive|:?[\\/]?)$", location_norm, re.IGNORECASE)
                if drive_match:
                    drive = drive_match.group(1).upper()
                    search_hint = f"{drive}:\\"
                    heuristic = [{"tool": "explorer.delete", "args": {"name": item, "search_hint": search_hint, "permanent": permanent_flag}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using explorer.delete with search -> {item} in {search_hint}")
                    return heuristic, raw, prompt
                elif location_norm.lower() in {"desktop", "downloads", "documents", "pictures", "music", "videos"}:
                    heuristic = [{"tool": "explorer.delete", "args": {"name": item, "search_hint": location_norm, "permanent": permanent_flag}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using explorer.delete with search -> {item} in {location_norm}")
                    return heuristic, raw, prompt

        if ("open" in g or "launch" in g) and " in " in g and "http" not in g:  # exclude web opens
            open_match = re.search(r"(?:open|launch)\s+[\"']?([^\"']+?)[\"']?\s+(?:in|inside|under|from)", goal, re.IGNORECASE)
            item = open_match.group(1).strip() if open_match else ""
            in_match = re.search(r"\b(?:in|inside|under|from)\s+([A-Za-z](?:\s+drive|:[\\/ ]?.*|[A-Za-z_\.\- ]*))$", goal, re.IGNORECASE)
            location = in_match.group(1).strip().strip("\"'") if in_match else ""
            location_norm = location.strip()

            if item:
                drive_match = re.match(r"^([A-Za-z])(?:\s+drive|:?[\\/]?)$", location_norm, re.IGNORECASE)
                if drive_match:
                    drive = drive_match.group(1).upper()
                    search_hint = f"{drive}:\\"
                    heuristic = [{"tool": "explorer.open_file", "args": {"name": item, "search_hint": search_hint}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using explorer.open_file with search -> {item} in {search_hint}")
                    return heuristic, raw, prompt
                elif location_norm.lower() in {"desktop", "downloads", "documents", "pictures", "music", "videos"}:
                    heuristic = [{"tool": "explorer.open_file", "args": {"name": item, "search_hint": location_norm}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using explorer.open_file with search -> {item} in {location_norm}")
                    return heuristic, raw, prompt

        # Copy with search hints: "copy X from Y to Z"
        if "copy" in g and " from " in g and " to " in g:
            copy_match = re.search(r"copy\s+[\"']?([^\"']+?)[\"']?\s+from\s+([^\s].*?)\s+to\s+([^\s].*)$", goal, re.IGNORECASE)
            if copy_match:
                item = copy_match.group(1).strip().strip("\"'")
                from_loc = copy_match.group(2).strip().strip("\"'")
                to_loc = copy_match.group(3).strip().strip("\"'")

                # Normalize hints like "D drive" or known folders
                def norm_hint(h: str) -> str:
                    h2 = h.strip()
                    m = re.match(r"^([A-Za-z])(?:\s+drive|:)$", h2, re.IGNORECASE)
                    if m:
                        return f"{m.group(1).upper()}:\\"
                    return h2

                from_hint = norm_hint(from_loc)
                to_hint = norm_hint(to_loc)
                heuristic = [{"tool": "explorer.copy_file_search", "args": {"name": item, "from": from_hint, "to": to_hint}}]
                raw = json.dumps(heuristic)
                print(f"[Planner] Using explorer.copy_file_search -> {item} from {from_hint} to {to_hint}")
                return heuristic, raw, prompt

        # Move with search hints: "move X from Y to Z"
        if "move" in g and " from " in g and " to " in g:
            move_match = re.search(r"move\s+[\"']?([^\"']+?)[\"']?\s+from\s+([^\s].*?)\s+to\s+([^\s].*)$", goal, re.IGNORECASE)
            if move_match:
                item = move_match.group(1).strip().strip("\"'")
                from_loc = move_match.group(2).strip().strip("\"'")
                to_loc = move_match.group(3).strip().strip("\"'")

                # Normalize hints like "D drive" or known folders
                def norm_hint(h: str) -> str:
                    h2 = h.strip()
                    m = re.match(r"^([A-Za-z])(?:\s+drive|:)$", h2, re.IGNORECASE)
                    if m:
                        return f"{m.group(1).upper()}:\\"
                    return h2

                from_hint = norm_hint(from_loc)
                to_hint = norm_hint(to_loc)
                heuristic = [{"tool": "explorer.move_file_search", "args": {"name": item, "from": from_hint, "to": to_hint}}]
                raw = json.dumps(heuristic)
                print(f"[Planner] Using explorer.move_file_search -> {item} from {from_hint} to {to_hint}")
                return heuristic, raw, prompt

        # Image/video/file sending heuristics (even without "whatsapp" keyword)
        # Pattern: "send image <path> to <contact>" or "send <path> to <contact>"
        if "send" in g and any(word in g for word in ["image", "photo", "picture", "pic", ".jpg", ".png", ".jpeg", ".gif"]):
            # Extract file path - look for paths with backslashes or file extensions
            path_match = re.search(r'([A-Za-z]:\\[^\s]+\.[a-zA-Z0-9]+)', goal)
            if not path_match:
                path_match = re.search(r'([/\\]?[\w/\\]+\.[a-zA-Z0-9]+)', goal)
            image_path = path_match.group(1) if path_match else ""
            
            # Check for folder context like "in documents", "in downloads", etc.
            import os
            folder_match = re.search(r'\bin\s+(documents?|downloads?|pictures?|desktop|music|videos?)', goal, re.IGNORECASE)
            if folder_match and image_path and not os.path.isabs(image_path):
                folder = folder_match.group(1).lower()
                user_profile = os.environ.get("USERPROFILE", "")
                if "document" in folder:
                    image_path = os.path.join(user_profile, "Documents", image_path)
                elif "download" in folder:
                    image_path = os.path.join(user_profile, "Downloads", image_path)
                elif "picture" in folder:
                    image_path = os.path.join(user_profile, "Pictures", image_path)
                elif "desktop" in folder:
                    image_path = os.path.join(user_profile, "Desktop", image_path)
                elif "music" in folder:
                    image_path = os.path.join(user_profile, "Music", image_path)
                elif "video" in folder:
                    image_path = os.path.join(user_profile, "Videos", image_path)
            
            # Extract contact - look for "to <name>" at end
            contact_match = re.search(r'\bto\s+([A-Za-z][A-Za-z0-9_\s]*?)(?:\s+on|\s+via|\s+using|$)', goal, re.IGNORECASE)
            contact = contact_match.group(1).strip() if contact_match else ""
            
            if image_path and contact:
                heuristic = [{"tool": "whatsapp.send_image", "args": {"contact": contact, "image_path": image_path}}]
                raw = json.dumps(heuristic)
                print(f"[Planner] Using send image heuristic -> {contact}, path: {image_path}")
                return heuristic, raw, prompt
        
        if "send" in g and any(word in g for word in ["video", ".mp4", ".mov", ".avi"]):
            path_match = re.search(r'([A-Za-z]:\\[^\s]+\.[a-zA-Z0-9]+)', goal)
            if not path_match:
                path_match = re.search(r'([/\\]?[\w/\\]+\.[a-zA-Z0-9]+)', goal)
            video_path = path_match.group(1) if path_match else ""
            
            contact_match = re.search(r'\bto\s+([A-Za-z][A-Za-z0-9_\s]*?)(?:\s+on|\s+via|\s+using|$)', goal, re.IGNORECASE)
            contact = contact_match.group(1).strip() if contact_match else ""
            
            if video_path and contact:
                heuristic = [{"tool": "whatsapp.send_video", "args": {"contact": contact, "video_path": video_path}}]
                raw = json.dumps(heuristic)
                print(f"[Planner] Using send video heuristic -> {contact}, path: {video_path}")
                return heuristic, raw, prompt
        
        if "send" in g and any(word in g for word in ["document", "file", "doc", ".pdf", ".docx", ".xlsx", ".txt", ".zip"]):
            path_match = re.search(r'([A-Za-z]:\\[^\s]+\.[a-zA-Z0-9]+)', goal)
            if not path_match:
                path_match = re.search(r'([/\\]?[\w/\\]+\.[a-zA-Z0-9]+)', goal)
            file_path = path_match.group(1) if path_match else ""
            
            contact_match = re.search(r'\bto\s+([A-Za-z][A-Za-z0-9_\s]*?)(?:\s+on|\s+via|\s+using|$)', goal, re.IGNORECASE)
            contact = contact_match.group(1).strip() if contact_match else ""
            
            if file_path and contact:
                heuristic = [{"tool": "whatsapp.send_document", "args": {"contact": contact, "file_path": file_path}}]
                raw = json.dumps(heuristic)
                print(f"[Planner] Using send document heuristic -> {contact}, path: {file_path}")
                return heuristic, raw, prompt

        # Reply heuristic (even without "whatsapp" keyword)
        # Pattern: "reply to <contact> saying <message>"
        if "reply" in g:
            contact_match = re.search(r"(?:reply\s+)?(?:to|in)\s+([A-Za-z][A-Za-z\s]+?)(?:\s+saying|\s+with|\s+that|$)", goal, re.IGNORECASE)
            contact = contact_match.group(1).strip() if contact_match else ""
            msg_match = re.search(r"(?:saying|with|that)\s*\"?(.+?)\"?\s*$", goal, re.IGNORECASE)
            reply_text = msg_match.group(1).strip() if msg_match else "Ok"
            if contact:
                heuristic = [{"tool": "whatsapp.reply_to_message", "args": {"contact": contact, "reply_text": reply_text}}]
                raw = json.dumps(heuristic)
                print(f"[Planner] Using WhatsApp reply heuristic -> {contact}: {reply_text}")
                return heuristic, raw, prompt

        # WhatsApp heuristics
        if "whatsapp" in g:
            # Send message via WhatsApp
            if any(word in g for word in ["send", "message", "text", "tell", "say"]) and not any(word in g for word in ["image", "photo", "picture", "video", "file", "document", "location", "contact"]):
                # Extract contact name and message
                # Patterns: "message to John saying X", "send whatsapp to John", "tell John X", "send whatsapp to my friend abdus saying X"
                
                # First try to extract contact before "saying" or "that"
                contact_match = re.search(
                    r"(?:to\s+)?(?:my\s+)?(?:friend\s+|buddy\s+|mate\s+)?([a-zA-Z][a-zA-Z0-9_]*)\s+(?:saying|that|with|:)",
                    goal, re.IGNORECASE
                )
                if not contact_match:
                    # Try: "to John" at end or before "saying"
                    contact_match = re.search(r"to\s+(?:my\s+)?(?:friend\s+)?([a-zA-Z][a-zA-Z0-9_]*)", goal, re.IGNORECASE)
                if not contact_match:
                    # Try: "tell John"
                    contact_match = re.search(r"tell\s+([a-zA-Z][a-zA-Z0-9_]*)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                
                msg_match = re.search(r"(?:saying|that|with|:)\s*\"?([^\"]+)\"?$", goal, re.IGNORECASE)
                if not msg_match:
                    msg_match = re.search(r"send\s+\"([^\"]+)\"", goal, re.IGNORECASE)
                message = msg_match.group(1).strip() if msg_match else "Hello"
                
                if contact:
                    heuristic = [{"tool": "whatsapp.send_message", "args": {"contact": contact, "message": message}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp send message heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Send image/photo
            if any(word in g for word in ["image", "photo", "picture", "pic"]) and "send" in g:
                contact_match = re.search(r"to\s+([A-Za-z][A-Za-z\s]+?)(?:\s+on|\s+via|\s+with|$)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                path_match = re.search(r"(?:image|photo|picture|pic)\s+([^\s]+\.[a-z]+)", goal, re.IGNORECASE)
                if not path_match:
                    path_match = re.search(r"\"([^\"]+)\"", goal)
                image_path = path_match.group(1) if path_match else ""
                if contact and image_path:
                    heuristic = [{"tool": "whatsapp.send_image", "args": {"contact": contact, "image_path": image_path}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp send image heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Send video
            if "video" in g and "send" in g:
                contact_match = re.search(r"to\s+([A-Za-z][A-Za-z\s]+?)(?:\s+on|\s+via|\s+with|$)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                path_match = re.search(r"video\s+([^\s]+\.[a-z]+)", goal, re.IGNORECASE)
                if not path_match:
                    path_match = re.search(r"\"([^\"]+)\"", goal)
                video_path = path_match.group(1) if path_match else ""
                if contact and video_path:
                    heuristic = [{"tool": "whatsapp.send_video", "args": {"contact": contact, "video_path": video_path}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp send video heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Send document/file
            if any(word in g for word in ["document", "file", "doc", "pdf"]) and "send" in g:
                contact_match = re.search(r"to\s+([A-Za-z][A-Za-z\s]+?)(?:\s+on|\s+via|\s+with|$)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                path_match = re.search(r"(?:document|file|doc)\s+([^\s]+\.[a-z]+)", goal, re.IGNORECASE)
                if not path_match:
                    path_match = re.search(r"\"([^\"]+)\"", goal)
                file_path = path_match.group(1) if path_match else ""
                if contact and file_path:
                    heuristic = [{"tool": "whatsapp.send_document", "args": {"contact": contact, "file_path": file_path}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp send document heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Forward message
            if "forward" in g:
                from_match = re.search(r"from\s+([A-Za-z][A-Za-z\s]+?)(?:\s+to)", goal, re.IGNORECASE)
                to_match = re.search(r"to\s+([A-Za-z][A-Za-z\s]+?)(?:\s+on|\s+via|$)", goal, re.IGNORECASE)
                from_contact = from_match.group(1).strip() if from_match else ""
                to_contact = to_match.group(1).strip() if to_match else ""
                if from_contact and to_contact:
                    heuristic = [{"tool": "whatsapp.forward_message", "args": {"from_contact": from_contact, "to_contact": to_contact}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp forward heuristic -> {from_contact} to {to_contact}")
                    return heuristic, raw, prompt
            
            # Reply to message
            if "reply" in g:
                contact_match = re.search(r"(?:to|in)\s+([A-Za-z][A-Za-z\s]+?)(?:\s+saying|\s+with|$)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                msg_match = re.search(r"(?:saying|with)\s*\"?([^\"]+)\"?$", goal, re.IGNORECASE)
                reply_text = msg_match.group(1).strip() if msg_match else "Ok"
                if contact:
                    heuristic = [{"tool": "whatsapp.reply_to_message", "args": {"contact": contact, "reply_text": reply_text}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp reply heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Read messages
            if any(word in g for word in ["read", "check", "show", "get"]) and "message" in g:
                contact_match = re.search(r"(?:from|with)\s+([A-Za-z][A-Za-z\s]+)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                if contact:
                    heuristic = [{"tool": "whatsapp.read_messages", "args": {"contact": contact, "limit": 10}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp read messages heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Check unread
            if any(word in g for word in ["unread", "new messages", "notifications"]):
                heuristic = [{"tool": "whatsapp.get_unread_chats", "args": {}}]
                raw = json.dumps(heuristic)
                print("[Planner] Using WhatsApp get unread heuristic")
                return heuristic, raw, prompt
            
            # List all chats
            if any(word in g for word in ["list", "show", "all"]) and "chat" in g:
                heuristic = [{"tool": "whatsapp.get_all_chats", "args": {"limit": 20}}]
                raw = json.dumps(heuristic)
                print("[Planner] Using WhatsApp get all chats heuristic")
                return heuristic, raw, prompt
            
            # Search messages
            if "search" in g or "find" in g:
                # Support patterns like:
                # - search for <query> in <contact> on whatsapp
                # - find "<query>" in <contact>
                # - search <query> in <contact>
                # - search for <query> (global)

                # First, try to extract contact if an "in <contact>" or "from <contact>" segment exists
                contact = None
                contact_match = re.search(
                    r"(?:in|from)\s+([A-Za-z][A-Za-z0-9_\s]*?)(?:\s+on\s+whatsapp|\s+via\s+whatsapp|\s+using\s+whatsapp|$)",
                    goal,
                    re.IGNORECASE,
                )
                if contact_match:
                    contact = contact_match.group(1).strip()

                # Next, isolate the query between the verb and the "in/from <contact>" segment if present
                query = ""
                verb_match = re.search(r"(search|find)\s+(?:for\s+)?", goal, re.IGNORECASE)
                if verb_match:
                    start = verb_match.end()
                    end = contact_match.start() if contact_match else len(goal)
                    raw_query = goal[start:end].strip()
                    # Trim surrounding quotes if any
                    if len(raw_query) >= 2 and ((raw_query[0] == '"' and raw_query[-1] == '"') or (raw_query[0] == "'" and raw_query[-1] == "'")):
                        raw_query = raw_query[1:-1]
                    # Remove any trailing helper words like "in", just in case
                    raw_query = re.sub(r"\s+(in|from)\s*$", "", raw_query, flags=re.IGNORECASE).strip()
                    # Also strip any trailing "on whatsapp" accidentally captured
                    raw_query = re.sub(r"\s+on\s+whatsapp\s*$", "", raw_query, flags=re.IGNORECASE).strip()
                    query = raw_query

                if query:
                    args = {"query": query}
                    if contact:
                        args["contact"] = contact
                    heuristic = [{"tool": "whatsapp.search_messages", "args": args}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp search heuristic -> query='{query}' contact='{contact or ''}'")
                    return heuristic, raw, prompt
            
            # Mute chat
            if "mute" in g and "unmute" not in g:
                contact_match = re.search(r"mute\s+([A-Za-z][A-Za-z\s]+?)(?:\s+for|\s+on|$)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                if contact:
                    heuristic = [{"tool": "whatsapp.mute_chat", "args": {"contact": contact}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp mute heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Unmute chat
            if "unmute" in g:
                contact_match = re.search(r"unmute\s+([A-Za-z][A-Za-z\s]+)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                if contact:
                    heuristic = [{"tool": "whatsapp.unmute_chat", "args": {"contact": contact}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp unmute heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Archive chat
            if "archive" in g:
                contact_match = re.search(r"archive\s+([A-Za-z][A-Za-z\s]+?)(?:\s+on|$)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                if contact:
                    heuristic = [{"tool": "whatsapp.archive_chat", "args": {"contact": contact}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp archive heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Pin/unpin chat
            if "pin" in g:
                contact_match = re.search(r"(?:pin|unpin)\s+([A-Za-z][A-Za-z\s]+?)(?:\s+on|$)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                if contact:
                    tool = "whatsapp.unpin_chat" if "unpin" in g else "whatsapp.pin_chat"
                    heuristic = [{"tool": tool, "args": {"contact": contact}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp pin/unpin heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Block/unblock contact
            if "block" in g:
                contact_match = re.search(r"(?:block|unblock)\s+([A-Za-z][A-Za-z\s]+?)(?:\s+on|$)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                if contact:
                    tool = "whatsapp.unblock_contact" if "unblock" in g else "whatsapp.block_contact"
                    heuristic = [{"tool": tool, "args": {"contact": contact}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp block/unblock heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Delete message
            if "delete" in g and "message" in g:
                contact_match = re.search(r"(?:from|in)\s+([A-Za-z][A-Za-z\s]+)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                if contact:
                    heuristic = [{"tool": "whatsapp.delete_message", "args": {"contact": contact, "for_everyone": True}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp delete message heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Delete/clear chat
            if "delete" in g and "chat" in g:
                contact_match = re.search(r"delete\s+(?:chat\s+)?(?:with\s+)?([A-Za-z][A-Za-z\s]+)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                if contact:
                    heuristic = [{"tool": "whatsapp.delete_chat", "args": {"contact": contact}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp delete chat heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            if "clear" in g and "chat" in g:
                contact_match = re.search(r"clear\s+(?:chat\s+)?(?:with\s+)?([A-Za-z][A-Za-z\s]+)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                if contact:
                    heuristic = [{"tool": "whatsapp.clear_chat", "args": {"contact": contact}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp clear chat heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Star message
            if "star" in g:
                contact_match = re.search(r"(?:in|from)\s+([A-Za-z][A-Za-z\s]+)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                if contact:
                    heuristic = [{"tool": "whatsapp.star_message", "args": {"contact": contact}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp star message heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Create group
            if "create" in g and "group" in g:
                name_match = re.search(r"(?:called|named)\s+\"?([^\"]+)\"?", goal, re.IGNORECASE)
                group_name = name_match.group(1).strip() if name_match else "New Group"
                members_match = re.search(r"with\s+(.+?)(?:\s+on|$)", goal, re.IGNORECASE)
                members = []
                if members_match:
                    members = [m.strip() for m in re.split(r",|\s+and\s+", members_match.group(1))]
                if members:
                    heuristic = [{"tool": "whatsapp.create_group", "args": {"group_name": group_name, "members": members}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp create group heuristic -> {group_name}")
                    return heuristic, raw, prompt
            
            # Add to group
            if "add" in g and "group" in g:
                group_match = re.search(r"to\s+(?:group\s+)?([A-Za-z][A-Za-z\s]+?)(?:\s+group|$)", goal, re.IGNORECASE)
                group_name = group_match.group(1).strip() if group_match else ""
                members_match = re.search(r"add\s+(.+?)\s+to", goal, re.IGNORECASE)
                members = []
                if members_match:
                    members = [m.strip() for m in re.split(r",|\s+and\s+", members_match.group(1))]
                if group_name and members:
                    heuristic = [{"tool": "whatsapp.add_to_group", "args": {"group_name": group_name, "members": members}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp add to group heuristic -> {group_name}")
                    return heuristic, raw, prompt
            
            # Leave group
            if "leave" in g and "group" in g:
                group_match = re.search(r"leave\s+(?:the\s+)?(?:group\s+)?([A-Za-z][A-Za-z\s]+?)(?:\s+group|$)", goal, re.IGNORECASE)
                group_name = group_match.group(1).strip() if group_match else ""
                if group_name:
                    heuristic = [{"tool": "whatsapp.leave_group", "args": {"group_name": group_name}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp leave group heuristic -> {group_name}")
                    return heuristic, raw, prompt
            
            # Send location
            if "location" in g:
                contact_match = re.search(r"to\s+([A-Za-z][A-Za-z\s]+)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                if contact:
                    heuristic = [{"tool": "whatsapp.send_location", "args": {"contact": contact}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp send location heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Send/share contact
            if "share" in g and "contact" in g:
                to_match = re.search(r"(?:to|with)\s+([A-Za-z][A-Za-z\s]+?)(?:\s+on|$)", goal, re.IGNORECASE)
                share_match = re.search(r"share\s+([A-Za-z][A-Za-z\s]+?)(?:\s+contact|\s+with|\s+to)", goal, re.IGNORECASE)
                to_contact = to_match.group(1).strip() if to_match else ""
                share_contact = share_match.group(1).strip() if share_match else ""
                if to_contact and share_contact:
                    heuristic = [{"tool": "whatsapp.send_contact", "args": {"to_contact": to_contact, "share_contact": share_contact}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp share contact heuristic -> {share_contact} to {to_contact}")
                    return heuristic, raw, prompt
            
            # Check online/last seen
            if any(word in g for word in ["online", "last seen", "status"]):
                contact_match = re.search(r"(?:of|for|is)\s+([A-Za-z][A-Za-z\s]+?)(?:\s+online|\s+on|$)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                if contact:
                    heuristic = [{"tool": "whatsapp.get_last_seen", "args": {"contact": contact}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp last seen heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Get contact/chat info
            if any(word in g for word in ["info", "about", "details"]):
                contact_match = re.search(r"(?:of|about|for)\s+([A-Za-z][A-Za-z\s]+)", goal, re.IGNORECASE)
                contact = contact_match.group(1).strip() if contact_match else ""
                if contact:
                    heuristic = [{"tool": "whatsapp.get_contact_info", "args": {"contact": contact}}]
                    raw = json.dumps(heuristic)
                    print(f"[Planner] Using WhatsApp get contact info heuristic -> {contact}")
                    return heuristic, raw, prompt
            
            # Open/initialize WhatsApp
            if any(word in g for word in ["open", "start", "launch", "initialize"]):
                heuristic = [{"tool": "whatsapp.initialize", "args": {}}]
                raw = json.dumps(heuristic)
                print("[Planner] Using WhatsApp initialize heuristic")
                return heuristic, raw, prompt

        if ("message" in g or "dm" in g or "text" in g) and (" to " in g or " @" in g):
            mname = re.search(r"(?:message|dm|text)\s+([@#]?\w+)", goal, re.IGNORECASE)
            contact = mname.group(1) if mname else "contact"
            mbody = re.search(r"(?:saying|with|that)\s+\"([^\"]+)\"", goal, re.IGNORECASE)
            body = mbody.group(1) if mbody else "Hello"
            heuristic = [{"tool": "messaging.send_to_contact", "args": {"name": contact, "message": body}}]
            raw = json.dumps(heuristic)
            print("[Planner] Using messaging heuristic")
            return heuristic, raw, prompt

        # Heuristic: read Notepad content for "what's on my screen"/define/read/summarize intents
        g_screen = g
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
        has_followup = any(word in g for word in ["write", "type", "click", "select", "fill", "enter", "submit", "search", "play", "text", "message", "send"])
        
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
