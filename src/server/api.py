from __future__ import annotations

from fastapi import FastAPI
from pathlib import Path
from pydantic import BaseModel

from ..agent.main import run_agent
from ..executors.web_exec import WebExecutor, WebConfig
from ..executors.local_search import LocalSearchExecutor, LocalSearchConfig
from ..executors.email_exec import EmailExecutor, EmailConfig
from ..executors.calendar_exec import GoogleCalendarExecutor, CalendarConfig
from ..executors.slack_exec import SlackExecutor, SlackConfig
from ..executors.spotify_exec import SpotifyExecutor, SpotifyConfig
from ..executors.browser_exec import BrowserExecutor, BrowserConfig
from ..executors.desktop_exec import DesktopExecutor, DesktopConfig
from ..agent.config import desktop_enabled
from ..agent.config import search_root, smtp_config, chroma_dir, embed_model, db_path, preference_model_path, google_calendar_config, slack_config, spotify_config
from ..memory.vector_memory import VectorMemory, VectorMemoryConfig
from ..memory.sqlite_memory import MemoryConfig, SQLiteMemory
from ..training.dataset import DatasetExporter, ExportConfig
from ..training.preference_model import train_preference_model, score_plan


class RunRequest(BaseModel):
    goal: str


class RunResponse(BaseModel):
    run_id: str
    artifact: str


app = FastAPI(title="Kayas-lite Agent")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/agent/run", response_model=RunResponse)
def agent_run(req: RunRequest) -> RunResponse:
    out = run_agent(req.goal)
    return RunResponse(**out)


class WebFetchRequest(BaseModel):
    url: str


@app.post("/tools/web/fetch")
def web_fetch(req: WebFetchRequest) -> dict:
    web = WebExecutor(WebConfig())
    return web.fetch(req.url)


class LocalSearchRequest(BaseModel):
    query: str


@app.post("/tools/local/search")
def local_search_api(req: LocalSearchRequest) -> dict:
    search = LocalSearchExecutor(LocalSearchConfig(root=search_root()))
    return search.search(req.query)


class EmailSendRequest(BaseModel):
    to: str
    subject: str = ""
    body: str = ""


@app.post("/tools/email/send")
def email_send_api(req: EmailSendRequest) -> dict:
    email = EmailExecutor(EmailConfig(**smtp_config()))
    return email.send(req.to, req.subject, req.body)


class FeedbackRequest(BaseModel):
    run_id: str
    feedback: str
    tags: str | None = None


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest) -> dict:
    # Log to SQLite
    mem = SQLiteMemory(MemoryConfig(db_path=Path(".agent/agent.db").resolve()))
    mem.log_feedback(req.run_id, req.feedback, req.tags or "")
    # Store in vector memory as well
    vmem = VectorMemory(VectorMemoryConfig(persist_dir=chroma_dir(), embed_model=embed_model()))
    doc = f"Feedback for run {req.run_id}: {req.feedback}"
    vmem.add([doc], metadatas=[{"type": "feedback", "run_id": req.run_id, "tags": req.tags or ""}], ids=[f"fb-{req.run_id}"])
    return {"ok": True}


class ExportRequest(BaseModel):
    out_path: str = ".agent/datasets/plan_feedback.jsonl"


@app.post("/training/export")
def export_training_data(req: ExportRequest) -> dict:
    cfg = ExportConfig(db_path=db_path(), out_path=Path(req.out_path).resolve())
    exporter = DatasetExporter(cfg)
    out = exporter.export()
    return {"ok": True, "path": str(out)}


class TrainPrefRequest(BaseModel):
    max_vocab: int | None = None
    epochs: int | None = None
    lr: float | None = None


@app.post("/training/preference/train")
def train_preference(req: TrainPrefRequest) -> dict:
    from ..training.preference_model import PrefConfig
    cfg = PrefConfig(
        db_file=db_path(),
        model_file=preference_model_path(),
        max_vocab=req.max_vocab or 5000,
        epochs=req.epochs or 5,
        lr=req.lr or 0.1,
    )
    model = train_preference_model(cfg)
    return {"ok": True, "model_path": str(preference_model_path()), "vocab_size": len(model.vocab)}


class ScorePrefRequest(BaseModel):
    prompt: str
    completion: str


@app.post("/training/preference/score")
def score_preference(req: ScorePrefRequest) -> dict:
    s = score_plan(req.prompt, req.completion, model_path=preference_model_path())
    return {"ok": True, "score": s}
# Browser run steps
class BrowserRunRequest(BaseModel):
    steps: list
    headless: bool | None = None
    base_url: str | None = None
    session_name: str | None = None
    persist_session: bool | None = None
    stop_on_error: bool | None = True


@app.post("/tools/browser/run_steps")
def browser_run_steps(req: BrowserRunRequest) -> dict:
    try:
        browser = BrowserExecutor(BrowserConfig())
        return browser.run_steps(
            req.steps,
            headless=req.headless,
            base_url=req.base_url,
            session_name=req.session_name,
            persist_session=req.persist_session,
            stop_on_error=req.stop_on_error if req.stop_on_error is not None else True,
        )
    except Exception as e:
        return {"error": f"Browser service unavailable: {str(e)}"}


# Desktop run steps (guarded by config)
class DesktopRunRequest(BaseModel):
    steps: list
    stop_on_error: bool | None = True


@app.post("/tools/desktop/run_steps")
def desktop_run_steps(req: DesktopRunRequest) -> dict:
    if not desktop_enabled():
        return {"error": "Desktop automation disabled. Set DESKTOP_AUTOMATION_ENABLED=1 or profile desktop.enabled: true"}
    try:
        desktop = DesktopExecutor(DesktopConfig())
        return desktop.run_steps(req.steps, stop_on_error=req.stop_on_error if req.stop_on_error is not None else True)
    except Exception as e:
        return {"error": f"Desktop service unavailable: {str(e)}"}


# API integration endpoints
class CalendarListRequest(BaseModel):
    calendar_id: str = "primary"
    max_results: int = 10
    days_ahead: int = 7


@app.post("/tools/calendar/list_events")
def calendar_list_events(req: CalendarListRequest) -> dict:
    try:
        calendar = GoogleCalendarExecutor(CalendarConfig(**google_calendar_config()))
        return calendar.list_events(req.calendar_id, req.max_results, req.days_ahead)
    except Exception as e:
        return {"error": f"Calendar service unavailable: {str(e)}"}


class CalendarCreateRequest(BaseModel):
    summary: str
    start_time: str
    end_time: str
    description: str = ""
    location: str = ""
    calendar_id: str = "primary"


@app.post("/tools/calendar/create_event")
def calendar_create_event(req: CalendarCreateRequest) -> dict:
    try:
        calendar = GoogleCalendarExecutor(CalendarConfig(**google_calendar_config()))
        return calendar.create_event(req.summary, req.start_time, req.end_time, req.description, req.location, req.calendar_id)
    except Exception as e:
        return {"error": f"Calendar service unavailable: {str(e)}"}


class SlackMessageRequest(BaseModel):
    channel: str
    text: str
    thread_ts: str | None = None


@app.post("/tools/slack/send_message")
def slack_send_message(req: SlackMessageRequest) -> dict:
    try:
        slack = SlackExecutor(SlackConfig(**slack_config()))
        return slack.send_message(req.channel, req.text, req.thread_ts)
    except Exception as e:
        return {"error": f"Slack service unavailable: {str(e)}"}


class SlackChannelsRequest(BaseModel):
    types: str = "public_channel,private_channel"
    limit: int = 100


@app.post("/tools/slack/list_channels")
def slack_list_channels(req: SlackChannelsRequest) -> dict:
    try:
        slack = SlackExecutor(SlackConfig(**slack_config()))
        return slack.list_channels(req.types, req.limit)
    except Exception as e:
        return {"error": f"Slack service unavailable: {str(e)}"}


class SpotifySearchRequest(BaseModel):
    query: str
    search_type: str = "track"
    limit: int = 10


@app.post("/tools/spotify/search")
def spotify_search(req: SpotifySearchRequest) -> dict:
    try:
        spotify = SpotifyExecutor(SpotifyConfig(**spotify_config()))
        return spotify.search_music(req.query, req.search_type, req.limit)
    except Exception as e:
        return {"error": f"Spotify service unavailable: {str(e)}"}


class SpotifyPlayRequest(BaseModel):
    track_uri: str
    device_id: str | None = None


@app.post("/tools/spotify/play")
def spotify_play(req: SpotifyPlayRequest) -> dict:
    try:
        spotify = SpotifyExecutor(SpotifyConfig(**spotify_config()))
        return spotify.play_track(req.track_uri, req.device_id)
    except Exception as e:
        return {"error": f"Spotify service unavailable: {str(e)}"}


class SpotifyPlayQueryRequest(BaseModel):
    query: str
    device_id: str | None = None


@app.post("/tools/spotify/play_query")
def spotify_play_query(req: SpotifyPlayQueryRequest) -> dict:
    try:
        spotify = SpotifyExecutor(SpotifyConfig(**spotify_config()))
        return spotify.play_query(req.query, req.device_id)
    except Exception as e:
        return {"error": f"Spotify service unavailable: {str(e)}"}


@app.get("/tools/spotify/current")
def spotify_current() -> dict:
    try:
        spotify = SpotifyExecutor(SpotifyConfig(**spotify_config()))
        return spotify.get_current_playing()
    except Exception as e:
        return {"error": f"Spotify service unavailable: {str(e)}"}
