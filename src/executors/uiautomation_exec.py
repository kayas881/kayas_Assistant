"""
UI Automation Executor - Layer A (Most Reliable)

Uses Windows UI Automation (pywinauto) for native UI interaction.
Works with: Windows apps, .NET apps, Win32 apps, WPF apps.

Advantages:
- Most reliable (uses OS APIs)
- Finds elements by accessibility properties
- Works even when UI changes visually
- Can read text, states, positions

Usage:
    executor = UIAutomationExecutor()
    result = executor.find_window(title="Notepad")
    result = executor.click_button(window_title="Notepad", button_text="Save")
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time
import sys
import os

# Fix COM threading mode for Windows - MUST be set before any COM imports
if sys.platform == "win32":
    os.environ.setdefault('PYWINAUTO_COINIT_FLAGS', '0')

try:
    from pywinauto import Application, Desktop
    from pywinauto.findwindows import ElementNotFoundError, ElementAmbiguousError
    from pywinauto.timings import TimeoutError as PWTimeoutError
    PYWINAUTO_AVAILABLE = True
except (ImportError, OSError) as e:
    # Handle both missing library and COM threading errors
    PYWINAUTO_AVAILABLE = False
    _pywinauto_error = str(e)


@dataclass
class UIAutomationConfig:
    """Configuration for UI Automation"""
    timeout: int = 10  # Seconds to wait for elements
    retry_interval: float = 0.5  # Seconds between retries
    backend: str = "uia"  # "uia" (modern) or "win32" (legacy)


class UIAutomationExecutor:
    """
    Windows UI Automation executor using pywinauto.
    
    Hierarchy:
    Desktop → Application → Window → Control (button, textbox, etc.)
    """
    
    def __init__(self, config: UIAutomationConfig = None):
        if not PYWINAUTO_AVAILABLE:
            error_msg = _pywinauto_error if '_pywinauto_error' in globals() else "pywinauto not installed"
            raise ImportError(f"UI Automation not available: {error_msg}")
        
        self.config = config or UIAutomationConfig()
        self.desktop = Desktop(backend=self.config.backend)
        self.apps = {}  # Cache connected applications
    
    def find_window(self, 
                   title: str = None,
                   class_name: str = None, 
                   process_id: int = None,
                   best_match: str = None) -> Dict[str, Any]:
        """
        Find a window by various criteria.
        
        Args:
            title: Window title (can be partial match)
            class_name: Window class name
            process_id: Process ID
            best_match: Most flexible - finds by any text
            
        Returns:
            {
                "success": bool,
                "window": window object,
                "title": str,
                "class_name": str,
                "pid": int,
                "visible": bool
            }
        """
        try:
            # Build search criteria
            kwargs = {}
            if title:
                kwargs["title"] = title
            if class_name:
                kwargs["class_name"] = class_name
            if process_id:
                kwargs["process"] = process_id
            if best_match:
                kwargs["best_match"] = best_match
            
            # Find window with reduced timeout
            try:
                window = self.desktop.window(**kwargs)
                # Try to access window properties to verify it exists
                window_title = window.window_text()
            except (ElementNotFoundError, TimeoutError):
                return {
                    "success": False,
                    "error": f"Window not found with criteria: {kwargs}"
                }
            
            return {
                "success": True,
                "window": window,
                "title": window_title,
                "class_name": window.class_name(),
                "pid": window.process_id(),
                "visible": window.is_visible(),
                "enabled": window.is_enabled()
            }
            
        except ElementNotFoundError:
            return {
                "success": False,
                "error": f"Window not found with criteria: {kwargs}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error finding window: {str(e)}"
            }
    
    def list_windows(self) -> Dict[str, Any]:
        """
        List all visible windows.
        
        Returns:
            {
                "success": bool,
                "windows": [
                    {"title": str, "class_name": str, "pid": int},
                    ...
                ]
            }
        """
        try:
            windows = []
            for window in self.desktop.windows():
                if window.is_visible():
                    windows.append({
                        "title": window.window_text(),
                        "class_name": window.class_name(),
                        "pid": window.process_id()
                    })
            
            return {
                "success": True,
                "count": len(windows),
                "windows": windows
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def click_button(self,
                    window_title: str,
                    button_text: str = None,
                    button_id: str = None,
                    button_class: str = None) -> Dict[str, Any]:
        """
        Click a button in a window.
        
        Args:
            window_title: Title of the window
            button_text: Text on the button
            button_id: Automation ID of the button
            button_class: Class name of the button
            
        Returns:
            {"success": bool, "message": str}
        """
        try:
            # Find window
            window_result = self.find_window(title=window_title)
            if not window_result["success"]:
                return window_result
            
            window = window_result["window"]
            
            # Find button
            button_kwargs = {}
            if button_text:
                button_kwargs["title"] = button_text
            if button_id:
                button_kwargs["auto_id"] = button_id
            if button_class:
                button_kwargs["class_name"] = button_class
            
            button = window.child_window(**button_kwargs)
            button.wait("enabled", timeout=self.config.timeout)
            button.click()
            
            return {
                "success": True,
                "message": f"Clicked button '{button_text or button_id}' in '{window_title}'"
            }
            
        except ElementNotFoundError:
            return {
                "success": False,
                "error": f"Button not found: {button_kwargs}"
            }
        except PWTimeoutError:
            return {
                "success": False,
                "error": f"Button not enabled within {self.config.timeout}s"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error clicking button: {str(e)}"
            }
    
    def type_text(self,
                 window_title: str,
                 text: str,
                 control_id: str = None,
                 control_type: str = "Edit") -> Dict[str, Any]:
        """
        Type text into a control (textbox, editor, etc.).
        
        Args:
            window_title: Title of the window
            text: Text to type
            control_id: Automation ID of the control
            control_type: Type of control ("Edit", "Document", etc.)
            
        Returns:
            {"success": bool, "message": str}
        """
        try:
            # Find window
            window_result = self.find_window(title=window_title)
            if not window_result["success"]:
                return window_result
            
            window = window_result["window"]
            
            # Find control
            if control_id:
                control = window.child_window(auto_id=control_id)
            else:
                control = window.child_window(class_name=control_type)
            
            # Type text
            control.wait("enabled", timeout=self.config.timeout)
            control.type_keys(text, with_spaces=True)
            
            return {
                "success": True,
                "message": f"Typed text into {control_type} in '{window_title}'"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error typing text: {str(e)}"
            }
    
    def read_text(self,
                 window_title: str,
                 control_id: str = None) -> Dict[str, Any]:
        """
        Read text from a control.
        
        Args:
            window_title: Title of the window
            control_id: Automation ID (optional - reads all text if not specified)
            
        Returns:
            {"success": bool, "text": str}
        """
        try:
            # Find window
            window_result = self.find_window(title=window_title)
            if not window_result["success"]:
                return window_result
            
            window = window_result["window"]
            
            if control_id:
                control = window.child_window(auto_id=control_id)
                text = control.window_text()
            else:
                text = window.window_text()
            
            return {
                "success": True,
                "text": text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading text: {str(e)}"
            }
    
    def get_menu_items(self, window_title: str) -> Dict[str, Any]:
        """
        Get all menu items from a window.
        
        Returns:
            {"success": bool, "menus": [...]}
        """
        try:
            window_result = self.find_window(title=window_title)
            if not window_result["success"]:
                return window_result
            
            window = window_result["window"]
            menu = window.menu()
            
            items = []
            for item in menu.items():
                items.append({
                    "text": item.text(),
                    "enabled": item.is_enabled()
                })
            
            return {
                "success": True,
                "menus": items
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting menu items: {str(e)}"
            }
    
    def click_menu_item(self,
                       window_title: str,
                       menu_path: str) -> Dict[str, Any]:
        """
        Click a menu item by path.
        
        Args:
            window_title: Title of the window
            menu_path: Menu path like "File->Save" or "Edit->Copy"
            
        Returns:
            {"success": bool, "message": str}
        """
        try:
            window_result = self.find_window(title=window_title)
            if not window_result["success"]:
                return window_result
            
            window = window_result["window"]
            menu = window.menu()
            menu.select(menu_path)
            
            return {
                "success": True,
                "message": f"Clicked menu item '{menu_path}'"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error clicking menu: {str(e)}"
            }
    
    def focus_window(self, window_title: str) -> Dict[str, Any]:
        """
        Bring a window to the foreground.
        
        Returns:
            {"success": bool, "message": str}
        """
        try:
            window_result = self.find_window(title=window_title)
            if not window_result["success"]:
                return window_result
            
            window = window_result["window"]
            window.set_focus()
            
            return {
                "success": True,
                "message": f"Focused window '{window_title}'"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error focusing window: {str(e)}"
            }
    
    def close_window(self, window_title: str) -> Dict[str, Any]:
        """
        Close a window.
        
        Returns:
            {"success": bool, "message": str}
        """
        try:
            window_result = self.find_window(title=window_title)
            if not window_result["success"]:
                return window_result
            
            window = window_result["window"]
            window.close()
            
            return {
                "success": True,
                "message": f"Closed window '{window_title}'"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error closing window: {str(e)}"
            }
    
    def get_control_tree(self, window_title: str) -> Dict[str, Any]:
        """
        Get the entire control hierarchy of a window (for debugging).
        
        Returns:
            {"success": bool, "tree": str}
        """
        try:
            window_result = self.find_window(title=window_title)
            if not window_result["success"]:
                return window_result
            
            window = window_result["window"]
            tree = window.print_control_identifiers()
            
            return {
                "success": True,
                "tree": tree
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting control tree: {str(e)}"
            }
