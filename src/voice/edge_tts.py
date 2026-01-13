# -*- coding: utf-8 -*-
"""
Enhanced Text-to-Speech using Microsoft Edge TTS.

Edge TTS provides high-quality neural voices for free, sounding much more
natural than pyttsx3. It requires internet but works great for a companion AI.
"""

import asyncio
import tempfile
import os
from pathlib import Path
from typing import Optional
import threading
import queue

# Check for edge-tts availability
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    print("[EdgeTTS] edge-tts not installed. Run: pip install edge-tts")

# Check for audio playback
try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


# Available voices (subset of best ones)
VOICES = {
    # US English
    "jenny": "en-US-JennyNeural",      # Female, friendly
    "aria": "en-US-AriaNeural",        # Female, professional
    "guy": "en-US-GuyNeural",          # Male, casual
    "davis": "en-US-DavisNeural",      # Male, professional
    
    # UK English
    "sonia": "en-GB-SoniaNeural",      # Female, British
    "ryan": "en-GB-RyanNeural",        # Male, British
    
    # Other accents
    "natasha": "en-AU-NatashaNeural",  # Female, Australian
    "connor": "en-IE-ConnorNeural",    # Male, Irish
}

# Default voice - Jenny sounds friendly and natural
DEFAULT_VOICE = "en-US-JennyNeural"


class EdgeTTS:
    """
    High-quality TTS using Microsoft Edge's neural voices.
    
    Usage:
        tts = EdgeTTS()
        tts.speak("Hello, how are you today?")
    """
    
    def __init__(self, voice: str = None, rate: str = "+0%", pitch: str = "+0Hz"):
        """
        Initialize Edge TTS.
        
        Args:
            voice: Voice ID or shorthand (e.g., "jenny", "en-US-JennyNeural")
            rate: Speaking rate (e.g., "+10%", "-20%")
            pitch: Voice pitch (e.g., "+5Hz", "-10Hz")
        """
        self.voice = self._resolve_voice(voice or DEFAULT_VOICE)
        self.rate = rate
        self.pitch = pitch
        
        # Temp directory for audio files
        self.temp_dir = Path(tempfile.gettempdir()) / "kayas_tts"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Background playback queue
        self._queue: queue.Queue = queue.Queue()
        self._shutdown = threading.Event()
        self._worker: Optional[threading.Thread] = None
        
        # Start worker thread
        self._start_worker()
    
    def _resolve_voice(self, voice: str) -> str:
        """Resolve voice shorthand to full voice ID."""
        if voice.lower() in VOICES:
            return VOICES[voice.lower()]
        return voice
    
    def _start_worker(self):
        """Start the background TTS worker thread."""
        def worker():
            # Create event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            while not self._shutdown.is_set():
                try:
                    item = self._queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                if item is None:
                    break
                
                text, done_event = item
                try:
                    loop.run_until_complete(self._speak_async(text))
                except Exception as e:
                    print(f"[EdgeTTS] Error: {e}")
                finally:
                    if done_event:
                        done_event.set()
            
            loop.close()
        
        self._worker = threading.Thread(target=worker, name="EdgeTTSWorker", daemon=True)
        self._worker.start()
    
    async def _speak_async(self, text: str) -> None:
        """Generate and play speech asynchronously."""
        if not EDGE_TTS_AVAILABLE:
            print(f"[TTS] {text}")
            return
        
        # Generate unique filename
        import uuid
        audio_file = self.temp_dir / f"speech_{uuid.uuid4().hex[:8]}.mp3"
        
        try:
            # Generate speech
            communicate = edge_tts.Communicate(
                text, 
                self.voice,
                rate=self.rate,
                pitch=self.pitch
            )
            await communicate.save(str(audio_file))
            
            # Play audio
            if PYGAME_AVAILABLE:
                pygame.mixer.music.load(str(audio_file))
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    await asyncio.sleep(0.1)
            else:
                # Fallback to system player
                import subprocess
                import sys
                if sys.platform == "win32":
                    subprocess.run(
                        ["powershell", "-c", f"(New-Object Media.SoundPlayer '{audio_file}').PlaySync()"],
                        capture_output=True
                    )
                elif sys.platform == "darwin":
                    subprocess.run(["afplay", str(audio_file)], capture_output=True)
                else:
                    subprocess.run(["aplay", str(audio_file)], capture_output=True)
        
        finally:
            # Cleanup temp file
            try:
                if audio_file.exists():
                    audio_file.unlink()
            except Exception:
                pass
    
    def speak(self, text: str, blocking: bool = True) -> None:
        """
        Speak text using Edge TTS.
        
        Args:
            text: Text to speak
            blocking: If True, wait for speech to complete
        """
        if not text.strip():
            return
        
        done_event = threading.Event() if blocking else None
        self._queue.put((text, done_event))
        
        if blocking and done_event:
            done_event.wait(timeout=60.0)
    
    def speak_async(self, text: str) -> None:
        """Speak text without blocking."""
        self.speak(text, blocking=False)
    
    def set_voice(self, voice: str) -> None:
        """Change the voice."""
        self.voice = self._resolve_voice(voice)
    
    def set_rate(self, rate: str) -> None:
        """Change speaking rate (e.g., '+10%', '-20%')."""
        self.rate = rate
    
    @staticmethod
    def list_voices() -> dict:
        """Get available voice options."""
        return VOICES.copy()
    
    def shutdown(self):
        """Clean shutdown."""
        self._shutdown.set()
        self._queue.put(None)
        if self._worker:
            self._worker.join(timeout=2.0)


# Singleton for convenience
_edge_tts: Optional[EdgeTTS] = None


def get_edge_tts(voice: str = None) -> EdgeTTS:
    """Get or create the Edge TTS singleton."""
    global _edge_tts
    if _edge_tts is None:
        _edge_tts = EdgeTTS(voice=voice)
    return _edge_tts


def speak(text: str, blocking: bool = True) -> None:
    """Convenience function to speak using Edge TTS."""
    get_edge_tts().speak(text, blocking=blocking)
