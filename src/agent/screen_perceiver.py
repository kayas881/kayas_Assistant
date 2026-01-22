"""
Screen Perceiver - Vision-based understanding of the current screen state.

This enables the cognitive agent to "see" what's happening on screen,
which is essential for context-aware responses and the universal interface.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

try:
    import pyautogui
    import pygetwindow as gw
    DESKTOP_AVAILABLE = True
except ImportError:
    DESKTOP_AVAILABLE = False

try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


@dataclass
class ScreenState:
    """Current state of the screen."""
    active_window: str = ""
    active_window_title: str = ""
    visible_windows: List[str] = None
    screen_width: int = 0
    screen_height: int = 0
    screenshot_path: Optional[str] = None
    vision_description: str = ""
    timestamp: str = ""
    
    def __post_init__(self):
        if self.visible_windows is None:
            self.visible_windows = []
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class ScreenPerceiver:
    """
    Understands the current screen state.
    
    Combines:
    - Window API queries (fast, reliable for window info)
    - Screenshots (for vision model description)
    - Optional vision model integration
    """
    
    def __init__(self, vision_model=None, screenshot_dir: Path = None):
        """
        Initialize screen perceiver.
        
        Args:
            vision_model: Optional VL model for screen understanding
            screenshot_dir: Where to save screenshots (default: artifacts)
        """
        self.vision_model = vision_model
        self.screenshot_dir = screenshot_dir or Path("artifacts/screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        self._last_state: Optional[ScreenState] = None
        self._last_screenshot_time: float = 0
        self._screenshot_cooldown: float = 1.0  # Don't screenshot more than once per second
    
    def get_current_state(self, include_screenshot: bool = False) -> Dict[str, Any]:
        """
        Get the current screen state.
        
        Args:
            include_screenshot: Whether to capture and analyze screenshot
            
        Returns:
            Dict with screen state information
        """
        state = ScreenState()
        
        if DESKTOP_AVAILABLE:
            try:
                # Get active window
                active = gw.getActiveWindow()
                if active:
                    state.active_window = self._get_app_name(active.title)
                    state.active_window_title = active.title
                
                # Get all visible windows
                all_windows = gw.getAllTitles()
                state.visible_windows = [
                    self._get_app_name(w) 
                    for w in all_windows 
                    if w and w.strip()
                ]
                # Deduplicate
                state.visible_windows = list(set(state.visible_windows))
                
                # Screen dimensions
                state.screen_width, state.screen_height = pyautogui.size()
                
            except Exception as e:
                pass
        
        # Optionally capture screenshot
        if include_screenshot and PIL_AVAILABLE and DESKTOP_AVAILABLE:
            state.screenshot_path = self._capture_screenshot()
            
            # If we have a vision model, describe the screen
            if self.vision_model and state.screenshot_path:
                state.vision_description = self._describe_screen(state.screenshot_path)
        
        self._last_state = state
        
        return {
            "active_window": state.active_window,
            "active_window_title": state.active_window_title,
            "visible_apps": state.visible_windows,
            "description": state.vision_description,
            "screenshot_path": state.screenshot_path,
            "screen_size": (state.screen_width, state.screen_height),
        }
    
    def _get_app_name(self, window_title: str) -> str:
        """Extract app name from window title."""
        if not window_title:
            return ""
        
        # Common patterns: "Document - App Name" or "App Name - Document"
        # Try to extract the app name
        
        # Known app patterns
        known_apps = {
            "Chrome": ["Google Chrome", "Chrome"],
            "VS Code": ["Visual Studio Code", "VS Code", "Code"],
            "Firefox": ["Mozilla Firefox", "Firefox"],
            "Edge": ["Microsoft Edge", "Edge"],
            "Notepad": ["Notepad"],
            "Explorer": ["File Explorer", "Explorer"],
            "Terminal": ["Windows Terminal", "Terminal", "Command Prompt", "PowerShell"],
            "Spotify": ["Spotify"],
            "Discord": ["Discord"],
            "Slack": ["Slack"],
            "WhatsApp": ["WhatsApp"],
            "Teams": ["Microsoft Teams", "Teams"],
            "Outlook": ["Outlook"],
            "Word": ["Microsoft Word", "Word"],
            "Excel": ["Microsoft Excel", "Excel"],
            "YouTube": ["YouTube"],
        }
        
        title_lower = window_title.lower()
        for app, patterns in known_apps.items():
            for pattern in patterns:
                if pattern.lower() in title_lower:
                    return app
        
        # If no known app, return the title truncated
        if " - " in window_title:
            # Usually "Document - App" format
            parts = window_title.split(" - ")
            return parts[-1].strip()[:30]
        
        return window_title[:30]
    
    def _capture_screenshot(self) -> Optional[str]:
        """Capture a screenshot if cooldown allows."""
        now = time.time()
        if now - self._last_screenshot_time < self._screenshot_cooldown:
            # Return last screenshot if within cooldown
            if self._last_state and self._last_state.screenshot_path:
                return self._last_state.screenshot_path
            return None
        
        self._last_screenshot_time = now
        
        try:
            screenshot = pyautogui.screenshot()
            
            # Resize for efficiency (vision models don't need full resolution)
            max_size = 1280
            if screenshot.width > max_size or screenshot.height > max_size:
                ratio = min(max_size / screenshot.width, max_size / screenshot.height)
                new_size = (int(screenshot.width * ratio), int(screenshot.height * ratio))
                screenshot = screenshot.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save
            filename = f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = self.screenshot_dir / filename
            screenshot.save(filepath)
            
            return str(filepath)
            
        except Exception as e:
            return None
    
    def _describe_screen(self, screenshot_path: str) -> str:
        """Use vision model to describe what's on screen."""
        if not self.vision_model:
            return ""
        
        try:
            # This would integrate with your VL vision executor
            result = self.vision_model.describe_image(
                screenshot_path,
                prompt="Briefly describe what's happening on this computer screen. "
                       "Focus on: active application, what the user seems to be doing, "
                       "any notable UI elements or content."
            )
            return result.get("description", "")
        except Exception:
            return ""
    
    def get_quick_context(self) -> str:
        """Get a quick one-line context for prompts."""
        state = self.get_current_state(include_screenshot=False)
        
        parts = []
        if state["active_window"]:
            parts.append(f"Currently in: {state['active_window']}")
        if state["active_window_title"] and state["active_window_title"] != state["active_window"]:
            # Add more context if title is informative
            title = state["active_window_title"]
            if len(title) > 50:
                title = title[:50] + "..."
            parts.append(f"({title})")
        
        return " ".join(parts) if parts else "Desktop"
    
    def has_window_open(self, app_name: str) -> bool:
        """Check if an app is currently open."""
        state = self.get_current_state(include_screenshot=False)
        app_lower = app_name.lower()
        
        for window in state.get("visible_apps", []):
            if app_lower in window.lower():
                return True
        return False
    
    def is_app_focused(self, app_name: str) -> bool:
        """Check if an app is currently focused."""
        state = self.get_current_state(include_screenshot=False)
        active = state.get("active_window", "").lower()
        return app_name.lower() in active
