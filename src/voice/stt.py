from __future__ import annotations

import queue
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from ..agent.config import whisper_model


def record_audio(seconds: float = 5.0, sample_rate: int = 16000) -> np.ndarray:
    print(f"[voice] Recording {seconds}s…")
    audio = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    return audio.flatten()


def transcribe(audio: np.ndarray, sample_rate: int = 16000, model_name: Optional[str] = None) -> str:
    name = model_name or whisper_model()
    model = WhisperModel(name)
    segments, info = model.transcribe(audio, language="en", beam_size=1)
    text_parts = []
    for seg in segments:
        text_parts.append(seg.text)
    text = " ".join(text_parts).strip()
    return text


def stt_listen(seconds: float = 5.0) -> str:
    audio = record_audio(seconds=seconds)
    return transcribe(audio)
