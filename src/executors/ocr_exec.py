"""
OCR Executor - Layer D (Fallback)

Uses Tesseract OCR to find and interact with text on screen.
Works when: All other methods fail, UI is graphical/custom.

Advantages:
- Works with any visual UI
- Can find text anywhere on screen
- No API or accessibility needed

Disadvantages:
- Slower (OCR takes time)
- Less accurate
- Requires clear text rendering

Usage:
    executor = OCRExecutor()
    result = executor.find_text_on_screen("Save")
    result = executor.click_text("OK")
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional
import re

try:
    import pytesseract
    from PIL import Image, ImageGrab
    import pyautogui
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


@dataclass
class OCRConfig:
    """Configuration for OCR"""
    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Windows default
    language: str = "eng"  # OCR language
    confidence_threshold: float = 60.0  # Minimum confidence to accept
    preprocessing: bool = True  # Apply image preprocessing


class OCRExecutor:
    """
    OCR-based UI interaction using Tesseract.
    
    Process:
    1. Take screenshot
    2. Run OCR to find text
    3. Get coordinates of found text
    4. Click near the text
    """
    
    def __init__(self, config: OCRConfig = None):
        if not TESSERACT_AVAILABLE:
            raise ImportError(
                "OCR dependencies not installed. Install with:\n"
                "pip install pytesseract pillow pyautogui\n"
                "And install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki"
            )
        
        self.config = config or OCRConfig()
        
        # Set Tesseract path
        try:
            pytesseract.pytesseract.tesseract_cmd = self.config.tesseract_cmd
        except Exception:
            pass  # Will fail when actually using if not installed
    
    def capture_screen(self, region: Tuple[int, int, int, int] = None) -> Image.Image:
        """
        Capture screenshot.
        
        Args:
            region: (left, top, width, height) or None for full screen
            
        Returns:
            PIL Image
        """
        if region:
            return ImageGrab.grab(bbox=region)
        return ImageGrab.grab()
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy.
        
        Applies:
        - Grayscale conversion
        - Contrast enhancement
        - Noise reduction
        """
        from PIL import ImageEnhance, ImageFilter
        
        # Convert to grayscale
        image = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Reduce noise
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        return image
    
    def ocr_image(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Run OCR on image and get text with bounding boxes.
        
        Returns:
            [
                {
                    "text": str,
                    "confidence": float,
                    "left": int, "top": int, "width": int, "height": int
                },
                ...
            ]
        """
        if self.config.preprocessing:
            image = self.preprocess_image(image)
        
        # Get detailed OCR data
        data = pytesseract.image_to_data(
            image,
            lang=self.config.language,
            output_type=pytesseract.Output.DICT
        )
        
        results = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = float(data['conf'][i])
            
            # Filter low confidence and empty text
            if conf > self.config.confidence_threshold and text:
                results.append({
                    "text": text,
                    "confidence": conf,
                    "left": data['left'][i],
                    "top": data['top'][i],
                    "width": data['width'][i],
                    "height": data['height'][i]
                })
        
        return results
    
    def find_text_on_screen(self,
                           search_text: str,
                           region: Tuple[int, int, int, int] = None,
                           case_sensitive: bool = False) -> Dict[str, Any]:
        """
        Find text on screen using OCR.
        
        Args:
            search_text: Text to find
            region: Search region (left, top, width, height)
            case_sensitive: Whether to match case
            
        Returns:
            {
                "success": bool,
                "found": bool,
                "matches": [
                    {
                        "text": str,
                        "confidence": float,
                        "x": int,  # center x
                        "y": int,  # center y
                        "box": {...}
                    },
                    ...
                ]
            }
        """
        try:
            # Capture screen
            screenshot = self.capture_screen(region)
            
            # Run OCR
            ocr_results = self.ocr_image(screenshot)
            
            # Find matches
            matches = []
            for result in ocr_results:
                text = result["text"]
                
                # Match logic
                if not case_sensitive:
                    text_lower = text.lower()
                    search_lower = search_text.lower()
                    match = search_lower in text_lower
                else:
                    match = search_text in text
                
                if match:
                    # Calculate center point
                    center_x = result["left"] + result["width"] // 2
                    center_y = result["top"] + result["height"] // 2
                    
                    # Adjust for region offset if specified
                    if region:
                        center_x += region[0]
                        center_y += region[1]
                    
                    matches.append({
                        "text": text,
                        "confidence": result["confidence"],
                        "x": center_x,
                        "y": center_y,
                        "box": result
                    })
            
            return {
                "success": True,
                "found": len(matches) > 0,
                "count": len(matches),
                "matches": matches
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"OCR error: {str(e)}"
            }
    
    def click_text(self,
                  text: str,
                  region: Tuple[int, int, int, int] = None,
                  button: str = "left",
                  clicks: int = 1) -> Dict[str, Any]:
        """
        Find text on screen and click it.
        
        Args:
            text: Text to find and click
            region: Search region
            button: "left", "right", or "middle"
            clicks: Number of clicks (1 or 2)
            
        Returns:
            {"success": bool, "message": str}
        """
        try:
            # Find text
            find_result = self.find_text_on_screen(text, region)
            
            if not find_result["success"]:
                return find_result
            
            if not find_result["found"]:
                return {
                    "success": False,
                    "error": f"Text '{text}' not found on screen"
                }
            
            # Click the first match
            match = find_result["matches"][0]
            x, y = match["x"], match["y"]
            
            pyautogui.click(x, y, clicks=clicks, button=button)
            
            return {
                "success": True,
                "message": f"Clicked '{text}' at ({x}, {y})",
                "confidence": match["confidence"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error clicking text: {str(e)}"
            }
    
    def read_screen_text(self,
                        region: Tuple[int, int, int, int] = None) -> Dict[str, Any]:
        """
        Read all text from screen or region.
        
        Returns:
            {
                "success": bool,
                "text": str,  # All text concatenated
                "items": [...],  # Individual text items
                "full_text": str  # Paragraph mode
            }
        """
        try:
            # Capture screen
            screenshot = self.capture_screen(region)
            
            # Run OCR
            ocr_results = self.ocr_image(screenshot)
            
            # Extract text
            all_text = " ".join([r["text"] for r in ocr_results])
            
            # Also get paragraph mode for better formatting
            if self.config.preprocessing:
                screenshot = self.preprocess_image(screenshot)
            
            full_text = pytesseract.image_to_string(
                screenshot,
                lang=self.config.language
            )
            
            return {
                "success": True,
                "text": all_text,
                "items": ocr_results,
                "item_count": len(ocr_results),
                "full_text": full_text.strip()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading screen text: {str(e)}"
            }
    
    def wait_for_text(self,
                     text: str,
                     timeout: int = 10,
                     region: Tuple[int, int, int, int] = None) -> Dict[str, Any]:
        """
        Wait for text to appear on screen.
        
        Args:
            text: Text to wait for
            timeout: Maximum seconds to wait
            region: Search region
            
        Returns:
            {"success": bool, "found": bool, "elapsed": float}
        """
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.find_text_on_screen(text, region)
            
            if result["success"] and result["found"]:
                return {
                    "success": True,
                    "found": True,
                    "elapsed": time.time() - start_time,
                    "matches": result["matches"]
                }
            
            time.sleep(0.5)  # Check every 500ms
        
        return {
            "success": True,
            "found": False,
            "elapsed": time.time() - start_time,
            "error": f"Text '{text}' not found within {timeout}s"
        }
    
    def get_text_near_position(self,
                              x: int,
                              y: int,
                              radius: int = 100) -> Dict[str, Any]:
        """
        Get all text near a specific screen position.
        
        Args:
            x, y: Screen coordinates
            radius: Search radius in pixels
            
        Returns:
            {"success": bool, "texts": [...]}
        """
        # Define region around position
        region = (
            max(0, x - radius),
            max(0, y - radius),
            radius * 2,
            radius * 2
        )
        
        return self.read_screen_text(region)
    
    def find_buttons(self,
                    region: Tuple[int, int, int, int] = None) -> Dict[str, Any]:
        """
        Find common button texts on screen.
        
        Returns:
            {"success": bool, "buttons": [...]}
        """
        button_keywords = [
            "OK", "Cancel", "Yes", "No", "Apply", "Close", "Save", 
            "Open", "Delete", "Add", "Remove", "Submit", "Continue",
            "Next", "Back", "Finish", "Accept", "Reject"
        ]
        
        screenshot = self.capture_screen(region)
        ocr_results = self.ocr_image(screenshot)
        
        buttons = []
        for result in ocr_results:
            text = result["text"].strip()
            if text in button_keywords:
                center_x = result["left"] + result["width"] // 2
                center_y = result["top"] + result["height"] // 2
                
                if region:
                    center_x += region[0]
                    center_y += region[1]
                
                buttons.append({
                    "text": text,
                    "x": center_x,
                    "y": center_y,
                    "confidence": result["confidence"]
                })
        
        return {
            "success": True,
            "count": len(buttons),
            "buttons": buttons
        }
