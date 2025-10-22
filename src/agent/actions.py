from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Action:
    tool: str
    args: Dict[str, Any]


def parse_actions(text: str) -> List[Action]:
    import json

    # Accept either a single JSON object or a JSON list
    try:
        data = json.loads(text)
    except Exception:
        return []
    if isinstance(data, dict):
        data = [data]
    out: List[Action] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        tool = item.get("tool")
        args = item.get("args", {})
        if isinstance(tool, str) and isinstance(args, dict):
            out.append(Action(tool=tool, args=args))
    return out


class Router:
    def __init__(self, executors: Dict[str, Any], safety: Optional[Any] = None):
        self.executors = executors
        self.safety = safety

    def route(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Route an action dict like {"action": "tool.method", "args": {...}} or {"tool": "...", "args": {...}} to the appropriate executor."""
        # Support both "action" and "tool" keys for compatibility
        action_str = action_data.get("action") or action_data.get("tool", "")
        args = action_data.get("args", {})
        
        # Convert to Action object for dispatch
        action = Action(tool=action_str, args=args)
        return self.dispatch(action)

    def dispatch(self, action: Action) -> Dict[str, Any]:
        t = action.tool
        a = action.args
        # Safety gate
        if self.safety is not None:
            decision = self.safety.assess(t, a)
            if decision.needs_confirmation and not decision.allowed:
                return {
                    "needs_confirmation": True,
                    "reason": decision.reason,
                    "suggestion": (decision.alternatives or {}).get("suggestion"),
                    "suggested_args": (decision.alternatives or {}).get("args"),
                    "tool": t,
                    "args": a,
                }
        try:
            if t == "filesystem.create_file":
                return self.executors["fs"].create_file(a.get("filename", "notes.txt"), a.get("content", ""))
            if t == "filesystem.append_file":
                return self.executors["fs"].append_file(a.get("filename", "notes.txt"), a.get("content", ""))
            if t == "filesystem.delete_file":
                return self.executors["fs"].delete_file(a.get("filename", "notes.txt"))
            if t == "filesystem.archive_file":
                return self.executors["fs"].archive_file(a.get("filename", "notes.txt"))
            if t == "web.fetch":
                return self.executors["web"].fetch(a["url"])  # raises KeyError if missing
            if t == "email.send":
                return self.executors["email"].send(a["to"], a.get("subject", ""), a.get("body", ""))
            if t == "local.search":
                return self.executors["search"].search(a.get("query", ""))
            if t == "browser.run_steps":
                return self.executors["browser"].run_steps(
                    steps=a.get("steps", []),
                    headless=a.get("headless"),
                    base_url=a.get("base_url"),
                    stop_on_error=a.get("stop_on_error", True),
                )
            if t == "desktop.run_steps":
                return self.executors["desktop"].run_steps(
                    steps=a.get("steps", []),
                    stop_on_error=a.get("stop_on_error", True),
                )
            # API integrations
            if t == "calendar.list_events":
                return self.executors["calendar"].list_events(
                    calendar_id=a.get("calendar_id", "primary"),
                    max_results=a.get("max_results", 10),
                    days_ahead=a.get("days_ahead", 7)
                )
            if t == "calendar.create_event":
                return self.executors["calendar"].create_event(
                    summary=a["summary"],
                    start_time=a["start_time"],
                    end_time=a["end_time"],
                    description=a.get("description", ""),
                    location=a.get("location", ""),
                    calendar_id=a.get("calendar_id", "primary")
                )
            if t == "calendar.delete_event":
                return self.executors["calendar"].delete_event(
                    event_id=a["event_id"],
                    calendar_id=a.get("calendar_id", "primary")
                )
            if t == "calendar.find_free_time":
                return self.executors["calendar"].find_free_time(
                    duration_minutes=a.get("duration_minutes", 60),
                    days_ahead=a.get("days_ahead", 7),
                    start_hour=a.get("start_hour", 9),
                    end_hour=a.get("end_hour", 17)
                )
            if t == "slack.send_message":
                return self.executors["slack"].send_message(
                    channel=a["channel"],
                    text=a["text"],
                    thread_ts=a.get("thread_ts")
                )
            if t == "slack.list_channels":
                return self.executors["slack"].list_channels(
                    types=a.get("types", "public_channel,private_channel"),
                    limit=a.get("limit", 100)
                )
            if t == "slack.get_user_info":
                return self.executors["slack"].get_user_info(user_id=a["user_id"])
            if t == "slack.search_messages":
                return self.executors["slack"].search_messages(
                    query=a["query"],
                    count=a.get("count", 20)
                )
            if t == "slack.set_status":
                return self.executors["slack"].set_status(
                    text=a["text"],
                    emoji=a.get("emoji", ""),
                    expiration=a.get("expiration")
                )
            if t == "spotify.search_music":
                return self.executors["spotify"].search_music(
                    query=a["query"],
                    search_type=a.get("search_type", "track"),
                    limit=a.get("limit", 10)
                )
            if t == "spotify.play_track":
                return self.executors["spotify"].play_track(
                    track_uri=a["track_uri"],
                    device_id=a.get("device_id")
                )
            if t == "spotify.play_query":
                return self.executors["spotify"].play_query(
                    query=a["query"],
                    device_id=a.get("device_id")
                )
            if t == "spotify.get_current_playing":
                return self.executors["spotify"].get_current_playing()
            if t == "spotify.pause_playback":
                return self.executors["spotify"].pause_playback(device_id=a.get("device_id"))
            if t == "spotify.resume_playback":
                return self.executors["spotify"].resume_playback(device_id=a.get("device_id"))
            if t == "spotify.get_user_playlists":
                return self.executors["spotify"].get_user_playlists(limit=a.get("limit", 20))
            if t == "spotify.create_playlist":
                return self.executors["spotify"].create_playlist(
                    name=a["name"],
                    description=a.get("description", ""),
                    public=a.get("public", True)
                )
            if t == "spotify.add_tracks_to_playlist":
                return self.executors["spotify"].add_tracks_to_playlist(
                    playlist_id=a["playlist_id"],
                    track_uris=a["track_uris"]
                )
            # Process executor
            if t == "process.run_command":
                return self.executors["process"].run_command(
                    command=a["command"],
                    timeout=a.get("timeout"),
                    shell=a.get("shell"),
                    working_dir=a.get("working_dir")
                )
            if t == "process.start_program":
                return self.executors["process"].start_program(
                    program=a["program"],
                    args=a.get("args"),
                    background=a.get("background", True),
                    process_id=a.get("process_id")
                )
            if t == "process.kill_process":
                return self.executors["process"].kill_process(
                    process_id=a.get("process_id"),
                    pid=a.get("pid"),
                    name=a.get("name")
                )
            if t == "process.list_processes":
                return self.executors["process"].list_processes(
                    filter_name=a.get("filter_name")
                )
            if t == "process.get_system_info":
                return self.executors["process"].get_system_info()
            # Clipboard executor
            if t == "clipboard.copy_text":
                return self.executors["clipboard"].copy_text(
                    text=a["text"],
                    add_to_history=a.get("add_to_history", True)
                )
            if t == "clipboard.paste_text":
                return self.executors["clipboard"].paste_text()
            if t == "clipboard.copy_image":
                return self.executors["clipboard"].copy_image(
                    image_path=a.get("image_path"),
                    add_to_history=a.get("add_to_history", True)
                )
            if t == "clipboard.paste_image":
                return self.executors["clipboard"].paste_image(
                    save_path=a.get("save_path")
                )
            if t == "clipboard.get_history":
                return self.executors["clipboard"].get_history(
                    limit=a.get("limit")
                )
            if t == "clipboard.clear_history":
                return self.executors["clipboard"].clear_history()
            # Network executor
            if t == "network.http_request":
                return self.executors["network"].http_request(
                    url=a["url"],
                    method=a.get("method", "GET"),
                    headers=a.get("headers"),
                    data=a.get("data"),
                    json_data=a.get("json"),
                    params=a.get("params"),
                    timeout=a.get("timeout")
                )
            if t == "network.download_file":
                return self.executors["network"].download_file(
                    url=a["url"],
                    save_path=a["save_path"],
                    chunk_size=a.get("chunk_size", 8192),
                    show_progress=a.get("show_progress", True)
                )
            if t == "network.upload_file":
                return self.executors["network"].upload_file(
                    url=a["url"],
                    file_path=a["file_path"],
                    field_name=a.get("field_name", "file"),
                    additional_data=a.get("additional_data")
                )
            if t == "network.get_url_info":
                return self.executors["network"].get_url_info(url=a["url"])
            if t == "network.check_connectivity":
                return self.executors["network"].check_connectivity(
                    hosts=a.get("hosts")
                )
            # FileWatcher executor
            if t == "filewatcher.watch_directory":
                return self.executors["filewatcher"].watch_directory(
                    path=a["path"],
                    watch_id=a.get("watch_id")
                )
            if t == "filewatcher.stop_watching":
                return self.executors["filewatcher"].stop_watching(
                    watch_id=a["watch_id"]
                )
            if t == "filewatcher.get_active_watches":
                return self.executors["filewatcher"].get_active_watches()
            if t == "filewatcher.get_event_log":
                return self.executors["filewatcher"].get_event_log(
                    watch_id=a.get("watch_id"),
                    limit=a.get("limit", 50)
                )
            if t == "filewatcher.clear_event_log":
                return self.executors["filewatcher"].clear_event_log()
            # LLM executor
            if t == "llm.generate":
                return self.executors["llm"].generate(
                    prompt=a["prompt"],
                    system=a.get("system"),
                    temperature=a.get("temperature", 0.7),
                    max_tokens=a.get("max_tokens")
                )
            if t == "llm.chat":
                return self.executors["llm"].chat(
                    messages=a["messages"],
                    system=a.get("system"),
                    temperature=a.get("temperature", 0.7),
                    max_tokens=a.get("max_tokens")
                )
            if t == "llm.summarize":
                return self.executors["llm"].summarize(
                    text=a["text"],
                    max_length=a.get("max_length", 100)
                )
            if t == "llm.chain_of_thought":
                return self.executors["llm"].chain_of_thought(
                    problem=a["problem"],
                    steps=a.get("steps")
                )
            if t == "llm.few_shot_learning":
                return self.executors["llm"].few_shot_learning(
                    examples=a["examples"],
                    query=a["query"]
                )
            if t == "llm.embeddings":
                return self.executors["llm"].embeddings(
                    texts=a["texts"]
                )
            # Phase 1: UI Automation tools
            if t == "uia.find_window":
                return self.executors["uia"].find_window(
                    title=a.get("title"),
                    class_name=a.get("class_name"),
                    process_id=a.get("process_id"),
                    best_match=a.get("best_match")
                )
            if t == "uia.list_windows":
                return self.executors["uia"].list_windows()
            if t == "uia.click_button":
                return self.executors["uia"].click_button(
                    window_title=a["window_title"],
                    button_text=a.get("button_text"),
                    button_id=a.get("button_id"),
                    button_class=a.get("button_class")
                )
            if t == "uia.type_text":
                return self.executors["uia"].type_text(
                    window_title=a["window_title"],
                    text=a["text"],
                    control_id=a.get("control_id"),
                    control_type=a.get("control_type")
                )
            if t == "uia.read_text":
                return self.executors["uia"].read_text(
                    window_title=a["window_title"],
                    control_id=a.get("control_id")
                )
            if t == "uia.get_menu_items":
                return self.executors["uia"].get_menu_items(
                    window_title=a["window_title"]
                )
            if t == "uia.click_menu_item":
                return self.executors["uia"].click_menu_item(
                    window_title=a["window_title"],
                    menu_path=a["menu_path"]
                )
            if t == "uia.focus_window":
                return self.executors["uia"].focus_window(
                    window_title=a["window_title"]
                )
            if t == "uia.close_window":
                return self.executors["uia"].close_window(
                    window_title=a["window_title"]
                )
            if t == "uia.get_control_tree":
                return self.executors["uia"].get_control_tree(
                    window_title=a["window_title"]
                )
            # Phase 1: OCR tools
            if t == "ocr.find_text":
                return self.executors["ocr"].find_text_on_screen(
                    search_text=a["text"],
                    region=a.get("region"),
                    case_sensitive=a.get("case_sensitive", False)
                )
            if t == "ocr.click_text":
                return self.executors["ocr"].click_text(
                    text=a["text"],
                    region=a.get("region"),
                    button=a.get("button", "left"),
                    clicks=a.get("clicks", 1)
                )
            if t == "ocr.read_screen":
                return self.executors["ocr"].read_screen_text(
                    region=a.get("region")
                )
            if t == "ocr.wait_for_text":
                return self.executors["ocr"].wait_for_text(
                    text=a["text"],
                    timeout=a.get("timeout", 10),
                    region=a.get("region")
                )
            if t == "ocr.get_text_near":
                return self.executors["ocr"].get_text_near_position(
                    x=a["x"],
                    y=a["y"],
                    radius=a.get("radius", 50)
                )
            if t == "ocr.find_buttons":
                return self.executors["ocr"].find_buttons(
                    region=a.get("region")
                )
            # Phase 1: Perception Engine (smart tools)
            if t == "perception.smart_click":
                return self.executors["perception"].smart_click(
                    target=a["target"],
                    context=a.get("context", {})
                )
            if t == "perception.smart_type":
                return self.executors["perception"].smart_type(
                    text=a["text"],
                    context=a.get("context", {})
                )
            if t == "perception.smart_read":
                return self.executors["perception"].smart_read(
                    context=a.get("context", {})
                )
            if t == "perception.find_element":
                return self.executors["perception"].find_element(
                    description=a["description"],
                    context=a.get("context", {})
                )
            if t == "perception.get_capabilities":
                return self.executors["perception"].get_capabilities()
            # Phase 1: Computer Vision tools
            if t == "cv.find_image":
                return self.executors["cv"].find_image_on_screen(
                    template_path=a["template_path"],
                    confidence=a.get("confidence"),
                    region=a.get("region"),
                    multi_match=a.get("multi_match")
                )
            if t == "cv.click_image":
                return self.executors["cv"].click_image(
                    template_path=a["template_path"],
                    confidence=a.get("confidence"),
                    region=a.get("region"),
                    button=a.get("button", "left"),
                    clicks=a.get("clicks", 1)
                )
            if t == "cv.wait_for_image":
                return self.executors["cv"].wait_for_image(
                    template_path=a["template_path"],
                    timeout=a.get("timeout", 10),
                    confidence=a.get("confidence"),
                    region=a.get("region")
                )
            if t == "cv.find_by_feature":
                return self.executors["cv"].find_by_feature_matching(
                    template_path=a["template_path"],
                    region=a.get("region"),
                    min_matches=a.get("min_matches", 10)
                )
            if t == "cv.find_by_color":
                return self.executors["cv"].find_by_color(
                    color_range=a["color_range"],
                    region=a.get("region"),
                    min_area=a.get("min_area", 100)
                )
            if t == "cv.screenshot":
                return self.executors["cv"].save_screenshot(
                    filename=a["filename"],
                    region=a.get("region")
                )
        except Exception as e:
            return {"error": str(e), "tool": t, "args": a}
        return {"error": f"Unknown tool: {t}", "args": a}
