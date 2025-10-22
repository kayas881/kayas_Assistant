"""
Clipboard executor for advanced clipboard operations.
"""
from __future__ import annotations

import pyperclip
import io
from PIL import Image, ImageGrab
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass
import base64


@dataclass
class ClipboardConfig:
    history_size: int = 50
    auto_save: bool = True


class ClipboardExecutor:
    def __init__(self, cfg: ClipboardConfig | None = None):
        self.cfg = cfg or ClipboardConfig()
        self.history: List[Dict[str, Any]] = []

    def copy_text(self, text: str, add_to_history: bool = True) -> Dict[str, Any]:
        """Copy text to clipboard."""
        try:
            pyperclip.copy(text)
            
            if add_to_history and self.cfg.auto_save:
                self._add_to_history("text", text)
            
            return {
                "action": "clipboard.copy_text",
                "success": True,
                "text": text[:100] + "..." if len(text) > 100 else text
            }
        except Exception as e:
            return {
                "action": "clipboard.copy_text",
                "success": False,
                "error": str(e)
            }

    def paste_text(self) -> Dict[str, Any]:
        """Get text from clipboard."""
        try:
            text = pyperclip.paste()
            
            return {
                "action": "clipboard.paste_text",
                "success": True,
                "text": text
            }
        except Exception as e:
            return {
                "action": "clipboard.paste_text",
                "success": False,
                "error": str(e)
            }

    def copy_image(self, image_path: str | None = None, add_to_history: bool = True) -> Dict[str, Any]:
        """Copy image to clipboard from file or take screenshot."""
        try:
            if image_path:
                img = Image.open(image_path)
            else:
                # Screenshot
                img = ImageGrab.grab()
            
            # Copy to clipboard (Windows-specific)
            output = io.BytesIO()
            img.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]  # Remove BMP header
            output.close()
            
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
            
            if add_to_history and self.cfg.auto_save:
                self._add_to_history("image", str(image_path) if image_path else "screenshot")
            
            return {
                "action": "clipboard.copy_image",
                "success": True,
                "source": image_path or "screenshot",
                "size": img.size
            }
        except Exception as e:
            return {
                "action": "clipboard.copy_image",
                "success": False,
                "error": str(e)
            }

    def paste_image(self, save_path: str | None = None) -> Dict[str, Any]:
        """Get image from clipboard and optionally save it."""
        try:
            img = ImageGrab.grabclipboard()
            
            if img is None:
                return {
                    "action": "clipboard.paste_image",
                    "success": False,
                    "error": "No image in clipboard"
                }
            
            result = {
                "action": "clipboard.paste_image",
                "success": True,
                "size": img.size
            }
            
            if save_path:
                img.save(save_path)
                result["saved_to"] = save_path
            
            return result
        except Exception as e:
            return {
                "action": "clipboard.paste_image",
                "success": False,
                "error": str(e)
            }

    def get_history(self, limit: int | None = None) -> Dict[str, Any]:
        """Get clipboard history."""
        try:
            history = self.history[-(limit or self.cfg.history_size):]
            
            return {
                "action": "clipboard.history",
                "success": True,
                "count": len(history),
                "history": history
            }
        except Exception as e:
            return {
                "action": "clipboard.history",
                "success": False,
                "error": str(e)
            }

    def clear_history(self) -> Dict[str, Any]:
        """Clear clipboard history."""
        try:
            self.history.clear()
            
            return {
                "action": "clipboard.clear_history",
                "success": True
            }
        except Exception as e:
            return {
                "action": "clipboard.clear_history",
                "success": False,
                "error": str(e)
            }

    def _add_to_history(self, content_type: str, content: Any) -> None:
        """Add item to history."""
        import time
        
        entry = {
            "type": content_type,
            "timestamp": time.time(),
            "preview": str(content)[:200] if content_type == "text" else content
        }
        
        self.history.append(entry)
        
        # Keep history size in check
        if len(self.history) > self.cfg.history_size:
            self.history = self.history[-self.cfg.history_size:]
