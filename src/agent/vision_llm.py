"""
Vision LLM - Client for Qwen3-VL model for screen understanding.

This enables JARVIS to "see" the screen by sending screenshots
to the vision model and getting descriptions of what's happening.
"""
from __future__ import annotations

import base64
import requests
from pathlib import Path
from typing import Optional, Dict, Any


class VisionLLM:
    """
    Client for Qwen2.5-VL vision model hosted on vLLM.
    
    Sends screenshots to the model and gets descriptions
    of what the user is doing on screen.
    """
    
    def __init__(
        self,
        base_url: str = "https://overlavish-elenora-fellowly.ngrok-free.dev",
        model: str = "Qwen/Qwen2.5-VL-7B-Instruct-AWQ",  # 7B for faster responses
        timeout: int = 60,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.endpoint = f"{self.base_url}/v1/chat/completions"
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def _get_image_mime(self, image_path: str) -> str:
        """Get MIME type for image."""
        ext = Path(image_path).suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return mime_map.get(ext, "image/png")
    
    def describe_screen(
        self,
        image_path: str,
        prompt: str = None,
        max_tokens: int = 300,
    ) -> Dict[str, Any]:
        """
        Send screenshot to vision model and get description.
        
        Args:
            image_path: Path to screenshot
            prompt: Custom prompt (default: describe what user is doing)
            max_tokens: Max response length
            
        Returns:
            Dict with 'description' and 'success' keys
        """
        if not Path(image_path).exists():
            return {"success": False, "description": "", "error": "Image not found"}
        
        if prompt is None:
            prompt = """Look at this computer screenshot and describe:
1. What application is the user in?
2. What specific content are they looking at (document, webpage, code, etc.)?
3. What seems to be their current task or goal?

Be concise but specific. Focus on actionable context."""
        
        try:
            # Encode image
            image_b64 = self._encode_image(image_path)
            mime_type = self._get_image_mime(image_path)
            
            # Build message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
            
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }
            
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Strip thinking tags if present
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()
            
            return {
                "success": True,
                "description": content,
            }
            
        except requests.exceptions.Timeout:
            return {"success": False, "description": "", "error": "Vision model timeout"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "description": "", "error": str(e)}
        except Exception as e:
            return {"success": False, "description": "", "error": str(e)}
    
    def analyze_activity(self, image_path: str) -> str:
        """
        Analyze user activity from screenshot for JARVIS context.
        
        Returns a concise summary suitable for the Analyst prompt.
        """
        result = self.describe_screen(
            image_path,
            prompt="""Analyze this screenshot briefly:
- What app/website is open?
- What is the user reading/writing/doing?
- Any notable details (document name, code file, video title, etc.)?

One paragraph, be specific about content visible.""",
            max_tokens=200,
        )
        
        if result["success"]:
            return result["description"]
        return ""


# Test function
def test_vision():
    """Test the vision model connection."""
    import pyautogui
    from datetime import datetime
    
    # Capture test screenshot
    screenshot = pyautogui.screenshot()
    test_path = f"test_screen_{datetime.now().strftime('%H%M%S')}.png"
    screenshot.save(test_path)
    
    # Test vision
    vision = VisionLLM()
    result = vision.describe_screen(test_path)
    
    print(f"Success: {result['success']}")
    print(f"Description: {result.get('description', '')[:200]}")
    
    # Cleanup
    Path(test_path).unlink(missing_ok=True)
    
    return result


if __name__ == "__main__":
    test_vision()
