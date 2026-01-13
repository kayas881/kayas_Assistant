# -*- coding: utf-8 -*-
"""
Enhanced Voice Agent for Kayas.

Features:
- Natural TTS using Edge TTS (Microsoft neural voices)
- Wake word detection ("Hey Kayas")
- Continuous listening mode
- Push-to-talk support
- Voice activity detection
"""

import threading
import queue
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any, List
from pathlib import Path

# Audio libraries
try:
    import sounddevice as sd
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

# Whisper for STT
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

# Edge TTS
try:
    from .edge_tts import EdgeTTS, get_edge_tts, EDGE_TTS_AVAILABLE
except ImportError:
    EDGE_TTS_AVAILABLE = False

# Wake word
try:
    from .wake_word import SimpleWakeWordDetector
    WAKE_WORD_AVAILABLE = True
except ImportError:
    WAKE_WORD_AVAILABLE = False

# Fallback TTS
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


@dataclass
class EnhancedVoiceConfig:
    """Configuration for the enhanced voice agent."""
    
    # TTS settings
    tts_engine: str = "edge"  # "edge" | "pyttsx3"
    tts_voice: str = "jenny"  # Edge voice shorthand or full ID
    tts_rate: str = "+5%"     # Speaking rate
    
    # STT settings
    stt_model: str = "small"  # Whisper model: tiny, base, small, medium
    sample_rate: int = 16000
    
    # Wake word settings
    enable_wake_word: bool = True
    wake_words: List[str] = field(default_factory=lambda: [
        # Primary wake words
        "hey kayas", "hi kayas", "kayas", "okay kayas",
        # Common Whisper transcription variations (for Indian accent)
        "hey guys", "hi guys", "guys",
        "hey chaos", "hey kaya", "kaya",
        "hey gaia", "hey kaius", "hey kias",
        "hey casa", "hey kas", "hey cass",
        "hey gaias", "hey kaias", "take guys",
        "k yas", "kayaz", "kyaz",
    ])
    
    # Recording settings
    max_recording_seconds: float = 30.0
    silence_threshold: float = 0.015
    silence_duration: float = 1.5  # Seconds of silence to stop recording
    min_recording_seconds: float = 0.5
    
    # Feedback sounds
    play_activation_sound: bool = True
    play_done_sound: bool = True


class EnhancedVoiceAgent:
    """
    Enhanced voice interface for Kayas.
    
    Provides natural voice interaction with:
    - High-quality neural TTS
    - Accurate speech recognition
    - Wake word activation
    - Continuous listening mode
    """
    
    def __init__(self, config: EnhancedVoiceConfig = None):
        self.config = config or EnhancedVoiceConfig()
        
        # State
        self._listening = False
        self._speaking = False
        self._wake_word_active = False
        
        # Components
        self._tts: Optional[EdgeTTS] = None
        self._whisper: Optional[WhisperModel] = None
        self._wake_detector: Optional[SimpleWakeWordDetector] = None
        self._pyttsx_engine = None
        
        # Threading
        self._audio_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        
        # Initialize components
        self._init_tts()
        self._init_stt()
        if self.config.enable_wake_word:
            self._init_wake_word()
        
        print("[EnhancedVoice] Initialized")
    
    def _init_tts(self):
        """Initialize text-to-speech."""
        if self.config.tts_engine == "edge" and EDGE_TTS_AVAILABLE:
            try:
                from .edge_tts import EdgeTTS
                self._tts = EdgeTTS(
                    voice=self.config.tts_voice,
                    rate=self.config.tts_rate
                )
                print(f"[EnhancedVoice] Edge TTS initialized with voice: {self.config.tts_voice}")
                return
            except Exception as e:
                print(f"[EnhancedVoice] Edge TTS failed: {e}")
        
        # Fallback to pyttsx3
        if PYTTSX3_AVAILABLE:
            try:
                # Initialize in background thread to avoid COM issues
                def init_pyttsx():
                    self._pyttsx_engine = pyttsx3.init()
                    voices = self._pyttsx_engine.getProperty('voices')
                    # Try to find a female voice
                    for voice in voices:
                        if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                            self._pyttsx_engine.setProperty('voice', voice.id)
                            break
                    self._pyttsx_engine.setProperty('rate', 180)
                
                t = threading.Thread(target=init_pyttsx)
                t.start()
                t.join(timeout=3.0)
                print("[EnhancedVoice] pyttsx3 TTS initialized")
            except Exception as e:
                print(f"[EnhancedVoice] pyttsx3 failed: {e}")
    
    def _init_stt(self):
        """Initialize speech-to-text."""
        if not WHISPER_AVAILABLE:
            print("[EnhancedVoice] Whisper not available - STT disabled")
            return
        
        try:
            # Use small model for balance of speed and accuracy
            model_name = self.config.stt_model
            print(f"[EnhancedVoice] Loading Whisper model: {model_name}")
            self._whisper = WhisperModel(model_name, device="cpu", compute_type="int8")
            print("[EnhancedVoice] Whisper loaded successfully")
        except Exception as e:
            print(f"[EnhancedVoice] Whisper init failed: {e}")
    
    def _init_wake_word(self):
        """Initialize wake word detection."""
        if not WAKE_WORD_AVAILABLE:
            print("[EnhancedVoice] Wake word detection not available")
            return
        
        try:
            self._wake_detector = SimpleWakeWordDetector(wake_words=self.config.wake_words)
            print("[EnhancedVoice] Wake word detector initialized")
        except Exception as e:
            print(f"[EnhancedVoice] Wake word init failed: {e}")
    
    # ==================== TTS ====================
    
    def speak(self, text: str, blocking: bool = True) -> bool:
        """
        Speak text using TTS.
        
        Args:
            text: Text to speak
            blocking: Wait for speech to complete
        
        Returns:
            True if successful
        """
        if not text.strip():
            return True
        
        self._speaking = True
        
        try:
            if self._tts:
                self._tts.speak(text, blocking=blocking)
                return True
            elif self._pyttsx_engine:
                self._pyttsx_engine.say(text)
                if blocking:
                    self._pyttsx_engine.runAndWait()
                return True
            else:
                print(f"[TTS] {text}")
                return True
        except Exception as e:
            print(f"[EnhancedVoice] TTS error: {e}")
            print(f"[TTS] {text}")
            return False
        finally:
            self._speaking = False
    
    def speak_async(self, text: str) -> None:
        """Speak without blocking."""
        threading.Thread(target=self.speak, args=(text, True), daemon=True).start()
    
    # ==================== STT ====================
    
    def listen(self, timeout: float = None) -> Optional[str]:
        """
        Listen for speech and transcribe.
        
        Args:
            timeout: Max seconds to listen (default from config)
        
        Returns:
            Transcribed text or None
        """
        if not AUDIO_AVAILABLE:
            print("[EnhancedVoice] Audio not available")
            return None
        
        if not self._whisper:
            print("[EnhancedVoice] Whisper not available")
            return None
        
        timeout = timeout or self.config.max_recording_seconds
        
        try:
            print("🎤 Listening...")
            
            # Record with voice activity detection
            audio_data = self._record_with_vad(timeout)
            
            if audio_data is None or len(audio_data) < self.config.sample_rate * self.config.min_recording_seconds:
                print("[EnhancedVoice] No speech detected")
                return None
            
            # Transcribe
            print("📝 Transcribing...")
            segments, info = self._whisper.transcribe(
                audio_data,
                language="en",
                beam_size=1,
                vad_filter=True
            )
            
            text = " ".join(seg.text for seg in segments).strip()
            
            if text:
                print(f"💬 You said: {text}")
                return text
            else:
                return None
                
        except Exception as e:
            print(f"[EnhancedVoice] Listen error: {e}")
            return None
    
    def _record_with_vad(self, timeout: float) -> Optional[np.ndarray]:
        """Record audio with voice activity detection."""
        sample_rate = self.config.sample_rate
        chunk_duration = 0.1  # 100ms chunks
        chunk_samples = int(sample_rate * chunk_duration)
        
        silence_threshold = self.config.silence_threshold
        max_silence_chunks = int(self.config.silence_duration / chunk_duration)
        
        audio_chunks = []
        silence_count = 0
        speech_started = False
        start_time = time.time()
        
        def audio_callback(indata, frames, time_info, status):
            nonlocal speech_started, silence_count
            
            if status:
                return
            
            chunk = indata[:, 0].copy()
            rms = np.sqrt(np.mean(chunk**2))
            
            if rms > silence_threshold:
                speech_started = True
                silence_count = 0
                audio_chunks.append(chunk)
            elif speech_started:
                audio_chunks.append(chunk)
                silence_count += 1
                
                if silence_count >= max_silence_chunks:
                    raise sd.CallbackAbort()
        
        try:
            with sd.InputStream(
                channels=1,
                samplerate=sample_rate,
                blocksize=chunk_samples,
                dtype=np.float32,
                callback=audio_callback
            ):
                # Wait for recording to complete or timeout
                while time.time() - start_time < timeout:
                    if len(audio_chunks) > 0 and silence_count >= max_silence_chunks:
                        break
                    time.sleep(0.05)
        except sd.CallbackAbort:
            pass  # Normal termination
        
        if not audio_chunks:
            return None
        
        return np.concatenate(audio_chunks)
    
    # ==================== Wake Word ====================
    
    def start_wake_word_listening(self, on_wake: Callable[[], None]):
        """
        Start listening for wake word.
        
        Args:
            on_wake: Callback when wake word is detected
        """
        if not self._wake_detector:
            print("[EnhancedVoice] Wake word detector not available")
            return
        
        if self._wake_word_active:
            return
        
        self._wake_word_active = True
        
        def on_wake_word():
            if self._speaking:
                return  # Don't activate while speaking
            on_wake()
        
        self._wake_detector.start(on_wake_word)
        print("🎤 Say 'Hey Kayas' to activate...")
    
    def stop_wake_word_listening(self):
        """Stop wake word detection."""
        if self._wake_detector:
            self._wake_detector.stop()
        self._wake_word_active = False
    
    # ==================== Continuous Mode ====================
    
    def start_continuous_mode(self, on_input: Callable[[str], None], use_wake_word: bool = True):
        """
        Start continuous voice interaction mode.
        
        Args:
            on_input: Callback for each voice input
            use_wake_word: If True, require wake word before listening
        """
        self._listening = True
        
        def handle_voice_input():
            # Play activation sound
            if self.config.play_activation_sound:
                self._play_beep(440, 0.1)
            
            # Listen for command
            text = self.listen()
            
            if text:
                # Play done sound
                if self.config.play_done_sound:
                    self._play_beep(880, 0.05)
                
                on_input(text)
        
        if use_wake_word and self._wake_detector:
            # Wake word mode
            self.start_wake_word_listening(handle_voice_input)
        else:
            # Continuous without wake word
            def loop():
                while self._listening:
                    text = self.listen(timeout=10.0)
                    if text:
                        on_input(text)
                    time.sleep(0.1)
            
            threading.Thread(target=loop, daemon=True).start()
    
    def stop_continuous_mode(self):
        """Stop continuous listening."""
        self._listening = False
        self.stop_wake_word_listening()
    
    def _play_beep(self, frequency: float, duration: float):
        """Play a simple beep sound."""
        if not AUDIO_AVAILABLE:
            return
        
        try:
            sample_rate = 44100
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            wave = 0.3 * np.sin(2 * np.pi * frequency * t)
            sd.play(wave.astype(np.float32), sample_rate)
        except Exception:
            pass
    
    # ==================== Status ====================
    
    def is_available(self) -> Dict[str, bool]:
        """Check component availability."""
        return {
            "tts_edge": self._tts is not None,
            "tts_pyttsx3": self._pyttsx_engine is not None,
            "stt_whisper": self._whisper is not None,
            "wake_word": self._wake_detector is not None,
            "audio": AUDIO_AVAILABLE,
        }
    
    def is_speaking(self) -> bool:
        return self._speaking
    
    def is_listening(self) -> bool:
        return self._listening
    
    # ==================== Cleanup ====================
    
    def shutdown(self):
        """Clean shutdown."""
        self.stop_continuous_mode()
        
        if self._tts:
            self._tts.shutdown()
        
        self._stop_event.set()
        print("[EnhancedVoice] Shutdown complete")


# Convenience function
def create_enhanced_voice_agent(config: EnhancedVoiceConfig = None) -> EnhancedVoiceAgent:
    """Create an enhanced voice agent."""
    return EnhancedVoiceAgent(config)
