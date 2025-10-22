"""
Voice interface for the agent using speech-to-text and text-to-speech.
Supports Whisper for STT and pyttsx3/Coqui for TTS.
"""
from __future__ import annotations

import threading
import time
import queue
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable, Any, Dict
import tempfile
import os

try:
    import speech_recognition as sr
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    import sounddevice as sd
    import numpy as np
    import scipy.io.wavfile as wav
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

from ..agent.config import whisper_model, tts_engine, tts_model


@dataclass
class VoiceConfig:
    stt_engine: str = "whisper"  # "whisper" | "speech_recognition"
    tts_engine: str = "pyttsx3"  # "pyttsx3" | "coqui"
    whisper_model: str = "small"  # small, base, medium, large-v3
    tts_model: str = "tts_models/en/ljspeech/tacotron2-DDC"  # for Coqui
    sample_rate: int = 16000
    chunk_duration: float = 1.0  # seconds per audio chunk
    silence_threshold: float = 0.01  # amplitude threshold for silence detection
    silence_duration: float = 2.0  # seconds of silence before stopping recording
    max_recording_duration: float = 30.0  # max seconds per recording
    voice_activation_threshold: float = 0.02  # threshold for voice activity detection


class VoiceAgent:
    def __init__(self, cfg: VoiceConfig | None = None):
        self.cfg = cfg or VoiceConfig()
        self._whisper_model: Optional[Any] = None
        self._tts_engine: Optional[Any] = None
        self._recognizer: Optional[sr.Recognizer] = None
        self._microphone: Optional[sr.Microphone] = None
        self._recording = False
        self._listening = False
        self._stop_listening: Optional[Callable] = None
        self._audio_queue: queue.Queue = queue.Queue()
        
        self._init_stt()
        self._init_tts()

    def _init_stt(self):
        """Initialize speech-to-text engine."""
        if self.cfg.stt_engine == "whisper" and WHISPER_AVAILABLE:
            try:
                print(f"Loading Whisper model: {self.cfg.whisper_model}")
                self._whisper_model = whisper.load_model(self.cfg.whisper_model)
                print("Whisper model loaded successfully")
            except Exception as e:
                print(f"Failed to load Whisper model: {e}")
                self._whisper_model = None
        
        if self.cfg.stt_engine == "speech_recognition" and STT_AVAILABLE:
            self._recognizer = sr.Recognizer()
            self._microphone = sr.Microphone()
            # Adjust for ambient noise
            try:
                with self._microphone as source:
                    print("Adjusting for ambient noise...")
                    self._recognizer.adjust_for_ambient_noise(source, duration=1)
                    print("Ambient noise adjustment complete")
            except Exception as e:
                print(f"Failed to adjust for ambient noise: {e}")

    def _init_tts(self):
        """Initialize text-to-speech engine."""
        if self.cfg.tts_engine == "pyttsx3" and PYTTSX3_AVAILABLE:
            try:
                self._tts_engine = pyttsx3.init()
                # Configure voice properties
                voices = self._tts_engine.getProperty('voices')
                if voices:
                    # Prefer female voice if available
                    for voice in voices:
                        if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                            self._tts_engine.setProperty('voice', voice.id)
                            break
                
                # Set speech rate and volume
                self._tts_engine.setProperty('rate', 180)  # words per minute
                self._tts_engine.setProperty('volume', 0.8)  # 0.0 to 1.0
                print("TTS engine initialized successfully")
            except Exception as e:
                print(f"Failed to initialize TTS engine: {e}")
                self._tts_engine = None

    def speak(self, text: str) -> bool:
        """Convert text to speech."""
        if not text.strip():
            return True
            
        try:
            if self._tts_engine and self.cfg.tts_engine == "pyttsx3":
                # Use a lock to prevent concurrent TTS operations
                if not hasattr(self, '_tts_lock'):
                    self._tts_lock = threading.Lock()
                
                # Don't run in thread - pyttsx3 doesn't like multiple threads
                with self._tts_lock:
                    self._tts_engine.say(text)
                    self._tts_engine.runAndWait()
                return True
            elif self.cfg.tts_engine == "coqui":
                # TODO: Implement Coqui TTS
                print(f"[TTS] {text}")
                return True
            else:
                print(f"[TTS] {text}")
                return True
        except Exception as e:
            print(f"TTS error: {e}")
            print(f"[TTS] {text}")
            return False

    def listen_once(self, timeout: float = 5.0) -> Optional[str]:
        """Listen for a single utterance and return transcribed text."""
        if self.cfg.stt_engine == "whisper" and self._whisper_model and SOUNDDEVICE_AVAILABLE:
            return self._listen_with_whisper(timeout)
        elif self.cfg.stt_engine == "speech_recognition" and self._recognizer and self._microphone:
            return self._listen_with_speech_recognition(timeout)
        else:
            print("No STT engine available")
            return None

    def _listen_with_whisper(self, timeout: float) -> Optional[str]:
        """Record audio and transcribe with Whisper."""
        try:
            print("Listening... (speak now)")
            
            # Record audio
            duration = min(timeout, self.cfg.max_recording_duration)
            sample_rate = self.cfg.sample_rate
            
            # Record with voice activity detection
            audio_data = []
            chunk_size = int(sample_rate * self.cfg.chunk_duration)
            silence_chunks = 0
            max_silence_chunks = int(self.cfg.silence_duration / self.cfg.chunk_duration)
            
            recording_started = False
            
            def audio_callback(indata, frames, time, status):
                nonlocal recording_started, silence_chunks
                if status:
                    print(f"Audio callback status: {status}")
                
                # Calculate RMS (volume level)
                rms = np.sqrt(np.mean(indata**2))
                
                # Voice activity detection
                if rms > self.cfg.voice_activation_threshold:
                    recording_started = True
                    silence_chunks = 0
                    audio_data.extend(indata.flatten())
                elif recording_started:
                    silence_chunks += 1
                    audio_data.extend(indata.flatten())
                    
                    # Stop if too much silence
                    if silence_chunks >= max_silence_chunks:
                        raise sd.CallbackAbort()

            try:
                with sd.InputStream(callback=audio_callback, 
                                  channels=1, 
                                  samplerate=sample_rate,
                                  blocksize=chunk_size):
                    sd.sleep(int(duration * 1000))  # Convert to milliseconds
            except sd.CallbackAbort:
                pass  # Normal termination due to silence
            
            if not audio_data:
                print("No audio recorded")
                return None
                
            # Convert to numpy array
            audio_array = np.array(audio_data, dtype=np.float32)
            
            # Save to temporary file for Whisper
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                wav.write(tmp_file.name, sample_rate, audio_array)
                tmp_path = tmp_file.name
            
            try:
                # Transcribe with Whisper
                print("Transcribing...")
                result = self._whisper_model.transcribe(tmp_path)
                text = result.get("text", "").strip()
                
                if text:
                    print(f"Transcribed: {text}")
                    return text
                else:
                    print("No speech detected")
                    return None
                    
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"Whisper STT error: {e}")
            return None

    def _listen_with_speech_recognition(self, timeout: float) -> Optional[str]:
        """Listen and transcribe with speech_recognition library."""
        try:
            print("Listening... (speak now)")
            with self._microphone as source:
                # Listen for audio
                audio = self._recognizer.listen(source, timeout=timeout, phrase_time_limit=self.cfg.max_recording_duration)
                
            print("Transcribing...")
            # Try Google Speech Recognition (requires internet)
            try:
                text = self._recognizer.recognize_google(audio)
                print(f"Transcribed: {text}")
                return text
            except sr.UnknownValueError:
                print("Could not understand audio")
                return None
            except sr.RequestError as e:
                print(f"Speech recognition service error: {e}")
                return None
                
        except sr.WaitTimeoutError:
            print("Listening timeout")
            return None
        except Exception as e:
            print(f"Speech recognition error: {e}")
            return None

    def start_continuous_listening(self, callback: Callable[[str], None]):
        """Start continuous listening mode with callback for each transcription."""
        if self._listening:
            return
            
        self._listening = True
        
        def _listen_loop():
            while self._listening:
                try:
                    text = self.listen_once(timeout=10.0)
                    if text and text.strip():
                        callback(text)
                except Exception as e:
                    print(f"Continuous listening error: {e}")
                    time.sleep(1)  # Brief pause before retrying
        
        thread = threading.Thread(target=_listen_loop, daemon=True)
        thread.start()
        print("Started continuous listening")

    def stop_continuous_listening(self):
        """Stop continuous listening mode."""
        self._listening = False
        print("Stopped continuous listening")

    def is_available(self) -> Dict[str, bool]:
        """Check availability of voice components."""
        return {
            "stt_whisper": WHISPER_AVAILABLE and self._whisper_model is not None,
            "stt_speech_recognition": STT_AVAILABLE and self._recognizer is not None,
            "tts_pyttsx3": PYTTSX3_AVAILABLE and self._tts_engine is not None,
            "sounddevice": SOUNDDEVICE_AVAILABLE,
        }

    def __del__(self):
        """Cleanup resources."""
        self.stop_continuous_listening()