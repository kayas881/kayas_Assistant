#!/usr/bin/env python3
"""
Perception Executor - Wrapper for PerceptionEngine
Provides a standard executor interface for the router
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class PerceptionExecutorConfig:
    """Configuration for perception executor"""
    timeout: int = 10
    enabled: bool = True


class PerceptionExecutor:
    """
    Executor wrapper for the PerceptionEngine.
    Provides tools for smart UI interaction with fallback strategies.
    """
    
    def __init__(self, config: PerceptionExecutorConfig = None):
        self.config = config or PerceptionExecutorConfig()
        
        # Try to import perception engine
        try:
            from .perception_engine import PerceptionEngine, PerceptionConfig
            self.engine = PerceptionEngine(PerceptionConfig(timeout=self.config.timeout))
            self.available = True
        except Exception as e:
            print(f"[PerceptionExecutor] Warning: PerceptionEngine not available: {e}")
            self.available = False
            self.engine = None
    
    def smart_click(self, target: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Click on UI element using multi-layer perception.
        
        Args:
            target: Element to click (button text, element ID, image path, etc.)
            context: Additional context (window_title, app_type, control_type, etc.)
        
        Returns:
            {"success": bool, "message": str, "method": str, "attempts": list, "error": Optional[str]}
        """
        if not self.available or not self.engine:
            return {
                "success": False,
                "message": "PerceptionEngine not available",
                "method": "none",
                "attempts": [],
                "error": "engine_unavailable",
                "elapsed": None,
            }
        
        context = context or {}
        try:
            result = self.engine.smart_click(target, context)
            return {
                "success": result.get("success", False),
                "message": result.get("message", "Click completed"),
                "method": result.get("method", "unknown"),
                "attempts": result.get("attempts", []),
                "error": result.get("error"),
                "elapsed": result.get("elapsed"),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {str(e)[:100]}",
                "method": "error",
                "attempts": [],
                "error": str(e),
                "elapsed": None,
            }
    
    def smart_type(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Type text using multi-layer perception.
        
        Args:
            text: Text to type
            context: Additional context (window_title, app_type, etc.)
        
        Returns:
            {"success": bool, "message": str}
        """
        if not self.available or not self.engine:
            return {
                "success": False,
                "message": "PerceptionEngine not available"
            }
        
        context = context or {}
        try:
            result = self.engine.smart_type(text, context)
            return {
                "success": result.get("success", False),
                "message": result.get("message", "Text typed")
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {str(e)[:100]}"
            }
    
    def find_and_click(self, target: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Find an element and click it using vision + automation.
        
        Args:
            target: Element to find and click
            context: Additional context
        
        Returns:
            {"success": bool, "message": str, "coordinates": (x, y)}
        """
        if not self.available or not self.engine:
            return {
                "success": False,
                "message": "PerceptionEngine not available"
            }
        
        context = context or {}
        try:
            result = self.engine.smart_click(target, context)
            return {
                "success": result.get("success", False),
                "message": result.get("message", "Element clicked"),
                "coordinates": result.get("coordinates", None)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {str(e)[:100]}"
            }
