"""Debugging utilities for executors"""

import os
from datetime import datetime
from pathlib import Path

def ensure_debug_dir():
    """Create debug_screens directory if it doesn't exist"""
    debug_dir = Path("debug_screens")
    debug_dir.mkdir(exist_ok=True)
    return debug_dir

def save_debug_screenshot(name: str, image) -> str:
    """
    Save a screenshot for debugging.
    
    Args:
        name: Filename (e.g., "ocr_try.png")
        image: PIL Image or numpy array
        
    Returns:
        Path to saved file
    """
    debug_dir = ensure_debug_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{name}"
    filepath = debug_dir / filename
    
    if image is None:
        return str(filepath)
    
    # Handle PIL Image
    if hasattr(image, 'save'):
        image.save(filepath)
    # Handle numpy array
    elif hasattr(image, 'shape'):
        try:
            from PIL import Image
            pil_image = Image.fromarray(image)
            pil_image.save(filepath)
        except Exception as e:
            print(f"[DebugUtils] Failed to save array image: {e}")
            return str(filepath)
    
    return str(filepath)

def annotate_screenshot_with_box(image, bbox: tuple, label: str = "Found"):
    """
    Annotate a screenshot with a bounding box and label.
    
    Args:
        image: PIL Image
        bbox: (x1, y1, x2, y2) or (x, y, width, height)
        label: Text label for the box
        
    Returns:
        Annotated PIL Image
    """
    try:
        from PIL import ImageDraw, ImageFont
        
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # Draw rectangle
        draw.rectangle(bbox, outline="red", width=2)
        
        # Draw label
        if len(bbox) == 4:
            x, y = bbox[0], bbox[1]
        else:
            x, y = bbox[0], bbox[1]
        
        try:
            draw.text((x + 5, y - 15), label, fill="red")
        except Exception:
            # If fonts fail, just skip label
            pass
        
        return img_copy
    except Exception as e:
        print(f"[DebugUtils] Failed to annotate: {e}")
        return image
