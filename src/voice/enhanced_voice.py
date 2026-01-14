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
import json
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
    
    # STT settings - use 'medium' for better accent handling
    stt_model: str = "medium"  # Whisper model: tiny, base, small, medium, large-v3
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
    
    # Smart Recording settings
    max_recording_seconds: float = 30.0
    min_recording_seconds: float = 0.5
    
    # Silence detection (smarter)
    silence_threshold: float = 0.012           # Lower = more sensitive
    min_silence_for_pause: float = 0.5         # Brief pause - keep listening
    min_silence_for_sentence: float = 1.5      # Sentence end - might be done
    min_silence_for_done: float = 2.5          # Definitely done talking
    
    # Speech energy tracking
    speech_energy_threshold: float = 0.02      # Clear speech
    mumble_energy_threshold: float = 0.008     # Might be speech
    
    # Feedback sounds
    play_activation_sound: bool = True
    play_done_sound: bool = True
    
    # Post-transcription correction
    enable_transcription_correction: bool = True
    
    # Confidence thresholds
    min_confidence: float = 0.4           # Below this, reject as noise
    low_confidence_threshold: float = 0.65 # Below this, ask for confirmation
    ask_confirmation_on_low: bool = True  # Ask "Did you say X?" when uncertain
    
    # Common transcription errors and their corrections
    # Format: {"misheard": "correct"}
    transcription_corrections: Dict[str, str] = field(default_factory=lambda: {
        # Wake word corrections
        "guys": "Kayas",
        "hey guys": "Hey Kayas",
        "hi guys": "Hi Kayas",
        "chaos": "Kayas",
        "hey chaos": "Hey Kayas",
        "kaya": "Kayas",
        "hey kaya": "Hey Kayas",
        "gaia": "Kayas",
        "hey gaia": "Hey Kayas",
        "kaius": "Kayas",
        "casa": "Kayas",
        "gaias": "Kayas",
        "kaias": "Kayas",
        
        # Common name/word corrections for this user
        # (can be expanded by learn_correction())
    })


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
        
        # Context - names and terms from conversation
        self._known_names: set = set()  # Names mentioned in conversation
        self._context_words: set = set()  # Important words from recent context
        
        # Paths for persistence
        self._data_dir = Path.cwd() / ".agent"
        self._corrections_file = self._data_dir / "voice_corrections.json"
        self._names_file = self._data_dir / "known_names.json"
        
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
        
        # Load learned corrections and names
        self._load_corrections()
        self._load_known_names()
        
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
    
    # ==================== Transcription Correction ====================
    
    def correct_transcription(self, text: str) -> str:
        """
        Apply post-transcription corrections for common misheard words.
        
        This fixes words that Whisper consistently gets wrong for this user,
        especially names and specialized terms.
        
        Args:
            text: Raw transcribed text
        
        Returns:
            Corrected text
        """
        if not self.config.enable_transcription_correction or not text:
            return text
        
        corrected = text
        
        # Apply word/phrase replacements (case-insensitive matching)
        import re
        for wrong, right in self.config.transcription_corrections.items():
            # Use word boundaries to avoid partial replacements
            pattern = re.compile(re.escape(wrong), re.IGNORECASE)
            corrected = pattern.sub(right, corrected)
        
        if corrected != text:
            print(f"   [Correction] '{text}' → '{corrected}'")
        
        # Also apply context-aware name corrections
        corrected = self._apply_name_corrections(corrected)
        
        return corrected
    
    def learn_correction(self, wrong: str, right: str, persist: bool = True) -> None:
        """
        Add a new transcription correction and optionally save to disk.
        
        Args:
            wrong: The misheard word/phrase
            right: The correct word/phrase
            persist: Save to disk for future sessions
        """
        self.config.transcription_corrections[wrong.lower()] = right
        print(f"   [Learned] '{wrong}' → '{right}'")
        
        if persist:
            self._save_corrections()
    
    def _load_corrections(self) -> None:
        """Load learned corrections from disk."""
        try:
            if self._corrections_file.exists():
                with open(self._corrections_file, 'r') as f:
                    saved = json.load(f)
                # Merge with defaults (saved corrections take priority)
                self.config.transcription_corrections.update(saved)
                print(f"[EnhancedVoice] Loaded {len(saved)} learned corrections")
        except Exception as e:
            print(f"[EnhancedVoice] Could not load corrections: {e}")
    
    def _save_corrections(self) -> None:
        """Save learned corrections to disk."""
        try:
            self._data_dir.mkdir(exist_ok=True)
            with open(self._corrections_file, 'w') as f:
                json.dump(self.config.transcription_corrections, f, indent=2)
        except Exception as e:
            print(f"[EnhancedVoice] Could not save corrections: {e}")
    
    def get_learned_corrections(self) -> Dict[str, str]:
        """Get all current transcription corrections."""
        return dict(self.config.transcription_corrections)
    
    # ==================== Context-Aware Names ====================
    
    def _load_known_names(self) -> None:
        """Load known names from disk."""
        try:
            if self._names_file.exists():
                with open(self._names_file, 'r') as f:
                    names = json.load(f)
                self._known_names = set(names)
                print(f"[EnhancedVoice] Loaded {len(names)} known names")
        except Exception as e:
            print(f"[EnhancedVoice] Could not load names: {e}")
    
    def _save_known_names(self) -> None:
        """Save known names to disk."""
        try:
            self._data_dir.mkdir(exist_ok=True)
            with open(self._names_file, 'w') as f:
                json.dump(list(self._known_names), f, indent=2)
        except Exception as e:
            print(f"[EnhancedVoice] Could not save names: {e}")
    
    def add_known_name(self, name: str) -> None:
        """Add a name to the known names list."""
        name = name.strip().capitalize()
        if name and len(name) > 1:
            self._known_names.add(name)
            self._save_known_names()
            print(f"   [Name learned] '{name}'")
    
    def _find_similar_name(self, word: str) -> Optional[str]:
        """
        Find a known name that sounds similar to the given word.
        
        Uses phonetic similarity to match mishearings like Abdul->Abdus.
        """
        if not self._known_names:
            return None
        
        word_lower = word.lower()
        
        # Exact match
        for name in self._known_names:
            if name.lower() == word_lower:
                return name
        
        # Similar-sounding match (e.g., Abdul vs Abdus)
        import difflib
        best_match = None
        best_ratio = 0.7  # Minimum 70% similarity
        
        for name in self._known_names:
            ratio = difflib.SequenceMatcher(None, word_lower, name.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = name
        
        return best_match
    
    def _apply_name_corrections(self, text: str) -> str:
        """
        Replace words in text with known names if they sound similar.
        """
        if not self._known_names:
            return text
        
        words = text.split()
        corrected_words = []
        made_correction = False
        
        for word in words:
            # Check if this word should be a known name
            similar_name = self._find_similar_name(word)
            if similar_name and similar_name.lower() != word.lower():
                corrected_words.append(similar_name)
                made_correction = True
            else:
                corrected_words.append(word)
        
        if made_correction:
            corrected = " ".join(corrected_words)
            print(f"   [Name correction] '{text}' → '{corrected}'")
            return corrected
        
        return text
    
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
    
    def _is_sentence_complete(self, text: str) -> bool:
        """
        Check if transcribed text appears to be a complete thought.
        
        Returns True if:
        - Ends with punctuation (. ! ?)
        - Is a complete short command
        - Doesn't end with incomplete indicators
        
        Returns False if:
        - Ends mid-phrase (and, but, or, to, the, etc.)
        - Ends with trailing words suggesting more coming
        """
        if not text:
            return False
        
        text = text.strip().lower()
        
        # Ends with sentence-ending punctuation = complete
        if text[-1] in '.!?':
            return True
        
        # Common complete short commands (even without punctuation)
        complete_patterns = [
            'stop', 'cancel', 'quit', 'exit', 'yes', 'no', 'okay', 'ok',
            'thanks', 'thank you', 'never mind', 'nevermind',
            'what time is it', 'play music', 'pause', 'resume',
        ]
        for pattern in complete_patterns:
            if text == pattern or text.endswith(pattern):
                return True
        
        # Incomplete indicators - likely more coming
        incomplete_endings = [
            ' and', ' but', ' or', ' so', ' because', ' then',
            ' the', ' a', ' an', ' to', ' for', ' with', ' in', ' on',
            ' is', ' are', ' was', ' were', ' will', ' would', ' should',
            ' can', ' could', ' if', ' when', ' while', ' that', ' which',
            ' i', ' you', ' we', ' they', ' it', ' my', ' your', ' our',
        ]
        for ending in incomplete_endings:
            if text.endswith(ending):
                return False
        
        # If it's reasonably long and doesn't end with incomplete words, probably done
        word_count = len(text.split())
        if word_count >= 3:
            return True
        
        # Very short without punctuation - might be incomplete
        return False
    
    def listen(self, timeout: float = None, allow_continuation: bool = True) -> Optional[str]:
        """
        Listen for speech and transcribe with smart completeness detection.
        
        Args:
            timeout: Max seconds to listen (default from config)
            allow_continuation: If True, continue listening if sentence incomplete
        
        Returns:
            Transcribed text or None
        """
        result = self.listen_with_confidence(timeout, allow_continuation)
        if result:
            return result[0]
        return None
    
    def listen_with_confidence(self, timeout: float = None, allow_continuation: bool = True) -> Optional[tuple]:
        """
        Listen for speech and return transcription with confidence score.
        
        Args:
            timeout: Max seconds to listen (default from config)
            allow_continuation: If True, continue listening if sentence incomplete
        
        Returns:
            Tuple of (text, confidence) or None
        """
        if not AUDIO_AVAILABLE:
            print("[EnhancedVoice] Audio not available")
            return None
        
        if not self._whisper:
            print("[EnhancedVoice] Whisper not available")
            return None
        
        timeout = timeout or self.config.max_recording_seconds
        max_continuations = 2  # Max times to continue listening
        
        all_audio = []
        continuation_count = 0
        
        try:
            while continuation_count <= max_continuations:
                if continuation_count == 0:
                    print("🎤 Listening...")
                else:
                    print("🎤 Continue speaking...")
                
                # Record with voice activity detection
                audio_data = self._record_with_vad(timeout)
                
                if audio_data is None or len(audio_data) < self.config.sample_rate * self.config.min_recording_seconds:
                    if all_audio:
                        # Had some audio before, use what we have
                        break
                    print("[EnhancedVoice] No speech detected")
                    return None
                
                all_audio.append(audio_data)
                
                # Transcribe current audio
                print("📝 Transcribing...")
                combined_audio = np.concatenate(all_audio)
                segments_list = list(self._whisper.transcribe(
                    combined_audio,
                    language="en",
                    beam_size=1,
                    vad_filter=True
                )[0])  # Get segments from tuple
                
                # Extract text and confidence
                text_parts = []
                confidences = []
                for seg in segments_list:
                    text_parts.append(seg.text)
                    # avg_logprob is log probability, convert to probability
                    prob = 2 ** seg.avg_logprob if hasattr(seg, 'avg_logprob') else 1.0
                    confidences.append(min(prob, 1.0))  # Cap at 1.0
                
                text = " ".join(text_parts).strip()
                avg_confidence = sum(confidences) / len(confidences) if confidences else 1.0
                
                if not text:
                    if continuation_count > 0:
                        break  # Had audio before, this continuation was empty
                    return None
                
                # Confidence feedback
                if avg_confidence < self.config.min_confidence:
                    print(f"   [Low confidence: {avg_confidence:.0%}] Probably noise, ignoring...")
                    if continuation_count > 0:
                        break
                    return None
                elif avg_confidence < self.config.low_confidence_threshold:
                    print(f"💬 Heard (uncertain, {avg_confidence:.0%}): {text}")
                else:
                    print(f"💬 Heard ({avg_confidence:.0%}): {text}")
                
                # Check if sentence is complete
                if not allow_continuation or self._is_sentence_complete(text):
                    # Apply transcription correction before returning
                    corrected = self.correct_transcription(text)
                    print(f"✅ Complete: {corrected}")
                    return (corrected, avg_confidence)
                
                # Sentence seems incomplete, try continuing
                print("   [Sentence incomplete, waiting for more...]")
                continuation_count += 1
                time.sleep(0.3)  # Brief pause before continuing
            
            # Max continuations reached, return what we have
            if all_audio:
                combined_audio = np.concatenate(all_audio)
                segments_list = list(self._whisper.transcribe(
                    combined_audio,
                    language="en",
                    beam_size=1,
                    vad_filter=True
                )[0])
                
                # Recalculate confidence for final transcription
                text_parts = []
                confidences = []
                for seg in segments_list:
                    text_parts.append(seg.text)
                    prob = 2 ** seg.avg_logprob if hasattr(seg, 'avg_logprob') else 1.0
                    confidences.append(min(prob, 1.0))
                
                text = " ".join(text_parts).strip()
                avg_confidence = sum(confidences) / len(confidences) if confidences else 1.0
                
                if text:
                    # Apply transcription correction before returning
                    corrected = self.correct_transcription(text)
                    print(f"✅ Final (max continuations): {corrected}")
                    return (corrected, avg_confidence)
            
            return None
                
        except Exception as e:
            print(f"[EnhancedVoice] Listen error: {e}")
            return None
    
    def _record_with_vad(self, timeout: float) -> Optional[np.ndarray]:
        """
        Record audio with SMART voice activity detection.
        
        Improvements over basic VAD:
        - Tracks speech energy to distinguish clear speech from silence
        - Uses tiered silence detection (pause vs sentence-end vs done)
        - Longer tolerance for natural pauses mid-sentence
        - Requires more silence after energetic speech
        """
        sample_rate = self.config.sample_rate
        chunk_duration = 0.1  # 100ms chunks
        chunk_samples = int(sample_rate * chunk_duration)
        
        # Tiered silence thresholds
        silence_threshold = self.config.silence_threshold
        speech_threshold = self.config.speech_energy_threshold
        mumble_threshold = self.config.mumble_energy_threshold
        
        # Convert silence durations to chunk counts
        pause_chunks = int(self.config.min_silence_for_pause / chunk_duration)
        sentence_chunks = int(self.config.min_silence_for_sentence / chunk_duration)
        done_chunks = int(self.config.min_silence_for_done / chunk_duration)
        min_speech_chunks = int(self.config.min_recording_seconds / chunk_duration)
        
        audio_chunks = []
        silence_count = 0
        speech_started = False
        speech_chunk_count = 0
        peak_energy = 0.0
        recent_energies = []
        start_time = time.time()
        
        def audio_callback(indata, frames, time_info, status):
            nonlocal speech_started, silence_count, speech_chunk_count
            nonlocal peak_energy, recent_energies
            
            if status:
                return
            
            chunk = indata[:, 0].copy()
            rms = np.sqrt(np.mean(chunk**2))
            
            # Track energy history (last 10 chunks = 1 second)
            recent_energies.append(rms)
            if len(recent_energies) > 10:
                recent_energies.pop(0)
            
            # Update peak energy
            if rms > peak_energy:
                peak_energy = rms
            
            # Determine if this is speech
            is_clear_speech = rms > speech_threshold
            is_possible_speech = rms > mumble_threshold
            is_silence = rms < silence_threshold
            
            if is_clear_speech or (is_possible_speech and speech_started):
                speech_started = True
                silence_count = 0
                speech_chunk_count += 1
                audio_chunks.append(chunk)
                
            elif speech_started:
                # We're in a potential pause
                audio_chunks.append(chunk)  # Keep recording during pauses
                silence_count += 1
                
                # Determine how much silence is enough to stop
                # More energetic speech = need more silence to confirm done
                avg_recent_energy = sum(recent_energies) / len(recent_energies) if recent_energies else 0
                was_energetic = peak_energy > speech_threshold * 2
                has_enough_speech = speech_chunk_count >= min_speech_chunks
                
                # Decision logic:
                # - If we haven't recorded enough, keep going
                # - If speech was energetic, wait for "done" silence
                # - If speech was quiet, sentence-level silence is enough
                if has_enough_speech:
                    if was_energetic:
                        # They were speaking clearly - wait for longer silence
                        if silence_count >= done_chunks:
                            raise sd.CallbackAbort()
                    else:
                        # Quieter speech - sentence-level silence is fine
                        if silence_count >= sentence_chunks:
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
                    # Check if we should stop
                    has_enough = speech_chunk_count >= min_speech_chunks
                    was_energetic = peak_energy > speech_threshold * 2
                    
                    if has_enough:
                        if was_energetic and silence_count >= done_chunks:
                            break
                        elif not was_energetic and silence_count >= sentence_chunks:
                            break
                    
                    time.sleep(0.05)
                    
        except sd.CallbackAbort:
            pass  # Normal termination
        
        if not audio_chunks:
            return None
        
        # Debug info
        duration = len(audio_chunks) * chunk_duration
        print(f"   [VAD] Recorded {duration:.1f}s, peak energy: {peak_energy:.4f}")
        
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
