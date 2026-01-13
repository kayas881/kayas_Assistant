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
    default = str(profile_get("models.main_model", "llama3.1"))
    return env_str("OLLAMA_MODEL", default)


def planner_model() -> str:
    """Model used for fast planning steps (e.g., query planning / gap spotting).

    Order of precedence:
    1) Profile: models.planner_model
    2) Env: OLLAMA_PLANNER_MODEL
    3) Fallback: ollama_model()
    """
    prof = profile_get("models.planner_model", None)
    default = str(prof) if prof else ollama_model()
    return env_str("OLLAMA_PLANNER_MODEL", default)


def embed_model() -> str:
    return env_str("EMBED_MODEL", "nomic-embed-text")


def ollama_url() -> str:
    # Default local ollama server URL
    return env_str("OLLAMA_URL", "http://localhost:11434")


def strong_model() -> str:
    # Optional stronger model for fallback planning
    return env_str("STRONG_MODEL", "")


# LLM backend configuration
def llm_backend() -> str:
    """Select LLM backend: 'groq' | 'ollama' | 'hf' | 'http' | 'azure' | 'vllm'."""
    val = profile_get("models.backend", None)
    if val:
        return str(val).lower()
    # Check env - support both KAYAS_BACKEND and AGENT_LLM_BACKEND for convenience
    backend = env_str("KAYAS_BACKEND", "") or env_str("AGENT_LLM_BACKEND", "groq")
    return backend.lower()


# Groq configuration (free tier with Llama 3.3 70B)
def groq_api_key() -> str:
    """Get Groq API key from env."""
    return env_str("GROQ_API_KEY", str(profile_get("models.groq.api_key", "")))


def groq_model() -> str:
    """Get Groq model name."""
    return env_str("GROQ_MODEL", str(profile_get("models.groq.model", "llama-3.3-70b-versatile")))


# vLLM remote backend config (self-hosted via ngrok)
def vllm_api_url() -> str:
    """Get vLLM API URL (ngrok or direct)."""
    prof = profile_get("models.vllm.api_url", "")
    if prof:
        return str(prof)
    return env_str("VLLM_API_URL", "")


def vllm_model() -> str:
    """Get vLLM model name."""
    return env_str("VLLM_MODEL", str(profile_get("models.vllm.model", "Qwen/Qwen3-32B-AWQ")))


def vllm_mode() -> str:
    """Get Qwen3 mode: 'thinking' (detailed reasoning) or 'fast' (quick responses)."""
    return env_str("VLLM_MODE", str(profile_get("models.vllm.mode", "thinking"))).lower()


def vllm_max_context() -> int:
    """Get vLLM max context length."""
    val = profile_get("models.vllm.max_context", None)
    if val is not None:
        return int(val)
    return int(env_str("VLLM_MAX_CONTEXT", "8192"))


# Remote HTTP LLM backend config
def remote_base_url() -> str:
    prof = profile_get("models.remote.base_url", "")
    if prof:
        return str(prof)
    return env_str("REMOTE_LLM_BASE_URL", "")


def remote_api_key() -> str:
    prof = profile_get("models.remote.api_key", "")
    if prof:
        return str(prof)
    return env_str("REMOTE_LLM_API_KEY", "")


def hf_base_model() -> str:
    return env_str("HF_BASE_MODEL", str(profile_get("models.hf.base_model", "Qwen/Qwen2.5-3B-Instruct")))


def hf_merged_model_dir() -> str:
    return env_str("HF_MERGED_MODEL_DIR", str(profile_get("models.hf.merged_model_dir", "")))


# src/agent/config.py

def hf_adapter_dir() -> str:
    # CHANGE: Point this default to your adapter path
    # Using os.path.abspath ensures it finds the folder regardless of where you run the command from
    default_path = os.path.join(os.getcwd(), "brain_training", "final_adapter")
    return env_str("HF_ADAPTER_DIR", str(profile_get("models.hf.adapter_dir", default_path)))


# src/agent/config.py

def hf_use_4bit() -> bool:
    val = profile_get("models.hf.use_4bit", None)
    if val is not None:
        return bool(val)
    return env_str("HF_USE_4BIT", "1").lower() in ("1", "true", "yes")


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
    # 'structured' | 'react' | 'multi_candidate'
    return env_str("PLANNING_MODE", str(profile_get("planning.mode", "structured"))).lower()


def use_multi_candidate_planning() -> bool:
    """Enable multi-candidate planning with verification and fallback."""
    val = profile_get("planning.use_multi_candidate", None)
    if val is not None:
        return bool(val)
    return env_str("USE_MULTI_CANDIDATE_PLANNING", "1").lower() in ("1", "true", "yes")


def num_plan_candidates() -> int:
    """Number of candidate plans to generate (default 3)."""
    return int(os.getenv("NUM_PLAN_CANDIDATES", str(profile_get("planning.num_candidates", 3))))


def max_action_retries() -> int:
    """Max retries per action before failing (default 2)."""
    return int(os.getenv("MAX_ACTION_RETRIES", str(profile_get("planning.max_retries", 2))))


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


def whatsapp_config() -> dict:
    return {
        "session_dir": env_str("WHATSAPP_SESSION_DIR", str(profile_get("apis.whatsapp.session_dir", ".agent/whatsapp_session"))),
        "headless": env_str("WHATSAPP_HEADLESS", str(profile_get("apis.whatsapp.headless", "false"))).lower() in ("1", "true", "yes"),
        "timeout_ms": int(env_str("WHATSAPP_TIMEOUT_MS", str(profile_get("apis.whatsapp.timeout_ms", "30000")))),
    }


# Desktop automation (dangerous, off by default)
def desktop_enabled() -> bool:
    # Enable only if explicitly set: env DESKTOP_AUTOMATION_ENABLED=1 or profile desktop.enabled: true
    prof = bool(profile_get("desktop.enabled", False))
    envv = env_str("DESKTOP_AUTOMATION_ENABLED", "0").lower() in ("1", "true", "yes")
    return bool(prof or envv)

# Persistent API Key Management
def _get_api_key_file() -> Path:
    """Get the path to the persistent API key file."""
    config_dir = Path.home() / ".kayas"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "api_key.txt"


def save_groq_api_key(api_key: str) -> bool:
    """Save the Groq API key to a file for persistent storage."""
    try:
        key_file = _get_api_key_file()
        key_file.write_text(api_key.strip(), encoding="utf-8")
        key_file.chmod(0o600)  # Restrict permissions for security
        return True
    except Exception as e:
        print(f"Warning: Could not save API key: {e}")
        return False


def load_groq_api_key_from_file() -> str:
    """Load the Groq API key from persistent storage."""
    try:
        key_file = _get_api_key_file()
        if key_file.exists():
            return key_file.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return ""


def ensure_groq_api_key() -> str:
    """Ensure Groq API key is set. Prompt user if needed."""
    # 1. Check environment variable first
    key = env_str("GROQ_API_KEY", "").strip()
    if key:
        return key
    
    # 2. Check saved file
    key = load_groq_api_key_from_file().strip()
    if key:
        os.environ["GROQ_API_KEY"] = key
        return key
    
    # 3. Prompt user
    print("\n" + "="*60)
    print("Groq API Key Required")
    print("="*60)
    print("\nYou need a Groq API key to use the SmartExecutor.")
    print("Get one free at: https://console.groq.com/keys")
    print("\nEnter your Groq API key (or 'skip' to use Ollama instead):")
    key = input("Groq API Key: ").strip()
    
    if key.lower() == "skip":
        print("Skipping Groq. Using Ollama backend instead.")
        return ""
    
    if key:
        # Save for future use
        if save_groq_api_key(key):
            print(f"✅ API key saved to {_get_api_key_file()}")
        os.environ["GROQ_API_KEY"] = key
        return key
    
    print("⚠️  No API key provided. Using Ollama backend instead.")
    return ""