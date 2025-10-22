"""
Perception Engine - Multi-Layer UI Interaction Orchestrator

Tries multiple methods to interact with UI, falling back when one fails:
1. Layer A: UI Automation (pywinauto) - Most reliable
2. Layer B: Application-specific (Browser/COM) - App-aware
3. Layer C: Computer Vision (OpenCV) - Visual matching
4. Layer D: OCR (Tesseract) - Text-based fallback

Usage:
    engine = PerceptionEngine()
    result = engine.smart_click("Save button")
    result = engine.smart_type("Hello", "in Notepad")
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum
import time


class PerceptionLayer(Enum):
    """Available perception layers"""
    UI_AUTOMATION = "uia"  # Layer A
    APP_SPECIFIC = "app"    # Layer B
    COMPUTER_VISION = "cv"  # Layer C
    OCR = "ocr"             # Layer D


@dataclass
class PerceptionConfig:
    """Configuration for perception engine"""
    timeout: int = 10  # Overall timeout for operation
    retry_count: int = 3  # Retries per layer
    layer_timeout: int = 3  # Timeout per layer
    enabled_layers: List[PerceptionLayer] = None  # Layers to use
    
    def __post_init__(self):
        if self.enabled_layers is None:
            # Enable all layers by default
            self.enabled_layers = list(PerceptionLayer)


class PerceptionEngine:
    """
    Multi-layer perception engine for robust UI interaction.
    
    Architecture:
        User Request
            ↓
        Perception Engine
            ↓
        Try Layer A (UI Automation)
            ↓ (if fails)
        Try Layer B (App-Specific)
            ↓ (if fails)
        Try Layer C (Computer Vision)
            ↓ (if fails)
        Try Layer D (OCR)
            ↓
        Return result or error
    """
    
    def __init__(self, config: PerceptionConfig = None):
        self.config = config or PerceptionConfig()
        
        # Initialize executors for each layer
        self.executors = {}
        self._init_executors()
    
    def _init_executors(self):
        """Initialize all available perception layers"""
        
        # Layer A: UI Automation
        if PerceptionLayer.UI_AUTOMATION in self.config.enabled_layers:
            try:
                from .uiautomation_exec import UIAutomationExecutor, UIAutomationConfig
                self.executors[PerceptionLayer.UI_AUTOMATION] = UIAutomationExecutor(
                    UIAutomationConfig(timeout=self.config.layer_timeout)
                )
            except Exception as e:
                print(f"UI Automation layer not available: {e}")
        
        # Layer B: App-Specific (browser, etc.)
        if PerceptionLayer.APP_SPECIFIC in self.config.enabled_layers:
            # These are already initialized in DirectAgent
            # We'll get references to them
            self.executors[PerceptionLayer.APP_SPECIFIC] = {}
        
        # Layer C: Computer Vision
        if PerceptionLayer.COMPUTER_VISION in self.config.enabled_layers:
            try:
                from .cv_exec import CVExecutor, CVConfig
                self.executors[PerceptionLayer.COMPUTER_VISION] = CVExecutor(
                    CVConfig(confidence=0.8)
                )
            except Exception as e:
                print(f"Computer Vision layer not available: {e}")
        
        # Layer D: OCR
        if PerceptionLayer.OCR in self.config.enabled_layers:
            try:
                from .ocr_exec import OCRExecutor, OCRConfig
                self.executors[PerceptionLayer.OCR] = OCRExecutor(
                    OCRConfig()
                )
            except Exception as e:
                print(f"OCR layer not available: {e}")
    
    def smart_click(self,
                   target: str,
                   context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Click on a UI element using best available method.
        
        Args:
            target: What to click (button text, element ID, image path, etc.)
            context: Additional context:
                - window_title: Title of window containing element
                - app_type: "browser", "desktop", etc.
                - control_type: "button", "link", etc.
                
        Returns:
            {
                "success": bool,
                "method": str,  # Which layer succeeded
                "attempts": List[Dict],  # All attempts made
                "message": str
            }
        """
        context = context or {}
        attempts = []
        start_time = time.time()
        
        # Try each layer in order
        for layer in self.config.enabled_layers:
            if time.time() - start_time > self.config.timeout:
                break
            
            executor = self.executors.get(layer)
            if not executor:
                continue
            
            print(f"[PerceptionEngine] Trying {layer.value} to click '{target}'")
            
            try:
                result = self._try_click_with_layer(layer, target, context, executor)
                attempts.append({
                    "layer": layer.value,
                    "result": result
                })
                
                if result.get("success"):
                    return {
                        "success": True,
                        "method": layer.value,
                        "attempts": attempts,
                        "message": f"Clicked '{target}' using {layer.value}",
                        "elapsed": time.time() - start_time
                    }
                    
            except Exception as e:
                attempts.append({
                    "layer": layer.value,
                    "error": str(e)
                })
        
        # All layers failed
        return {
            "success": False,
            "attempts": attempts,
            "error": f"Failed to click '{target}' with all available methods",
            "elapsed": time.time() - start_time
        }
    
    def _try_click_with_layer(self,
                             layer: PerceptionLayer,
                             target: str,
                             context: Dict[str, Any],
                             executor: Any) -> Dict[str, Any]:
        """Try clicking with a specific perception layer"""
        
        if layer == PerceptionLayer.UI_AUTOMATION:
            # Try UI Automation
            window_title = context.get("window_title", target)
            
            # Try as button
            result = executor.click_button(
                window_title=window_title,
                button_text=target
            )
            
            if not result.get("success"):
                # Try as menu item
                result = executor.click_menu_item(
                    window_title=window_title,
                    menu_path=target
                )
            
            return result
        
        elif layer == PerceptionLayer.APP_SPECIFIC:
            # App-specific logic
            app_type = context.get("app_type")
            
            if app_type == "browser":
                # Use browser executor
                # (would need reference to browser executor)
                pass
            
            return {"success": False, "error": "App-specific not implemented yet"}
        
        elif layer == PerceptionLayer.COMPUTER_VISION:
            # Try image-based clicking using CV executor
            if target.endswith(('.png', '.jpg', '.jpeg')):
                # Target is an image file - use template matching
                result = executor.click_image(
                    template_path=target,
                    confidence=context.get("confidence", 0.8),
                    region=context.get("region")
                )
                return result
            else:
                # For non-image targets, CV can't help directly
                # (Could try feature matching if we had a reference image)
                return {"success": False, "error": "CV requires image template"}
        
        elif layer == PerceptionLayer.OCR:
            # Use OCR to find and click text
            return executor.click_text(target)
        
        return {"success": False, "error": f"Unknown layer: {layer}"}
    
    def smart_type(self,
                  text: str,
                  context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Type text into a field using best available method.
        
        Args:
            text: Text to type
            context: Context (window_title, control_id, etc.)
            
        Returns:
            {"success": bool, "method": str, ...}
        """
        context = context or {}
        attempts = []
        
        for layer in self.config.enabled_layers:
            executor = self.executors.get(layer)
            if not executor:
                continue
            
            try:
                result = self._try_type_with_layer(layer, text, context, executor)
                attempts.append({
                    "layer": layer.value,
                    "result": result
                })
                
                if result.get("success"):
                    return {
                        "success": True,
                        "method": layer.value,
                        "attempts": attempts,
                        "message": f"Typed text using {layer.value}"
                    }
                    
            except Exception as e:
                attempts.append({
                    "layer": layer.value,
                    "error": str(e)
                })
        
        return {
            "success": False,
            "attempts": attempts,
            "error": "Failed to type text with all available methods"
        }
    
    def _try_type_with_layer(self,
                            layer: PerceptionLayer,
                            text: str,
                            context: Dict[str, Any],
                            executor: Any) -> Dict[str, Any]:
        """Try typing with a specific perception layer"""
        
        if layer == PerceptionLayer.UI_AUTOMATION:
            window_title = context.get("window_title", "")
            control_id = context.get("control_id")
            
            return executor.type_text(
                window_title=window_title,
                text=text,
                control_id=control_id
            )
        
        elif layer == PerceptionLayer.COMPUTER_VISION:
            # Use desktop automation to type
            return executor.run_steps(
                steps=[{
                    "action": "write",
                    "args": {"text": text}
                }]
            )
        
        return {"success": False, "error": f"Layer {layer} doesn't support typing"}
    
    def smart_read(self,
                  context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Read text from screen/window using best available method.
        
        Args:
            context: Context (window_title, region, etc.)
            
        Returns:
            {"success": bool, "text": str, "method": str}
        """
        context = context or {}
        attempts = []
        
        for layer in self.config.enabled_layers:
            executor = self.executors.get(layer)
            if not executor:
                continue
            
            try:
                result = self._try_read_with_layer(layer, context, executor)
                attempts.append({
                    "layer": layer.value,
                    "result": result
                })
                
                if result.get("success"):
                    return {
                        "success": True,
                        "method": layer.value,
                        "text": result.get("text", ""),
                        "attempts": attempts
                    }
                    
            except Exception as e:
                attempts.append({
                    "layer": layer.value,
                    "error": str(e)
                })
        
        return {
            "success": False,
            "attempts": attempts,
            "error": "Failed to read text with all available methods"
        }
    
    def _try_read_with_layer(self,
                            layer: PerceptionLayer,
                            context: Dict[str, Any],
                            executor: Any) -> Dict[str, Any]:
        """Try reading with a specific perception layer"""
        
        if layer == PerceptionLayer.UI_AUTOMATION:
            window_title = context.get("window_title", "")
            control_id = context.get("control_id")
            
            return executor.read_text(
                window_title=window_title,
                control_id=control_id
            )
        
        elif layer == PerceptionLayer.OCR:
            region = context.get("region")
            return executor.read_screen_text(region=region)
        
        return {"success": False, "error": f"Layer {layer} doesn't support reading"}
    
    def find_element(self,
                    description: str,
                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Find a UI element by description.
        
        Args:
            description: Description of element ("Save button", "username field", etc.)
            context: Additional context
            
        Returns:
            {
                "success": bool,
                "found": bool,
                "location": {"x": int, "y": int},
                "method": str
            }
        """
        context = context or {}
        
        # Try each layer to find the element
        for layer in self.config.enabled_layers:
            executor = self.executors.get(layer)
            if not executor:
                continue
            
            if layer == PerceptionLayer.OCR:
                # Try finding by text
                result = executor.find_text_on_screen(description)
                if result.get("found"):
                    match = result["matches"][0]
                    return {
                        "success": True,
                        "found": True,
                        "location": {"x": match["x"], "y": match["y"]},
                        "method": layer.value
                    }
            
            # Add more layer-specific finding logic here
        
        return {
            "success": False,
            "found": False,
            "error": f"Element '{description}' not found"
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get information about available perception layers.
        
        Returns:
            {
                "available_layers": [...],
                "capabilities": {...}
            }
        """
        available = [layer.value for layer in self.executors.keys()]
        
        capabilities = {
            "click": available,
            "type": [l.value for l in [PerceptionLayer.UI_AUTOMATION, PerceptionLayer.COMPUTER_VISION]],
            "read": [l.value for l in [PerceptionLayer.UI_AUTOMATION, PerceptionLayer.OCR]],
            "find": available
        }
        
        return {
            "available_layers": available,
            "capabilities": capabilities,
            "config": {
                "timeout": self.config.timeout,
                "retry_count": self.config.retry_count
            }
        }
