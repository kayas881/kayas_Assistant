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
        except Exception as e:
            return {"error": str(e), "tool": t, "args": a}
        return {"error": f"Unknown tool: {t}", "args": a}
