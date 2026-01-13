# -*- coding: utf-8 -*-
"""
Wake Word Detection for Kayas.

Listens for "Hey Kayas" (or similar) to activate the assistant.
Uses lightweight keyword spotting for low CPU usage.
"""

import threading
import queue
import time
from typing import Callable, Optional, List
from dataclasses import dataclass, field

# Try to import audio libraries
try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

# Try to import Vosk for offline wake word detection
try:
    from vosk import Model, KaldiRecognizer
    import json
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

# Try speech_recognition as fallback
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False


@dataclass
class WakeWordConfig:
    """Configuration for wake word detection."""
    
    # Wake words/phrases to listen for
    wake_words: List[str] = field(default_factory=lambda: [
        "hey kayas",
        "hi kayas",
        "kayas",
        "hey chaos",  # Common misrecognition
        "hey kaya",
        "okay kayas",
    ])
    
    # Audio settings
    sample_rate: int = 16000
    chunk_duration: float = 0.5  # Seconds per chunk
    
    # Detection settings
    cooldown_seconds: float = 1.0  # Min time between activations
    
    # Vosk model path (if using Vosk)
    vosk_model_path: Optional[str] = None


class WakeWordDetector:
    """
    Lightweight wake word detector.
    
    Listens continuously for the wake word with minimal CPU usage.
    When detected, calls the activation callback.
    """
    
    def __init__(self, config: WakeWordConfig = None):
        self.config = config or WakeWordConfig()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[], None]] = None
        self._last_activation = 0.0
        
        # Initialize detection engine
        self._vosk_model = None
        self._recognizer = None
        
        if VOSK_AVAILABLE:
            self._init_vosk()
        elif SR_AVAILABLE:
            self._init_speech_recognition()
    
    def _init_vosk(self):
        """Initialize Vosk for offline wake word detection."""
        try:
            # Use small model for speed
            model_path = self.config.vosk_model_path
            if not model_path:
                # Try common locations
                import os
                from pathlib import Path
                
                possible_paths = [
                    Path.home() / ".cache" / "vosk" / "vosk-model-small-en-us-0.15",
                    Path("models") / "vosk-model-small-en-us-0.15",
                    Path(__file__).parent / "models" / "vosk-model-small-en-us-0.15",
                ]
                
                for p in possible_paths:
                    if p.exists():
                        model_path = str(p)
                        break
            
            if model_path:
                self._vosk_model = Model(model_path)
                print(f"[WakeWord] Vosk model loaded from {model_path}")
            else:
                print("[WakeWord] Vosk model not found. Will use speech_recognition fallback.")
                self._init_speech_recognition()
        except Exception as e:
            print(f"[WakeWord] Vosk init failed: {e}")
            self._init_speech_recognition()
    
    def _init_speech_recognition(self):
        """Initialize speech_recognition as fallback."""
        if SR_AVAILABLE:
            self._recognizer = sr.Recognizer()
            # Lower energy threshold for wake word detection
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True
            print("[WakeWord] Using speech_recognition for wake word detection")
    
    def _check_wake_word(self, text: str) -> bool:
        """Check if text contains a wake word."""
        text_lower = text.lower().strip()
        
        for wake_word in self.config.wake_words:
            if wake_word in text_lower:
                return True
        
        return False
    
    def _detection_loop_vosk(self):
        """Detection loop using Vosk."""
        if not self._vosk_model or not SOUNDDEVICE_AVAILABLE:
            return
        
        rec = KaldiRecognizer(self._vosk_model, self.config.sample_rate)
        rec.SetWords(True)
        
        chunk_size = int(self.config.sample_rate * self.config.chunk_duration)
        
        def audio_callback(indata, frames, time_info, status):
            if status:
                return
            
            # Convert to int16
            audio_data = (indata[:, 0] * 32767).astype(np.int16).tobytes()
            
            if rec.AcceptWaveform(audio_data):
                result = json.loads(rec.Result())
                text = result.get("text", "")
                
                if text and self._check_wake_word(text):
                    self._trigger_activation()
        
        try:
            with sd.InputStream(
                channels=1,
                samplerate=self.config.sample_rate,
                blocksize=chunk_size,
                dtype=np.float32,
                callback=audio_callback
            ):
                while self._running:
                    time.sleep(0.1)
        except Exception as e:
            print(f"[WakeWord] Audio stream error: {e}")
    
    def _detection_loop_sr(self):
        """Detection loop using speech_recognition."""
        if not self._recognizer or not SR_AVAILABLE:
            return
        
        mic = sr.Microphone()
        
        with mic as source:
            # Adjust for ambient noise once
            self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        def listen_in_background(recognizer, audio):
            try:
                # Use Google Speech Recognition (requires internet)
                text = recognizer.recognize_google(audio)
                
                if self._check_wake_word(text):
                    self._trigger_activation()
            except sr.UnknownValueError:
                pass  # No speech detected
            except sr.RequestError as e:
                print(f"[WakeWord] Recognition error: {e}")
        
        # Start background listening
        stop_listening = self._recognizer.listen_in_background(
            mic,
            listen_in_background,
            phrase_time_limit=3
        )
        
        try:
            while self._running:
                time.sleep(0.1)
        finally:
            stop_listening(wait_for_stop=False)
    
    def _trigger_activation(self):
        """Trigger the activation callback with cooldown."""
        now = time.time()
        
        if now - self._last_activation < self.config.cooldown_seconds:
            return  # Still in cooldown
        
        self._last_activation = now
        print("[WakeWord] Wake word detected!")
        
        if self._callback:
            # Call in separate thread to not block detection
            threading.Thread(target=self._callback, daemon=True).start()
    
    def start(self, callback: Callable[[], None]):
        """
        Start wake word detection.
        
        Args:
            callback: Function to call when wake word is detected
        """
        if self._running:
            return
        
        self._running = True
        self._callback = callback
        
        if self._vosk_model:
            target = self._detection_loop_vosk
        elif self._recognizer:
            target = self._detection_loop_sr
        else:
            print("[WakeWord] No detection engine available!")
            return
        
        self._thread = threading.Thread(target=target, name="WakeWordDetector", daemon=True)
        self._thread.start()
        print("[WakeWord] Started listening for wake word...")
    
    def stop(self):
        """Stop wake word detection."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("[WakeWord] Stopped")
    
    def is_running(self) -> bool:
        """Check if detector is running."""
        return self._running


# Simplified detection without Vosk (uses continuous short recordings)
class SimpleWakeWordDetector:
    """
    Simple wake word detector using short recording snippets.
    
    More CPU intensive than Vosk but works without additional models.
    """
    
    def __init__(self, wake_words: List[str] = None):
        self.wake_words = wake_words or [
            "hey kayas", "hi kayas", "kayas", 
            "hey chaos", "okay kayas", "hey kaya",
            # Common Whisper transcription variations
            "hey guys", "hi guys", "guys",
            "hey gaia", "hey kaius", "hey kias",
            "hey casa", "hey kas", "hey cass",
            "hey gaias", "hey kaias",
            "k yas", "kayaz", "kyaz",
        ]
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[], None]] = None
        self._last_activation = 0.0
        
        # Try to use faster-whisper for better accuracy
        self._whisper = None
        try:
            from faster_whisper import WhisperModel
            self._whisper = WhisperModel("tiny", device="cpu", compute_type="int8")
            print("[WakeWord] Using faster-whisper for detection")
        except ImportError:
            print("[WakeWord] faster-whisper not available")
    
    def _check_wake_word(self, text: str) -> bool:
        text_lower = text.lower().strip()
        for wake_word in self.wake_words:
            if wake_word in text_lower:
                return True
        return False
    
    def _detection_loop(self):
        """Main detection loop."""
        if not SOUNDDEVICE_AVAILABLE:
            print("[WakeWord] sounddevice not available!")
            return
        
        sample_rate = 16000
        chunk_duration = 2.0  # 2 second chunks
        debug_counter = 0
        
        while self._running:
            try:
                # Record short audio chunk
                audio = sd.rec(
                    int(chunk_duration * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype=np.float32
                )
                sd.wait()
                
                # Check for speech (simple energy detection)
                rms = np.sqrt(np.mean(audio**2))
                
                # Debug output every 5 cycles
                debug_counter += 1
                if debug_counter % 5 == 0:
                    print(f"[WakeWord] Audio level: {rms:.4f} (threshold: 0.005)")
                
                if rms < 0.005:  # Lowered threshold
                    continue  # Too quiet, skip transcription
                
                print(f"[WakeWord] 🎙️ Detected speech (level: {rms:.3f}), transcribing...")
                
                # Transcribe
                text = ""
                if self._whisper:
                    segments, _ = self._whisper.transcribe(
                        audio.flatten(),
                        language="en",
                        beam_size=1,
                        vad_filter=True
                    )
                    text = " ".join(seg.text for seg in segments).strip()
                
                if text:
                    print(f"[WakeWord] Heard: '{text}'")
                
                # Check for wake word
                if text and self._check_wake_word(text):
                    self._trigger_activation()
                    time.sleep(1.0)  # Cooldown
                    
            except Exception as e:
                print(f"[WakeWord] Error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.5)
    
    def _trigger_activation(self):
        now = time.time()
        if now - self._last_activation < 1.0:
            return
        
        self._last_activation = now
        print("[WakeWord] 🎤 Wake word detected!")
        
        if self._callback:
            threading.Thread(target=self._callback, daemon=True).start()
    
    def start(self, callback: Callable[[], None]):
        if self._running:
            return
        
        self._running = True
        self._callback = callback
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()
        print("[WakeWord] Listening for 'Hey Kayas'...")
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)


def create_wake_word_detector(use_vosk: bool = False) -> WakeWordDetector | SimpleWakeWordDetector:
    """Factory function to create appropriate wake word detector."""
    if use_vosk and VOSK_AVAILABLE:
        return WakeWordDetector()
    else:
        return SimpleWakeWordDetector()
