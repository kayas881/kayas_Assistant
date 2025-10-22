"""
Computer Vision Executor - Layer C (Image/Template Matching)

Uses OpenCV and pyautogui for visual UI interaction through image recognition.
Works with: Any application, games, custom UIs, non-standard controls.

Advantages:
- Works with any visual interface
- No accessibility API required
- Can find buttons/elements by appearance
- Good for games and custom UIs

Usage:
    executor = CVExecutor()
    result = executor.find_image_on_screen("button.png")
    result = executor.click_image("save_button.png")
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
import time
from pathlib import Path

try:
    import cv2
    import numpy as np
    import pyautogui
    from PIL import ImageGrab
    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False


@dataclass
class CVConfig:
    """Configuration for Computer Vision executor."""
    confidence: float = 0.8  # Match confidence threshold (0.0 to 1.0)
    grayscale: bool = True  # Convert to grayscale for faster matching
    region: Optional[Tuple[int, int, int, int]] = None  # (x, y, width, height)
    multi_match: bool = False  # Find all matches vs first match
    scale_range: Tuple[float, float] = (0.8, 1.2)  # Scale invariance range
    cache_templates: bool = True  # Cache loaded template images


class CVExecutor:
    """Computer Vision executor using OpenCV for image-based UI interaction."""
    
    def __init__(self, config: CVConfig = None):
        if not CV_AVAILABLE:
            raise ImportError("opencv-python, numpy, and pyautogui required for CVExecutor")
        
        self.config = config or CVConfig()
        self._template_cache = {} if self.config.cache_templates else None
    
    def _load_template(self, template_path: str) -> np.ndarray:
        """Load and cache template image."""
        if self._template_cache is not None and template_path in self._template_cache:
            return self._template_cache[template_path]
        
        template = cv2.imread(template_path)
        if template is None:
            raise FileNotFoundError(f"Template image not found: {template_path}")
        
        if self.config.grayscale:
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        if self._template_cache is not None:
            self._template_cache[template_path] = template
        
        return template
    
    def _capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """Capture screen or region as OpenCV image."""
        region = region or self.config.region
        
        if region:
            screenshot = ImageGrab.grab(bbox=region)
        else:
            screenshot = ImageGrab.grab()
        
        # Convert PIL to OpenCV format
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        if self.config.grayscale:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        return img
    
    def find_image_on_screen(
        self,
        template_path: str,
        confidence: Optional[float] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        multi_match: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Find template image on screen using template matching.
        
        Args:
            template_path: Path to template image file
            confidence: Match confidence (0.0-1.0), defaults to config
            region: Search region (x, y, width, height)
            multi_match: Find all matches vs first match
        
        Returns:
            {
                "found": bool,
                "matches": [{"x": int, "y": int, "confidence": float}],
                "best_match": {"x": int, "y": int, "confidence": float},
                "match_count": int
            }
        """
        try:
            confidence = confidence if confidence is not None else self.config.confidence
            multi_match = multi_match if multi_match is not None else self.config.multi_match
            
            # Load template
            template = self._load_template(template_path)
            template_h, template_w = template.shape[:2]
            
            # Capture screen
            screen = self._capture_screen(region)
            
            # Perform template matching
            result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
            
            matches = []
            
            if multi_match:
                # Find all matches above threshold
                locations = np.where(result >= confidence)
                for pt in zip(*locations[::-1]):
                    matches.append({
                        "x": int(pt[0] + template_w / 2),
                        "y": int(pt[1] + template_h / 2),
                        "confidence": float(result[pt[1], pt[0]])
                    })
            else:
                # Find best match
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                if max_val >= confidence:
                    matches.append({
                        "x": int(max_loc[0] + template_w / 2),
                        "y": int(max_loc[1] + template_h / 2),
                        "confidence": float(max_val)
                    })
            
            # Adjust coordinates if region was specified
            if region:
                for match in matches:
                    match["x"] += region[0]
                    match["y"] += region[1]
            
            return {
                "success": True,
                "found": len(matches) > 0,
                "matches": matches,
                "best_match": matches[0] if matches else None,
                "match_count": len(matches),
                "template": template_path,
                "confidence_threshold": confidence
            }
            
        except Exception as e:
            return {
                "success": False,
                "found": False,
                "error": f"Image search failed: {str(e)}"
            }
    
    def click_image(
        self,
        template_path: str,
        confidence: Optional[float] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.1
    ) -> Dict[str, Any]:
        """
        Find and click on template image.
        
        Args:
            template_path: Path to template image
            confidence: Match confidence threshold
            region: Search region
            button: Mouse button ('left', 'right', 'middle')
            clicks: Number of clicks
            interval: Interval between clicks
        
        Returns:
            {
                "success": bool,
                "clicked": bool,
                "location": {"x": int, "y": int},
                "confidence": float
            }
        """
        try:
            # Find image
            result = self.find_image_on_screen(template_path, confidence, region, multi_match=False)
            
            if not result["found"]:
                return {
                    "success": False,
                    "clicked": False,
                    "error": "Template not found on screen"
                }
            
            # Click on best match
            match = result["best_match"]
            pyautogui.click(
                match["x"],
                match["y"],
                clicks=clicks,
                interval=interval,
                button=button
            )
            
            return {
                "success": True,
                "clicked": True,
                "location": {"x": match["x"], "y": match["y"]},
                "confidence": match["confidence"],
                "template": template_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "clicked": False,
                "error": f"Click failed: {str(e)}"
            }
    
    def wait_for_image(
        self,
        template_path: str,
        timeout: float = 10.0,
        confidence: Optional[float] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        check_interval: float = 0.5
    ) -> Dict[str, Any]:
        """
        Wait for template image to appear on screen.
        
        Args:
            template_path: Path to template image
            timeout: Maximum wait time in seconds
            confidence: Match confidence threshold
            region: Search region
            check_interval: Time between checks
        
        Returns:
            {
                "success": bool,
                "found": bool,
                "location": {"x": int, "y": int},
                "elapsed_time": float
            }
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.find_image_on_screen(template_path, confidence, region, multi_match=False)
            
            if result["found"]:
                return {
                    "success": True,
                    "found": True,
                    "location": {
                        "x": result["best_match"]["x"],
                        "y": result["best_match"]["y"]
                    },
                    "confidence": result["best_match"]["confidence"],
                    "elapsed_time": time.time() - start_time
                }
            
            time.sleep(check_interval)
        
        return {
            "success": False,
            "found": False,
            "error": f"Image not found within {timeout}s",
            "elapsed_time": time.time() - start_time
        }
    
    def find_by_feature_matching(
        self,
        template_path: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        min_matches: int = 10
    ) -> Dict[str, Any]:
        """
        Find template using feature matching (scale and rotation invariant).
        More robust but slower than template matching.
        
        Args:
            template_path: Path to template image
            region: Search region
            min_matches: Minimum number of good matches required
        
        Returns:
            {
                "success": bool,
                "found": bool,
                "location": {"x": int, "y": int},
                "matches": int
            }
        """
        try:
            # Load template
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                raise FileNotFoundError(f"Template not found: {template_path}")
            
            # Capture screen
            screen = self._capture_screen(region)
            if len(screen.shape) == 3:
                screen = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
            
            # Initialize ORB detector
            orb = cv2.ORB_create()
            
            # Find keypoints and descriptors
            kp1, des1 = orb.detectAndCompute(template, None)
            kp2, des2 = orb.detectAndCompute(screen, None)
            
            if des1 is None or des2 is None:
                return {
                    "success": False,
                    "found": False,
                    "error": "No features detected"
                }
            
            # Match features
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            matches = sorted(matches, key=lambda x: x.distance)
            
            if len(matches) < min_matches:
                return {
                    "success": True,
                    "found": False,
                    "matches": len(matches),
                    "min_matches_required": min_matches
                }
            
            # Get location from best matches
            src_pts = np.float32([kp1[m.queryIdx].pt for m in matches[:min_matches]])
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches[:min_matches]])
            
            # Calculate center location
            center_x = int(np.mean(dst_pts[:, 0]))
            center_y = int(np.mean(dst_pts[:, 1]))
            
            # Adjust for region
            if region:
                center_x += region[0]
                center_y += region[1]
            
            return {
                "success": True,
                "found": True,
                "location": {"x": center_x, "y": center_y},
                "matches": len(matches),
                "good_matches": min_matches
            }
            
        except Exception as e:
            return {
                "success": False,
                "found": False,
                "error": f"Feature matching failed: {str(e)}"
            }
    
    def find_by_color(
        self,
        color_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]],
        region: Optional[Tuple[int, int, int, int]] = None,
        min_area: int = 100
    ) -> Dict[str, Any]:
        """
        Find elements by color range.
        
        Args:
            color_range: ((lower_r, lower_g, lower_b), (upper_r, upper_g, upper_b))
            region: Search region
            min_area: Minimum area in pixels
        
        Returns:
            {
                "success": bool,
                "found": bool,
                "regions": [{"x": int, "y": int, "area": int}]
            }
        """
        try:
            # Capture screen
            screen = self._capture_screen(region)
            
            # Convert to HSV for better color detection
            hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
            
            # Create mask
            lower = np.array(color_range[0])
            upper = np.array(color_range[1])
            mask = cv2.inRange(hsv, lower, upper)
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter by area and get centers
            regions = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area >= min_area:
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        
                        # Adjust for region
                        if region:
                            cx += region[0]
                            cy += region[1]
                        
                        regions.append({"x": cx, "y": cy, "area": int(area)})
            
            return {
                "success": True,
                "found": len(regions) > 0,
                "regions": regions,
                "region_count": len(regions)
            }
            
        except Exception as e:
            return {
                "success": False,
                "found": False,
                "error": f"Color detection failed: {str(e)}"
            }
    
    def save_screenshot(
        self,
        filename: str,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Dict[str, Any]:
        """
        Save screenshot for creating templates or debugging.
        
        Args:
            filename: Output filename
            region: Region to capture
        
        Returns:
            {
                "success": bool,
                "path": str,
                "dimensions": {"width": int, "height": int}
            }
        """
        try:
            screenshot = ImageGrab.grab(bbox=region)
            screenshot.save(filename)
            
            return {
                "success": True,
                "path": str(Path(filename).absolute()),
                "dimensions": {
                    "width": screenshot.width,
                    "height": screenshot.height
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Screenshot failed: {str(e)}"
            }
    
    def get_screen_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int
    ) -> Dict[str, Any]:
        """
        Get information about a specific screen region.
        
        Args:
            x, y: Top-left coordinates
            width, height: Region dimensions
        
        Returns:
            {
                "success": bool,
                "region": {"x": int, "y": int, "width": int, "height": int},
                "dominant_colors": List[Tuple[int, int, int]]
            }
        """
        try:
            region = (x, y, x + width, y + height)
            img = self._capture_screen(region)
            
            # Calculate dominant colors
            pixels = img.reshape(-1, 3 if len(img.shape) == 3 else 1)
            colors, counts = np.unique(pixels, axis=0, return_counts=True)
            top_colors = colors[np.argsort(-counts)[:5]]
            
            return {
                "success": True,
                "region": {"x": x, "y": y, "width": width, "height": height},
                "dominant_colors": [tuple(map(int, color)) for color in top_colors],
                "total_pixels": len(pixels)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Region analysis failed: {str(e)}"
            }
