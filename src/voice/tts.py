from __future__ import annotations

from typing import Optional

import numpy as np

from ..agent.config import tts_engine, tts_model


def speak(text: str) -> None:
    engine = tts_engine()
    if engine == "coqui":
        try:
            from TTS.api import TTS
            import simpleaudio as sa

            model_name = tts_model()
            tts = TTS(model_name)
            # Generate waveform (22050 Hz default)
            wav = tts.tts(text)
            wav_np = np.array(wav, dtype=np.float32)
            # Normalize to int16
            audio = (wav_np * 32767).astype(np.int16)
            play_obj = sa.play_buffer(audio, 1, 2, 22050)
            play_obj.wait_done()
            return
        except Exception as e:
            print(f"[voice] Coqui TTS failed, falling back to pyttsx3: {e}")

    # Fallback: pyttsx3 (offline TTS)
    try:
        import pyttsx3

        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"[voice] pyttsx3 failed: {e}")
