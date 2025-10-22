"""
Audio executor for recording, playing, and converting audio.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import wave
import threading


@dataclass
class AudioConfig:
    sample_rate: int = 44100
    channels: int = 2
    chunk_size: int = 1024


class AudioExecutor:
    def __init__(self, cfg: AudioConfig | None = None):
        self.cfg = cfg or AudioConfig()
        self.recording = False
        self.recording_thread = None

    def play_audio(self, file_path: str, blocking: bool = True) -> Dict[str, Any]:
        """Play an audio file."""
        try:
            import pyaudio
            
            wf = wave.open(file_path, 'rb')
            
            p = pyaudio.PyAudio()
            stream = p.open(
                format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )
            
            def play():
                data = wf.readframes(self.cfg.chunk_size)
                while data:
                    stream.write(data)
                    data = wf.readframes(self.cfg.chunk_size)
                
                stream.stop_stream()
                stream.close()
                p.terminate()
                wf.close()
            
            if blocking:
                play()
            else:
                thread = threading.Thread(target=play, daemon=True)
                thread.start()
            
            return {
                "action": "audio.play",
                "success": True,
                "file_path": file_path,
                "blocking": blocking
            }
        except Exception as e:
            return {
                "action": "audio.play",
                "success": False,
                "error": str(e)
            }

    def record_audio(self, output_path: str, duration: int = 5) -> Dict[str, Any]:
        """Record audio for a specified duration."""
        try:
            import pyaudio
            
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=self.cfg.channels,
                rate=self.cfg.sample_rate,
                input=True,
                frames_per_buffer=self.cfg.chunk_size
            )
            
            frames = []
            num_chunks = int(self.cfg.sample_rate / self.cfg.chunk_size * duration)
            
            for _ in range(num_chunks):
                data = stream.read(self.cfg.chunk_size)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # Save to file
            wf = wave.open(output_path, 'wb')
            wf.setnchannels(self.cfg.channels)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.cfg.sample_rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            return {
                "action": "audio.record",
                "success": True,
                "output_path": output_path,
                "duration": duration,
                "sample_rate": self.cfg.sample_rate
            }
        except Exception as e:
            return {
                "action": "audio.record",
                "success": False,
                "error": str(e)
            }

    def convert_audio(self, input_path: str, output_path: str,
                     output_format: str = "mp3", bitrate: str = "192k") -> Dict[str, Any]:
        """Convert audio format (requires pydub)."""
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format=output_format, bitrate=bitrate)
            
            return {
                "action": "audio.convert",
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "format": output_format,
                "bitrate": bitrate
            }
        except Exception as e:
            return {
                "action": "audio.convert",
                "success": False,
                "error": str(e)
            }

    def get_audio_info(self, file_path: str) -> Dict[str, Any]:
        """Get audio file information."""
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(file_path)
            
            return {
                "action": "audio.get_info",
                "success": True,
                "file_path": file_path,
                "duration_seconds": len(audio) / 1000,
                "channels": audio.channels,
                "sample_rate": audio.frame_rate,
                "sample_width": audio.sample_width,
                "frame_count": audio.frame_count(),
                "file_size_bytes": Path(file_path).stat().st_size
            }
        except Exception as e:
            return {
                "action": "audio.get_info",
                "success": False,
                "error": str(e)
            }

    def trim_audio(self, input_path: str, output_path: str,
                  start_ms: int = 0, end_ms: int | None = None) -> Dict[str, Any]:
        """Trim audio file."""
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(input_path)
            trimmed = audio[start_ms:end_ms] if end_ms else audio[start_ms:]
            trimmed.export(output_path)
            
            return {
                "action": "audio.trim",
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "start_ms": start_ms,
                "end_ms": end_ms or len(audio),
                "new_duration_seconds": len(trimmed) / 1000
            }
        except Exception as e:
            return {
                "action": "audio.trim",
                "success": False,
                "error": str(e)
            }

    def change_volume(self, input_path: str, output_path: str,
                     change_db: float = 0) -> Dict[str, Any]:
        """Change audio volume."""
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(input_path)
            adjusted = audio + change_db
            adjusted.export(output_path)
            
            return {
                "action": "audio.change_volume",
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "change_db": change_db
            }
        except Exception as e:
            return {
                "action": "audio.change_volume",
                "success": False,
                "error": str(e)
            }

    def merge_audio(self, input_paths: list[str], output_path: str,
                   crossfade_ms: int = 0) -> Dict[str, Any]:
        """Merge multiple audio files."""
        try:
            from pydub import AudioSegment
            
            if not input_paths:
                return {
                    "action": "audio.merge",
                    "success": False,
                    "error": "No input files provided"
                }
            
            combined = AudioSegment.from_file(input_paths[0])
            
            for path in input_paths[1:]:
                audio = AudioSegment.from_file(path)
                if crossfade_ms > 0:
                    combined = combined.append(audio, crossfade=crossfade_ms)
                else:
                    combined = combined + audio
            
            combined.export(output_path)
            
            return {
                "action": "audio.merge",
                "success": True,
                "input_count": len(input_paths),
                "output_path": output_path,
                "duration_seconds": len(combined) / 1000
            }
        except Exception as e:
            return {
                "action": "audio.merge",
                "success": False,
                "error": str(e)
            }

    def extract_audio_from_video(self, video_path: str, output_path: str,
                                format: str = "mp3") -> Dict[str, Any]:
        """Extract audio from video file."""
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(video_path)
            audio.export(output_path, format=format)
            
            return {
                "action": "audio.extract_from_video",
                "success": True,
                "video_path": video_path,
                "output_path": output_path,
                "format": format
            }
        except Exception as e:
            return {
                "action": "audio.extract_from_video",
                "success": False,
                "error": str(e)
            }
