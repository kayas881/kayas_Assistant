"""
Vision-Language executor using remote Qwen3-VL model via vLLM.

This executor can:
- Analyze screenshots to understand what's on screen
- Find specific elements/files in a UI
- Answer questions about images
- Guide multi-step visual tasks
"""
from __future__ import annotations

import base64
import httpx
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import mss
import mss.tools


@dataclass  
class VLVisionConfig:
    """Configuration for VL Vision executor."""
    base_url: str = ""  # vLLM server URL (e.g., ngrok URL)
    model: str = "QuantTrio/Qwen3-VL-32B-Instruct-AWQ"
    temperature: float = 0.3
    max_tokens: int = 512  # Reduced for faster response
    timeout: float = 300.0  # 5 minutes - VL model is slow on Kaggle T4s


class VLVisionExecutor:
    """
    Vision-Language executor using Qwen3-VL for understanding images and screens.
    
    This is much more capable than OCR - it can understand context, find elements,
    and describe what it sees in natural language.
    """
    
    def __init__(self, config: VLVisionConfig = None):
        self.config = config or VLVisionConfig()
        self._client = httpx.Client(timeout=self.config.timeout)
        self._sct = mss.mss()
        
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 data URL."""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Determine mime type
        suffix = path.suffix.lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
        }
        mime = mime_types.get(suffix, 'image/png')
        
        with open(path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('utf-8')
        
        return f"data:{mime};base64,{data}"
    
    def _call_vl_model(self, prompt: str, image_data_url: str, system: str = None) -> str:
        """Call the VL model with an image."""
        if not self.config.base_url:
            raise ValueError("VL Vision requires base_url to be configured")
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        
        # OpenAI-compatible multimodal message format
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data_url}}
            ]
        })
        
        try:
            resp = self._client.post(
                f"{self.config.base_url}/v1/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": messages,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                },
                headers={"ngrok-skip-browser-warning": "true"}
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"VL model error: {e}")
    
    def take_screenshot(self, save_path: str = None) -> str:
        """Take a screenshot and return the path."""
        if save_path is None:
            save_path = str(Path.cwd() / ".agent" / f"screenshot_{int(time.time())}.png")
        
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Capture primary monitor
        monitor = self._sct.monitors[1]  # Primary monitor
        screenshot = self._sct.grab(monitor)
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=save_path)
        
        return save_path
    
    # ==================== High-Level Actions ====================
    
    def analyze_screen(self, question: str = None) -> Dict[str, Any]:
        """
        Take a screenshot and analyze what's on screen.
        
        Args:
            question: Optional specific question about the screen
        
        Returns:
            Analysis result with description and any requested info
        """
        try:
            screenshot_path = self.take_screenshot()
            image_url = self._encode_image(screenshot_path)
            
            prompt = question or "Describe what you see on this screen. Include any important UI elements, windows, text, and what the user appears to be doing."
            
            system = """You are a visual assistant analyzing a computer screenshot. 
Be specific about what you see - mention window titles, button labels, file names, etc.
If asked to find something specific, describe its exact location (top-left, center, etc.)."""
            
            analysis = self._call_vl_model(prompt, image_url, system)
            
            return {
                "action": "vl_vision.analyze_screen",
                "success": True,
                "screenshot_path": screenshot_path,
                "question": question,
                "analysis": analysis
            }
        except Exception as e:
            return {
                "action": "vl_vision.analyze_screen",
                "success": False,
                "error": str(e)
            }
    
    def find_on_screen(self, target: str) -> Dict[str, Any]:
        """
        Find a specific element/file/text on the current screen.
        
        Args:
            target: What to find (e.g., "cat video", "Chrome icon", "submit button")
        
        Returns:
            Location and details of the found element
        """
        try:
            screenshot_path = self.take_screenshot()
            image_url = self._encode_image(screenshot_path)
            
            prompt = f"""Find "{target}" on this screen.

If found, describe:
1. EXACTLY what you found (filename, icon label, button text, etc.)
2. Its LOCATION on screen (e.g., "top-left corner", "in the file list, 3rd item", "center of screen")
3. Any other relevant details

If NOT found, say "NOT FOUND" and suggest where it might be or what the user should do."""
            
            system = "You are a visual assistant helping locate elements on a computer screen. Be precise about locations."
            
            result = self._call_vl_model(prompt, image_url, system)
            
            found = "NOT FOUND" not in result.upper()
            
            return {
                "action": "vl_vision.find_on_screen",
                "success": True,
                "found": found,
                "target": target,
                "screenshot_path": screenshot_path,
                "result": result
            }
        except Exception as e:
            return {
                "action": "vl_vision.find_on_screen",
                "success": False,
                "error": str(e)
            }
    
    def analyze_image(self, image_path: str, question: str = None) -> Dict[str, Any]:
        """
        Analyze an image file.
        
        Args:
            image_path: Path to the image
            question: Optional question about the image
        
        Returns:
            Analysis of the image
        """
        try:
            image_url = self._encode_image(image_path)
            
            prompt = question or "Describe this image in detail. What do you see?"
            
            analysis = self._call_vl_model(prompt, image_url)
            
            return {
                "action": "vl_vision.analyze_image",
                "success": True,
                "image_path": image_path,
                "question": question,
                "analysis": analysis
            }
        except Exception as e:
            return {
                "action": "vl_vision.analyze_image",
                "success": False,
                "error": str(e)
            }
    
    def list_files_on_screen(self) -> Dict[str, Any]:
        """
        Look at the screen and list all visible files/folders.
        
        Useful for file managers, download folders, etc.
        """
        try:
            screenshot_path = self.take_screenshot()
            image_url = self._encode_image(screenshot_path)
            
            prompt = """List all visible files and folders on this screen.

Format as a numbered list:
1. [type] filename - description (if visible)

Where [type] is one of: [FILE], [FOLDER], [VIDEO], [IMAGE], [DOCUMENT], [OTHER]

Focus on the main content area. Include file extensions if visible."""
            
            system = "You are a file system assistant. List files you can see on screen accurately."
            
            result = self._call_vl_model(prompt, image_url, system)
            
            return {
                "action": "vl_vision.list_files_on_screen",
                "success": True,
                "screenshot_path": screenshot_path,
                "files": result
            }
        except Exception as e:
            return {
                "action": "vl_vision.list_files_on_screen",
                "success": False,
                "error": str(e)
            }
    
    def guide_click(self, target: str) -> Dict[str, Any]:
        """
        Find where to click for a specific action.
        
        Args:
            target: What to click (e.g., "send button", "cat_video.mp4")
        
        Returns:
            Instructions on where to click
        """
        try:
            screenshot_path = self.take_screenshot()
            image_url = self._encode_image(screenshot_path)
            
            prompt = f"""I need to click on "{target}".

Looking at this screen, tell me:
1. Can you see "{target}" or something similar?
2. If yes, describe its EXACT position (e.g., "bottom-right corner", "in the toolbar at top", "3rd item in the list")
3. What does it look like? (button color, icon, text label)
4. Any other clickable elements nearby I should be aware of?

If you can't find it, suggest what I should do first (scroll, open a menu, etc.)."""
            
            result = self._call_vl_model(prompt, image_url)
            
            return {
                "action": "vl_vision.guide_click",
                "success": True,
                "target": target,
                "screenshot_path": screenshot_path,
                "guidance": result
            }
        except Exception as e:
            return {
                "action": "vl_vision.guide_click",
                "success": False,
                "error": str(e)
            }
    
    def read_error_message(self) -> Dict[str, Any]:
        """
        Look for and read any error messages or dialogs on screen.
        """
        try:
            screenshot_path = self.take_screenshot()
            image_url = self._encode_image(screenshot_path)
            
            prompt = """Look at this screen for any:
- Error messages
- Warning dialogs
- Pop-up notifications
- Alert boxes
- Toast messages

If you find any, transcribe the EXACT text and describe what type of message it is.
If there are no error/warning messages, say "No error messages visible"."""
            
            result = self._call_vl_model(prompt, image_url)
            
            has_error = "no error" not in result.lower()
            
            return {
                "action": "vl_vision.read_error_message",
                "success": True,
                "has_error": has_error,
                "screenshot_path": screenshot_path,
                "result": result
            }
        except Exception as e:
            return {
                "action": "vl_vision.read_error_message",
                "success": False,
                "error": str(e)
            }


# Singleton for easy access
_vl_vision: Optional[VLVisionExecutor] = None

def get_vl_vision(base_url: str = None) -> VLVisionExecutor:
    """Get or create VL Vision executor."""
    global _vl_vision
    if _vl_vision is None or (base_url and _vl_vision.config.base_url != base_url):
        config = VLVisionConfig(base_url=base_url) if base_url else VLVisionConfig()
        _vl_vision = VLVisionExecutor(config)
    return _vl_vision
