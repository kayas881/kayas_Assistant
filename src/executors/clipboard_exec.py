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
    monitor_enabled: bool = False


class ClipboardExecutor:
    def __init__(self, cfg: ClipboardConfig | None = None):
        self.cfg = cfg or ClipboardConfig()
        self.history: List[Dict[str, Any]] = []
        self.monitor_active: bool = False
        self.last_clipboard_content: str = ""

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

    def monitor(self, pattern: str | None = None, timeout: int = 60) -> Dict[str, Any]:
        """Monitor clipboard for changes and optionally match a pattern.
        
        Args:
            pattern: Optional regex pattern to match clipboard content
            timeout: Duration to monitor in seconds (0 = indefinite)
            
        Returns:
            {
                "action": "clipboard.monitor",
                "success": bool,
                "monitor_id": str,
                "changes": [
                    {
                        "type": "text" or "image",
                        "timestamp": float,
                        "preview": str,
                        "matched": bool
                    }
                ],
                "match_found": bool
            }
        """
        import time
        import re
        
        try:
            monitor_id = f"clipboard_monitor_{time.time()}"
            changes = []
            start_time = time.time()
            match_found = False
            
            # Get initial clipboard content
            try:
                self.last_clipboard_content = pyperclip.paste()
            except:
                self.last_clipboard_content = ""
            
            # Monitor for timeout duration
            while timeout == 0 or (time.time() - start_time < timeout):
                try:
                    current_content = pyperclip.paste()
                    
                    # Check if content changed
                    if current_content != self.last_clipboard_content:
                        # Determine if it's text or image
                        is_text = isinstance(current_content, str)
                        content_type = "text" if is_text else "image"
                        
                        # Check if matches pattern
                        matched = False
                        if pattern and is_text:
                            try:
                                matched = bool(re.search(pattern, current_content))
                            except re.error:
                                matched = False
                        
                        change_event = {
                            "type": content_type,
                            "timestamp": time.time(),
                            "preview": current_content[:200] if is_text else "[image_data]",
                            "matched": matched
                        }
                        
                        changes.append(change_event)
                        self.last_clipboard_content = current_content
                        
                        # Add to history
                        self._add_to_history(content_type, current_content)
                        
                        # Stop if pattern matched
                        if pattern and matched:
                            match_found = True
                            break
                    
                    time.sleep(0.5)  # Check every 500ms
                    
                except Exception:
                    pass  # Continue monitoring on error
            
            return {
                "action": "clipboard.monitor",
                "success": True,
                "monitor_id": monitor_id,
                "changes": changes,
                "change_count": len(changes),
                "match_found": match_found,
                "elapsed": time.time() - start_time,
                "pattern": pattern
            }
            
        except Exception as e:
            return {
                "action": "clipboard.monitor",
                "success": False,
                "error": str(e)
            }
