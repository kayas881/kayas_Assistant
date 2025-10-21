from __future__ import annotations

from typing import Optional

from .main import run_agent
from ..voice.tts import speak


def dialog_once(listen_seconds: float = 5.0) -> dict:
    # 1) Listen (lazy import with fallback)
    try:
        from ..voice.stt import stt_listen  # type: ignore
        user_text = stt_listen(seconds=listen_seconds)
    except Exception:
        print("[voice] STT dependencies not installed. Falling back to typed input.")
        try:
            user_text = input("Type your request for Kayas: ").strip()
        except Exception:
            user_text = ""
    if not user_text:
        speak("I didn't catch that. Could you repeat?")
        return {"heard": "", "response": ""}

    # 2) Run agent
    out = run_agent(user_text)

    # 3) Speak back
    if out.get("artifact"):
        speak("I completed your request. I saved the result in the artifacts folder.")
    else:
        speak("I completed your request.")
    return {"heard": user_text, "response": out}
