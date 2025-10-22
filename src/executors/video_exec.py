"""
Video executor for playing and recording video.
"""
from __future__ import annotations

import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class VideoConfig:
    fps: int = 30
    codec: str = "mp4v"


class VideoExecutor:
    def __init__(self, cfg: VideoConfig | None = None):
        self.cfg = cfg or VideoConfig()

    def play_video(self, file_path: str, window_name: str = "Video") -> Dict[str, Any]:
        """Play a video file."""
        try:
            cap = cv2.VideoCapture(file_path)
            
            if not cap.isOpened():
                return {
                    "action": "video.play",
                    "success": False,
                    "error": f"Could not open video: {file_path}"
                }
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                cv2.imshow(window_name, frame)
                
                # Press 'q' to quit
                if cv2.waitKey(25) & 0xFF == ord('q'):
                    break
            
            cap.release()
            cv2.destroyAllWindows()
            
            return {
                "action": "video.play",
                "success": True,
                "file_path": file_path
            }
        except Exception as e:
            return {
                "action": "video.play",
                "success": False,
                "error": str(e)
            }

    def record_video(self, output_path: str, duration: int = 10,
                    camera_index: int = 0, fps: int | None = None) -> Dict[str, Any]:
        """Record video from camera."""
        try:
            cap = cv2.VideoCapture(camera_index)
            
            if not cap.isOpened():
                return {
                    "action": "video.record",
                    "success": False,
                    "error": f"Could not open camera {camera_index}"
                }
            
            fps = fps or self.cfg.fps
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            fourcc = cv2.VideoWriter_fourcc(*self.cfg.codec)
            out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
            
            frame_count = int(duration * fps)
            recorded = 0
            
            while recorded < frame_count:
                ret, frame = cap.read()
                if ret:
                    out.write(frame)
                    cv2.imshow('Recording...', frame)
                    recorded += 1
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                else:
                    break
            
            cap.release()
            out.release()
            cv2.destroyAllWindows()
            
            return {
                "action": "video.record",
                "success": True,
                "output_path": output_path,
                "duration": recorded / fps,
                "frames": recorded,
                "resolution": (frame_width, frame_height)
            }
        except Exception as e:
            return {
                "action": "video.record",
                "success": False,
                "error": str(e)
            }

    def get_video_info(self, file_path: str) -> Dict[str, Any]:
        """Get video file information."""
        try:
            cap = cv2.VideoCapture(file_path)
            
            if not cap.isOpened():
                return {
                    "action": "video.get_info",
                    "success": False,
                    "error": f"Could not open video: {file_path}"
                }
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            return {
                "action": "video.get_info",
                "success": True,
                "file_path": file_path,
                "fps": fps,
                "frame_count": frame_count,
                "resolution": (width, height),
                "width": width,
                "height": height,
                "duration_seconds": duration,
                "file_size_bytes": Path(file_path).stat().st_size
            }
        except Exception as e:
            return {
                "action": "video.get_info",
                "success": False,
                "error": str(e)
            }

    def extract_frames(self, file_path: str, output_dir: str,
                      frame_interval: int = 1, max_frames: int | None = None) -> Dict[str, Any]:
        """Extract frames from video."""
        try:
            cap = cv2.VideoCapture(file_path)
            
            if not cap.isOpened():
                return {
                    "action": "video.extract_frames",
                    "success": False,
                    "error": f"Could not open video: {file_path}"
                }
            
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            frame_num = 0
            saved_count = 0
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_num % frame_interval == 0:
                    frame_path = output_dir / f"frame_{frame_num:06d}.jpg"
                    cv2.imwrite(str(frame_path), frame)
                    saved_count += 1
                    
                    if max_frames and saved_count >= max_frames:
                        break
                
                frame_num += 1
            
            cap.release()
            
            return {
                "action": "video.extract_frames",
                "success": True,
                "file_path": file_path,
                "output_dir": str(output_dir),
                "frames_extracted": saved_count,
                "total_frames": frame_num
            }
        except Exception as e:
            return {
                "action": "video.extract_frames",
                "success": False,
                "error": str(e)
            }

    def create_video_from_images(self, image_paths: list[str], output_path: str,
                                fps: int | None = None) -> Dict[str, Any]:
        """Create video from image sequence."""
        try:
            if not image_paths:
                return {
                    "action": "video.create_from_images",
                    "success": False,
                    "error": "No images provided"
                }
            
            # Read first image to get dimensions
            first_frame = cv2.imread(image_paths[0])
            height, width, _ = first_frame.shape
            
            fps = fps or self.cfg.fps
            fourcc = cv2.VideoWriter_fourcc(*self.cfg.codec)
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            for img_path in image_paths:
                frame = cv2.imread(img_path)
                if frame is not None:
                    # Resize if needed
                    if frame.shape[:2] != (height, width):
                        frame = cv2.resize(frame, (width, height))
                    out.write(frame)
            
            out.release()
            
            return {
                "action": "video.create_from_images",
                "success": True,
                "output_path": output_path,
                "frame_count": len(image_paths),
                "fps": fps,
                "resolution": (width, height)
            }
        except Exception as e:
            return {
                "action": "video.create_from_images",
                "success": False,
                "error": str(e)
            }

    def resize_video(self, input_path: str, output_path: str,
                    width: int | None = None, height: int | None = None,
                    scale: float | None = None) -> Dict[str, Any]:
        """Resize video."""
        try:
            cap = cv2.VideoCapture(input_path)
            
            if not cap.isOpened():
                return {
                    "action": "video.resize",
                    "success": False,
                    "error": f"Could not open video: {input_path}"
                }
            
            original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            if scale:
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
            elif width and height:
                new_width = width
                new_height = height
            elif width:
                aspect = original_height / original_width
                new_width = width
                new_height = int(width * aspect)
            elif height:
                aspect = original_width / original_height
                new_height = height
                new_width = int(height * aspect)
            else:
                cap.release()
                return {
                    "action": "video.resize",
                    "success": False,
                    "error": "Must provide width, height, or scale"
                }
            
            fourcc = cv2.VideoWriter_fourcc(*self.cfg.codec)
            out = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height))
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                resized = cv2.resize(frame, (new_width, new_height))
                out.write(resized)
            
            cap.release()
            out.release()
            
            return {
                "action": "video.resize",
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "original_resolution": (original_width, original_height),
                "new_resolution": (new_width, new_height)
            }
        except Exception as e:
            return {
                "action": "video.resize",
                "success": False,
                "error": str(e)
            }

    def trim_video(self, input_path: str, output_path: str,
                  start_frame: int = 0, end_frame: int | None = None) -> Dict[str, Any]:
        """Trim video to specific frame range."""
        try:
            cap = cv2.VideoCapture(input_path)
            
            if not cap.isOpened():
                return {
                    "action": "video.trim",
                    "success": False,
                    "error": f"Could not open video: {input_path}"
                }
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            end_frame = end_frame or total_frames
            
            fourcc = cv2.VideoWriter_fourcc(*self.cfg.codec)
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            frame_num = 0
            written = 0
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                if start_frame <= frame_num < end_frame:
                    out.write(frame)
                    written += 1
                
                frame_num += 1
                
                if frame_num >= end_frame:
                    break
            
            cap.release()
            out.release()
            
            return {
                "action": "video.trim",
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "frames_written": written
            }
        except Exception as e:
            return {
                "action": "video.trim",
                "success": False,
                "error": str(e)
            }
