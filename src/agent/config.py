import os
from pathlib import Path
from typing import Any, Dict

import yaml


def env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def artifacts_dir() -> Path:
    return Path(env_str("AGENT_ARTIFACTS_DIR", "artifacts")).resolve()


def db_path() -> Path:
    return Path(env_str("AGENT_DB_PATH", ".agent/agent.db")).resolve()


def ollama_model() -> str:
    # Try to read from profile first, then env, then default
    default = str(profile_get("models.main_model", "llama3"))
    return env_str("OLLAMA_MODEL", default)


def embed_model() -> str:
    return env_str("EMBED_MODEL", "nomic-embed-text")


def ollama_url() -> str:
    # Default local ollama server URL
    return env_str("OLLAMA_URL", "http://localhost:11434")


def strong_model() -> str:
    # Optional stronger model for fallback planning
    return env_str("STRONG_MODEL", "")


def chroma_dir() -> Path:
    return Path(env_str("CHROMA_DIR", ".agent/chroma")).resolve()


def search_root() -> Path:
    return Path(env_str("SEARCH_ROOT", ".")).resolve()


def preference_model_path() -> Path:
    return Path(env_str("PREFERENCE_MODEL_PATH", ".agent/preference_model.json")).resolve()


def sandbox_mode() -> str:
    # disabled | dry-run | enforced
    return env_str("SANDBOX_MODE", "disabled").lower()


def archive_dir() -> Path:
    # Where archived files go (under artifacts by default)
    base = artifacts_dir()
    return (base / "archive").resolve()


# Voice & personality
def whisper_model() -> str:
    # small, base, medium, large-v3; prefer small/base for local CPU
    return env_str("WHISPER_MODEL", "small")


def tts_engine() -> str:
    # coqui | pyttsx3
    return env_str("TTS_ENGINE", "pyttsx3").lower()


def tts_model() -> str:
    # For Coqui TTS (e.g., tts_models/en/ljspeech/tacotron2-DDC)
    return env_str("TTS_MODEL", "tts_models/en/ljspeech/tacotron2-DDC")


# Personal profile (YAML)
def profile_path() -> Path:
    return Path(env_str("AGENT_PROFILE_PATH", ".agent/profile.yaml")).resolve()


_PROFILE_CACHE: Dict[str, Any] | None = None


def load_profile() -> Dict[str, Any]:
    global _PROFILE_CACHE
    if _PROFILE_CACHE is not None:
        return _PROFILE_CACHE
    p = profile_path()
    if not p.exists():
        _PROFILE_CACHE = {}
        return _PROFILE_CACHE
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            data = {}
        _PROFILE_CACHE = data
        return data
    except Exception:
        _PROFILE_CACHE = {}
        return _PROFILE_CACHE


def profile_get(path: str, default: Any) -> Any:
    data = load_profile()
    cur: Any = data
    try:
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur
    except Exception:
        return default


def default_notes_filename() -> str:
    return str(profile_get("files.notes_filename", "notes.txt"))


def preferred_search_engine() -> str:
    return str(profile_get("web.search_engine", "google"))


def preferred_search_base() -> str:
    engine = preferred_search_engine().lower()
    if engine == "duckduckgo":
        return "https://duckduckgo.com/?q="
    if engine == "brave":
        return "https://search.brave.com/search?q="
    if engine == "bing":
        return "https://www.bing.com/search?q="
    return "https://www.google.com/search?q="


def default_delete_action() -> str:
    # archive | delete
    return str(profile_get("safety.default_delete", "archive")).lower()


def strong_model() -> str:
    # Optional stronger model for fallback planning (profile can override env)
    val = profile_get("models.strong_model", None)
    if val:
        return str(val)
    return env_str("STRONG_MODEL", "")


# Planning modes
def planning_mode() -> str:
    # 'structured' | 'react'
    return env_str("PLANNING_MODE", str(profile_get("planning.mode", "structured"))).lower()


def react_max_steps() -> int:
    return int(os.getenv("REACT_MAX_STEPS", str(profile_get("planning.react.max_steps", 6))))


def react_beam_width() -> int:
    return int(os.getenv("REACT_BEAM_WIDTH", str(profile_get("planning.react.beam_width", 3))))


# API Integrations
def google_calendar_config() -> dict:
    return {
        "credentials_file": env_str("GOOGLE_CALENDAR_CREDENTIALS", str(profile_get("apis.google.credentials_file", ""))),
        "token_file": env_str("GOOGLE_CALENDAR_TOKEN", str(profile_get("apis.google.token_file", ".agent/google_token.json"))),
        "scopes": ["https://www.googleapis.com/auth/calendar"],
    }


def slack_config() -> dict:
    return {
        "bot_token": env_str("SLACK_BOT_TOKEN", str(profile_get("apis.slack.bot_token", ""))),
        "user_token": env_str("SLACK_USER_TOKEN", str(profile_get("apis.slack.user_token", ""))),
        "signing_secret": env_str("SLACK_SIGNING_SECRET", str(profile_get("apis.slack.signing_secret", ""))),
    }


def spotify_config() -> dict:
    return {
        "client_id": env_str("SPOTIFY_CLIENT_ID", str(profile_get("apis.spotify.client_id", ""))),
        "client_secret": env_str("SPOTIFY_CLIENT_SECRET", str(profile_get("apis.spotify.client_secret", ""))),
        "redirect_uri": env_str("SPOTIFY_REDIRECT_URI", str(profile_get("apis.spotify.redirect_uri", "http://localhost:8888/callback"))),
        "scope": "user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private playlist-read-collaborative",
    }


def smtp_config() -> dict:
    return {
        "host": env_str("SMTP_HOST", ""),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": env_str("SMTP_USER", ""),
        "password": env_str("SMTP_PASSWORD", ""),
        "from_addr": env_str("SMTP_FROM", ""),
        "use_tls": env_str("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes"),
    }


def github_config() -> dict:
    return {
        "token": env_str("GITHUB_TOKEN", str(profile_get("apis.github.token", ""))),
        "username": env_str("GITHUB_USERNAME", str(profile_get("apis.github.username", ""))),
    }


def notion_config() -> dict:
    return {
        "token": env_str("NOTION_TOKEN", str(profile_get("apis.notion.token", ""))),
    }


def trello_config() -> dict:
    return {
        "api_key": env_str("TRELLO_API_KEY", str(profile_get("apis.trello.api_key", ""))),
        "token": env_str("TRELLO_TOKEN", str(profile_get("apis.trello.token", ""))),
    }


def jira_config() -> dict:
    return {
        "url": env_str("JIRA_URL", str(profile_get("apis.jira.url", ""))),
        "email": env_str("JIRA_EMAIL", str(profile_get("apis.jira.email", ""))),
        "api_token": env_str("JIRA_API_TOKEN", str(profile_get("apis.jira.api_token", ""))),
    }


# Desktop automation (dangerous, off by default)
def desktop_enabled() -> bool:
    # Enable only if explicitly set: env DESKTOP_AUTOMATION_ENABLED=1 or profile desktop.enabled: true
    prof = bool(profile_get("desktop.enabled", False))
    envv = env_str("DESKTOP_AUTOMATION_ENABLED", "0").lower() in ("1", "true", "yes")
    return bool(prof or envv)
