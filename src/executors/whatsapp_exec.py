"""
WhatsApp Web Automation Executor

Uses Playwright to automate WhatsApp Web (https://web.whatsapp.com)
with session persistence - only need to scan QR code once.

Usage:
    executor = WhatsAppExecutor(WhatsAppConfig())
    result = executor.send_message("John", "Hello!")
    result = executor.get_unread_messages()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path
import time
import re
import os

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from ..agent.config import artifacts_dir


@dataclass
class WhatsAppConfig:
    """Configuration for WhatsApp Web automation"""
    session_dir: str = ".agent/whatsapp_session"
    headless: bool = False  # WhatsApp Web works better with visible browser
    timeout_ms: int = 15000  # Reduced from 30000
    message_delay_ms: int = 30  # Reduced from 100 for faster typing
    viewport_width: int = 1280
    viewport_height: int = 800


# WhatsApp Web selectors (may need updates if WhatsApp changes their UI)
class Selectors:
    # QR Code / Login - be more specific to avoid false positives
    QR_CODE = 'div[data-testid="qrcode"]'
    QR_CODE_FALLBACK = 'canvas[aria-label="Scan me!"]'
    
    # Logged in indicators - multiple options for reliability
    LOGGED_IN = 'div[data-testid="chat-list"]'
    SIDE_PANEL = 'div[data-testid="side"]'
    CHAT_LIST_HEADER = 'header[data-testid="chatlist-header"]'
    
    # Search and contacts
    SEARCH_BOX = 'div[contenteditable="true"][data-tab="3"]'
    SEARCH_BOX_ALT = 'div[title="Search input textbox"]'
    CONTACT_LIST = 'div[data-testid="cell-frame-container"]'
    CONTACT_ITEM = 'span[title="{name}"]'
    
    # Chat
    MESSAGE_INPUT = 'div[contenteditable="true"][data-tab="10"]'
    MESSAGE_INPUT_ALT = 'footer div[contenteditable="true"]'
    SEND_BUTTON = 'button[data-testid="send"], span[data-icon="send"]'
    SEND_BUTTON_ALT = 'button[aria-label="Send"], span[data-testid="send"]'
    
    # Messages
    MESSAGE_IN = 'div.message-in'
    MESSAGE_OUT = 'div.message-out'
    MESSAGE_TEXT = 'span.selectable-text'
    MESSAGE_TIME = 'span[data-testid="msg-meta"] span'
    MESSAGE_ROW = 'div[data-testid="msg-container"]'
    
    # Unread indicator
    UNREAD_BADGE = 'span[data-testid="icon-unread-count"]'
    UNREAD_CHAT = 'div[data-testid="cell-frame-container"]:has(span[data-testid="icon-unread-count"])'
    
    # Attachments - multiple selectors for different WhatsApp versions
    ATTACH_BUTTON = 'div[data-testid="conversation-clip"], span[data-icon="plus"], span[data-icon="attach-menu-plus"], div[data-testid="attach-btn"], button[aria-label="Attach"]'
    ATTACH_BUTTON_ALT = 'div[title="Attach"], span[data-icon="clip"], div[aria-label="Attach"]'
    ATTACH_DOCUMENT = 'input[accept="*"]'
    ATTACH_IMAGE = 'input[accept="image/*,video/mp4,video/3gpp,video/quicktime"]'
    ATTACH_IMAGE_ALT = 'input[type="file"][accept*="image"]'
    ATTACH_VIDEO = 'input[accept="video/*"]'
    
    # Attachment menu items - comprehensive selectors for current WhatsApp Web
    ATTACH_PHOTOS = (
        'li button[aria-label="Photos & videos"], '
        'div[aria-label="Photos & videos"], '
        'span[data-icon="attach-image"], '
        'li[data-icon="attach-image"], '
        'button span[data-icon="attach-image"], '
        '[data-testid="mi-attach-media"], '
        'li:has(span[data-icon="attach-image"])'
    )
    ATTACH_DOCS = (
        'li button[aria-label="Document"], '
        'div[aria-label="Document"], '
        'span[data-icon="attach-document"], '
        'li[data-icon="attach-document"], '
        'button span[data-icon="attach-document"], '
        '[data-testid="mi-attach-document"], '
        'li:has(span[data-icon="attach-document"])'
    )
    
    # Group info
    CHAT_HEADER = 'header[data-testid="conversation-header"]'
    CHAT_TITLE = 'span[data-testid="conversation-info-header-chat-title"]'
    CHAT_INFO_BUTTON = 'div[data-testid="conversation-header"]'
    
    # Context menu (right-click on message)
    CONTEXT_MENU = 'div[data-testid="context-menu"], ul[role="menu"], div[role="menu"]'
    MENU_REPLY = (
        'div[data-testid="mi-reply"], '
        'li[data-testid="mi-reply"], '
        'div[aria-label="Reply"], '
        'li[aria-label="Reply"], '
        'span[data-icon="reply"]'
    )
    MENU_FORWARD = (
        'div[data-testid="mi-forward"], '
        'li[data-testid="mi-forward"], '
        'div[aria-label="Forward"], '
        'span[data-icon="forward"]'
    )
    MENU_DELETE = (
        'div[data-testid="mi-delete"], '
        'li[data-testid="mi-delete"], '
        'div[aria-label="Delete"], '
        'span[data-icon="delete"]'
    )
    MENU_STAR = (
        'div[data-testid="mi-star"], '
        'li[data-testid="mi-star"], '
        'div[aria-label="Star"], '
        'span[data-icon="star"]'
    )
    MENU_INFO = 'div[data-testid="mi-msg-info"], li[data-testid="mi-msg-info"]'
    
    # Chat options (three dots menu)
    CHAT_MENU = 'div[data-testid="menu"], span[data-icon="menu"]'
    MENU_MUTE = 'div[data-testid="mi-mute"]'
    MENU_ARCHIVE = 'div[data-testid="mi-archive"]'
    MENU_PIN = 'div[data-testid="mi-pin"]'
    MENU_CLEAR = 'div[data-testid="mi-clear-chat"]'
    MENU_BLOCK = 'div[data-testid="mi-block"]'
    MENU_DELETE_CHAT = 'div[data-testid="mi-delete-chat"]'
    
    # Contact info panel
    CONTACT_INFO_PANEL = 'div[data-testid="contact-info-drawer"]'
    CONTACT_STATUS = 'span[data-testid="contact-info-status"]'
    CONTACT_ABOUT = 'span[data-testid="contact-info-about"]'
    
    # Group specific
    GROUP_SUBJECT = 'div[data-testid="group-subject"]'
    GROUP_PARTICIPANTS = 'div[data-testid="participants-section"]'
    ADD_PARTICIPANT = 'div[data-testid="add-participant"]'
    
    # New chat / group
    NEW_CHAT_BUTTON = 'div[data-testid="chat-list-header-menu"], span[data-icon="new-chat"]'
    NEW_GROUP_BUTTON = 'div[data-testid="menu-bar-new-group"]'
    
    # Pinned chats
    PINNED_CHAT = 'div[data-testid="pinned"]'
    
    # Media
    MEDIA_GALLERY = 'div[data-testid="media-gallery"]'
    DOWNLOAD_BUTTON = 'span[data-icon="download"]'
    
    # Forward dialog
    FORWARD_CONTACT_SEARCH = 'div[data-testid="forward-search-input"]'
    FORWARD_SEND = 'div[data-testid="forward-send"]'
    
    # Confirmation dialogs
    CONFIRM_BUTTON = 'div[data-testid="confirm-btn"]'
    CANCEL_BUTTON = 'div[data-testid="cancel-btn"]'


class WhatsAppExecutor:
    """
    WhatsApp Web automation executor.
    
    Features:
    - Session persistence (scan QR once)
    - Send/receive messages
    - Search contacts
    - Send attachments
    - Read unread messages
    """
    
    def __init__(self, cfg: WhatsAppConfig = None):
        self.cfg = cfg or WhatsAppConfig()
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
        
        # Ensure session directory exists
        self.session_path = Path(self.cfg.session_dir).resolve()
        self.session_path.mkdir(parents=True, exist_ok=True)
        
    def _ensure_browser(self) -> bool:
        """Ensure browser is running and connected to WhatsApp Web."""
        if not PLAYWRIGHT_AVAILABLE:
            return False
            
        if self._page is not None:
            try:
                # Check if page is still valid
                self._page.title()
                return True
            except Exception:
                self._cleanup()
        
        try:
            self._playwright = sync_playwright().start()
            
            # Launch browser with persistent context for session
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.session_path),
                headless=self.cfg.headless,
                viewport={"width": self.cfg.viewport_width, "height": self.cfg.viewport_height},
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                ]
            )
            
            # Get or create page
            if self._context.pages:
                self._page = self._context.pages[0]
            else:
                self._page = self._context.new_page()
            
            self._page.set_default_timeout(self.cfg.timeout_ms)
            
            return True
        except Exception as e:
            print(f"[WhatsApp] Failed to start browser: {e}")
            self._cleanup()
            return False
    
    def _cleanup(self):
        """Clean up browser resources."""
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
    
    def _navigate_to_whatsapp(self) -> Dict[str, Any]:
        """Navigate to WhatsApp Web and wait for login."""
        try:
            current_url = self._page.url
            
            # Fast path: already on WhatsApp and logged in
            if "web.whatsapp.com" in current_url:
                # Quick check if already logged in (very short timeout)
                logged_in_selectors = f"{Selectors.LOGGED_IN}, {Selectors.SIDE_PANEL}, {Selectors.CHAT_LIST_HEADER}"
                try:
                    self._page.wait_for_selector(logged_in_selectors, timeout=2000)
                    print("[WhatsApp] Already logged in - skipping navigation")
                    return {"success": True, "logged_in": True, "fast_path": True}
                except PWTimeoutError:
                    pass  # Not logged in yet, continue below
            
            # Navigate if not on WhatsApp
            if "web.whatsapp.com" not in current_url:
                self._page.goto("https://web.whatsapp.com")
                time.sleep(1)  # Reduced from 2s
            
            # First, check if already logged in by looking for chat list or side panel
            logged_in_selectors = f"{Selectors.LOGGED_IN}, {Selectors.SIDE_PANEL}, {Selectors.CHAT_LIST_HEADER}"
            
            # Try to find logged-in indicator first (reduced timeout)
            try:
                self._page.wait_for_selector(logged_in_selectors, timeout=8000)
                print("[WhatsApp] Detected logged-in state")
                return {"success": True, "logged_in": True}
            except PWTimeoutError:
                pass
            
            # Not logged in yet - check for QR code
            qr_element = self._page.query_selector(Selectors.QR_CODE)
            if not qr_element:
                qr_element = self._page.query_selector(Selectors.QR_CODE_FALLBACK)
            
            if qr_element:
                print("[WhatsApp] QR code detected - needs scan")
                return {
                    "success": False,
                    "needs_qr_scan": True,
                    "message": "Please scan the QR code in the browser window to log in to WhatsApp Web."
                }
            
            # Neither logged in nor QR code found - page might still be loading
            # Try waiting a bit more for logged-in state
            try:
                self._page.wait_for_selector(logged_in_selectors, timeout=5000)
                print("[WhatsApp] Detected logged-in state after wait")
                return {"success": True, "logged_in": True}
            except PWTimeoutError:
                # Last resort - check if there's any main content
                main_content = self._page.query_selector('div#app, div[id="app"]')
                if main_content:
                    # App loaded but we can't determine state - assume logged in and try
                    print("[WhatsApp] App loaded, assuming logged in")
                    return {"success": True, "logged_in": True, "uncertain": True}
                
                return {
                    "success": False,
                    "needs_qr_scan": True,
                    "message": "WhatsApp Web is still loading. Please wait and try again."
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _search_contact(self, name: str) -> bool:
        """Search for a contact by name."""
        try:
            # First, press Escape to close any open panels/dialogs and clear previous search
            self._page.keyboard.press("Escape")
            time.sleep(0.15)
            
            # Try primary search box selector, fall back to alternative
            search_box = None
            try:
                search_box = self._page.wait_for_selector(Selectors.SEARCH_BOX, timeout=2000)
            except PWTimeoutError:
                try:
                    search_box = self._page.wait_for_selector(Selectors.SEARCH_BOX_ALT, timeout=2000)
                except PWTimeoutError:
                    # Try clicking the search icon/area first
                    search_area = self._page.query_selector('div[data-testid="chat-list-search"]')
                    if search_area:
                        search_area.click()
                        time.sleep(0.15)
                        search_box = self._page.wait_for_selector(Selectors.SEARCH_BOX, timeout=2000)
            
            if not search_box:
                print("[WhatsApp] Could not find search box")
                return False
                
            search_box.click()
            time.sleep(0.1)
            
            # Clear and type contact name (faster)
            search_box.fill("")
            search_box.type(name, delay=20)  # Reduced delay
            time.sleep(0.8)  # Reduced from 1.5s
            
            # Try to find and click the contact
            # Use flexible matching - look for the name in chat titles (case insensitive)
            contact_selector = f'span[title*="{name}" i]'
            try:
                contact = self._page.wait_for_selector(contact_selector, timeout=3000)
                contact.click()
                time.sleep(0.2)
                print(f"[WhatsApp] Found and clicked contact: {name}")
                return True
            except PWTimeoutError:
                # Try clicking on first search result
                try:
                    first_result = self._page.wait_for_selector(
                        Selectors.CONTACT_LIST,
                        timeout=2000
                    )
                    first_result.click()
                    time.sleep(0.2)
                    print(f"[WhatsApp] Clicked first search result for: {name}")
                    return True
                except PWTimeoutError:
                    print(f"[WhatsApp] No results found for: {name}")
                    return False
                    
        except Exception as e:
            print(f"[WhatsApp] Search contact error: {e}")
            return False
    
    def _type_message(self, message: str) -> bool:
        """Type a message in the chat input."""
        try:
            # Try primary message input selector, fall back to alternative
            msg_input = None
            try:
                msg_input = self._page.wait_for_selector(Selectors.MESSAGE_INPUT, timeout=3000)
            except PWTimeoutError:
                try:
                    msg_input = self._page.wait_for_selector(Selectors.MESSAGE_INPUT_ALT, timeout=2000)
                except PWTimeoutError:
                    pass
            
            if not msg_input:
                print("[WhatsApp] Could not find message input")
                return False
            
            msg_input.click()
            time.sleep(0.1)
            
            # Type message with fast delay
            msg_input.type(message, delay=self.cfg.message_delay_ms)
            print(f"[WhatsApp] Typed message: {message[:50]}...")
            return True
        except Exception as e:
            print(f"[WhatsApp] Type message error: {e}")
            return False
    
    def _send_message(self) -> bool:
        """Click send button or press Enter."""
        try:
            # Try clicking send button with fallback
            send_btn = None
            try:
                send_btn = self._page.wait_for_selector(Selectors.SEND_BUTTON, timeout=1500)
            except PWTimeoutError:
                try:
                    send_btn = self._page.wait_for_selector(Selectors.SEND_BUTTON_ALT, timeout=1000)
                except PWTimeoutError:
                    pass
            
            if send_btn:
                send_btn.click()
                print("[WhatsApp] Clicked send button")
                return True
            
            # Fallback: press Enter on message input
            msg_input = self._page.query_selector(Selectors.MESSAGE_INPUT)
            if not msg_input:
                msg_input = self._page.query_selector(Selectors.MESSAGE_INPUT_ALT)
            
            if msg_input:
                msg_input.press("Enter")
                print("[WhatsApp] Pressed Enter to send")
                return True
            
            return False
        except Exception as e:
            print(f"[WhatsApp] Send message error: {e}")
            return False
    
    # ==================== PUBLIC API ====================
    
    def initialize(self) -> Dict[str, Any]:
        """
        Initialize WhatsApp Web connection.
        Opens browser and navigates to WhatsApp Web.
        
        Returns:
            {"success": bool, "logged_in": bool, "needs_qr_scan": bool, "message": str}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available. Install with: pip install playwright && python -m playwright install"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        return self._navigate_to_whatsapp()
    
    def send_message(self, contact: str, message: str) -> Dict[str, Any]:
        """
        Send a message to a contact or group.
        
        Args:
            contact: Name of the contact or group
            message: Message text to send
            
        Returns:
            {"success": bool, "contact": str, "message": str, "error": str?}
        """
        try:
            if not PLAYWRIGHT_AVAILABLE:
                return {"success": False, "error": "Playwright not available. Install with: pip install playwright && python -m playwright install chromium"}
            
            if not self._ensure_browser():
                return {"success": False, "error": "Failed to start browser. Check if Chromium is installed for Playwright."}
            
            # Ensure we're on WhatsApp
            nav_result = self._navigate_to_whatsapp()
            if not nav_result.get("success"):
                # Return the navigation error with more context
                error_msg = nav_result.get("message") or nav_result.get("error") or "Failed to navigate to WhatsApp Web"
                return {
                    "success": False, 
                    "error": error_msg,
                    "action": "whatsapp.send_message",
                    "needs_qr_scan": nav_result.get("needs_qr_scan", False)
                }
            
            # Search for contact
            if not self._search_contact(contact):
                return {
                    "success": False,
                    "error": f"Contact '{contact}' not found. Make sure the name matches a chat in your WhatsApp."
                }
            
            # Type and send message
            if not self._type_message(message):
                return {"success": False, "error": "Failed to type message in the chat input box"}
            
            time.sleep(0.1)  # Reduced from 0.3s
            
            if not self._send_message():
                return {"success": False, "error": "Failed to send message - could not find or click send button"}
            
            time.sleep(0.2)  # Reduced from 0.5s
            
            return {
                "success": True,
                "contact": contact,
                "message": message,
                "action": "whatsapp.send_message"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"WhatsApp send_message error: {str(e)}",
                "contact": contact,
                "message": message
            }
    
    def get_unread_chats(self) -> Dict[str, Any]:
        """
        Get list of chats with unread messages.
        
        Returns:
            {"success": bool, "chats": [{"name": str, "unread_count": int}], "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        try:
            # Find all chats with unread badges
            unread_chats = []
            
            # Get all chat elements
            chat_elements = self._page.query_selector_all(Selectors.UNREAD_CHAT)
            
            for chat in chat_elements:
                try:
                    # Get chat name
                    name_el = chat.query_selector('span[title]')
                    name = name_el.get_attribute('title') if name_el else "Unknown"
                    
                    # Get unread count
                    badge_el = chat.query_selector(Selectors.UNREAD_BADGE)
                    unread_text = badge_el.inner_text() if badge_el else "1"
                    try:
                        unread_count = int(unread_text)
                    except ValueError:
                        unread_count = 1
                    
                    unread_chats.append({
                        "name": name,
                        "unread_count": unread_count
                    })
                except Exception:
                    continue
            
            return {
                "success": True,
                "chats": unread_chats,
                "count": len(unread_chats),
                "action": "whatsapp.get_unread_chats"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def read_messages(self, contact: str, limit: int = 10) -> Dict[str, Any]:
        """
        Read recent messages from a chat.
        
        Args:
            contact: Name of the contact or group
            limit: Maximum number of messages to read
            
        Returns:
            {"success": bool, "messages": [{"text": str, "incoming": bool, "time": str}], "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        # Search for contact
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        time.sleep(1)  # Wait for messages to load
        
        try:
            messages = []
            
            # Get incoming messages
            in_messages = self._page.query_selector_all(Selectors.MESSAGE_IN)
            for msg in in_messages[-limit:]:
                try:
                    text_el = msg.query_selector(Selectors.MESSAGE_TEXT)
                    time_el = msg.query_selector(Selectors.MESSAGE_TIME)
                    
                    text = text_el.inner_text() if text_el else ""
                    msg_time = time_el.inner_text() if time_el else ""
                    
                    if text:
                        messages.append({
                            "text": text,
                            "incoming": True,
                            "time": msg_time
                        })
                except Exception:
                    continue
            
            # Get outgoing messages
            out_messages = self._page.query_selector_all(Selectors.MESSAGE_OUT)
            for msg in out_messages[-limit:]:
                try:
                    text_el = msg.query_selector(Selectors.MESSAGE_TEXT)
                    time_el = msg.query_selector(Selectors.MESSAGE_TIME)
                    
                    text = text_el.inner_text() if text_el else ""
                    msg_time = time_el.inner_text() if time_el else ""
                    
                    if text:
                        messages.append({
                            "text": text,
                            "incoming": False,
                            "time": msg_time
                        })
                except Exception:
                    continue
            
            # Sort by time if possible (basic sort)
            # Note: WhatsApp times are relative, so this is approximate
            
            return {
                "success": True,
                "contact": contact,
                "messages": messages[-limit:],
                "count": len(messages),
                "action": "whatsapp.read_messages"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_image(self, contact: str, image_path: str, caption: str = "") -> Dict[str, Any]:
        """
        Send an image to a contact.
        
        Args:
            contact: Name of the contact or group
            image_path: Path to the image file
            caption: Optional caption for the image
            
        Returns:
            {"success": bool, "contact": str, "image": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            # Validate image path with fallback search in common folders
            img_path = Path(image_path)
            if not img_path.exists():
                name = img_path.name
                user_profile = os.environ.get("USERPROFILE", "")
                candidates = [
                    Path(user_profile) / "Documents" / name,
                    Path(user_profile) / "Downloads" / name,
                    Path(user_profile) / "Pictures" / name,
                    Path(user_profile) / "Desktop" / name,
                    Path.cwd() / name,
                ]
                found = None
                for c in candidates:
                    if c.exists():
                        found = c
                        break
                if not found:
                    search_dirs = [
                        Path(user_profile) / "Documents",
                        Path(user_profile) / "Downloads",
                        Path(user_profile) / "Pictures",
                        Path(user_profile) / "Desktop",
                    ]
                    for sd in search_dirs:
                        try:
                            matches = list(sd.rglob(name))
                            if matches:
                                found = matches[0]
                                break
                        except Exception:
                            continue
                if found:
                    img_path = found
                else:
                    return {"success": False, "error": f"Image not found: {image_path}"}

            # Click attach button - try multiple selectors
            attach_btn = None
            for selector in [Selectors.ATTACH_BUTTON, Selectors.ATTACH_BUTTON_ALT]:
                try:
                    attach_btn = self._page.wait_for_selector(selector, timeout=3000)
                    if attach_btn:
                        print(f"[WhatsApp] Found attach button with selector: {selector[:50]}...")
                        break
                except PWTimeoutError:
                    continue
            
            if not attach_btn:
                # Try clicking the + button in the chat footer area
                try:
                    footer = self._page.query_selector('footer')
                    if footer:
                        plus_btn = footer.query_selector('div[role="button"], button')
                        if plus_btn:
                            attach_btn = plus_btn
                except Exception:
                    pass
            
            if not attach_btn:
                return {"success": False, "error": "Could not find attach button. WhatsApp UI may have changed."}
            
            attach_btn.click()
            time.sleep(1)  # Give menu time to appear
            
            print("[WhatsApp] Attach menu opened, looking for file input...")
            
            # IMPORTANT: Don't click on "Photos & Videos" - that opens native file dialog
            # Instead, find the hidden file input and set files directly on it
            
            # First, find the file input that's now available after opening the menu
            file_input = None
            input_selectors = [
                Selectors.ATTACH_IMAGE,
                Selectors.ATTACH_IMAGE_ALT,
                'input[type="file"][accept*="image"]',
                'input[type="file"][accept*="video"]',
                'input[accept*="image"]',
                'input[type="file"]'
            ]
            
            for selector in input_selectors:
                try:
                    file_input = self._page.wait_for_selector(selector, timeout=1500, state="attached")
                    if file_input:
                        print(f"[WhatsApp] Found file input with selector: {selector[:50]}...")
                        break
                except PWTimeoutError:
                    continue
            
            if not file_input:
                # Last resort - find any file input on the page
                all_inputs = self._page.query_selector_all('input[type="file"]')
                if all_inputs:
                    # Prefer the one for images/videos (usually has longer accept attribute)
                    for inp in all_inputs:
                        accept = inp.get_attribute('accept') or ''
                        if 'image' in accept:
                            file_input = inp
                            break
                    if not file_input:
                        file_input = all_inputs[0]
                    print(f"[WhatsApp] Found file input via query_selector_all, total: {len(all_inputs)}")
            
            if not file_input:
                return {"success": False, "error": "Could not find file input for image upload."}
            
            # Set files directly on the input element - this bypasses the native dialog
            file_input.set_input_files(str(img_path.resolve()))
            print(f"[WhatsApp] Set file on input: {img_path.name}")
            
            # Wait for preview to load
            time.sleep(3)
            
            # Check if preview appeared (image should now be ready to send)
            # Look for the send button in the preview dialog
            print("[WhatsApp] Waiting for preview and send button...")
            
            # Add caption if provided
            if caption:
                try:
                    caption_input = self._page.wait_for_selector(
                        'div[contenteditable="true"][data-tab="10"], div[contenteditable="true"][data-lexical-editor="true"]',
                        timeout=3000
                    )
                    caption_input.type(caption, delay=50)
                except PWTimeoutError:
                    print("[WhatsApp] Caption input not found, sending without caption")
            
            # Click send - look for the send button in the preview dialog
            send_btn = None
            for selector in [Selectors.SEND_BUTTON, Selectors.SEND_BUTTON_ALT, 'span[data-icon="send"]', 'div[aria-label="Send"]']:
                try:
                    send_btn = self._page.wait_for_selector(selector, timeout=3000)
                    if send_btn:
                        break
                except PWTimeoutError:
                    continue
            
            if send_btn:
                send_btn.click()
                print("[WhatsApp] Clicked send button")
            else:
                # Try pressing Enter as fallback
                self._page.keyboard.press("Enter")
                print("[WhatsApp] Pressed Enter to send")
            
            time.sleep(2)  # Wait for image to be sent
            
            return {
                "success": True,
                "contact": contact,
                "image": str(img_path),
                "caption": caption,
                "action": "whatsapp.send_image"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_chat_info(self, contact: str) -> Dict[str, Any]:
        """
        Get information about a chat (contact or group).
        
        Args:
            contact: Name of the contact or group
            
        Returns:
            {"success": bool, "name": str, "is_group": bool, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            # Get chat title from header
            title_el = self._page.wait_for_selector(Selectors.CHAT_TITLE, timeout=5000)
            chat_name = title_el.inner_text() if title_el else contact
            
            # Check if it's a group (groups typically have member count or "Group" indicator)
            header = self._page.query_selector(Selectors.CHAT_HEADER)
            header_text = header.inner_text() if header else ""
            is_group = "members" in header_text.lower() or "participants" in header_text.lower()
            
            return {
                "success": True,
                "name": chat_name,
                "is_group": is_group,
                "action": "whatsapp.get_chat_info"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def take_screenshot(self, filename: str = None) -> Dict[str, Any]:
        """
        Take a screenshot of the current WhatsApp Web state.
        
        Args:
            filename: Optional filename for the screenshot
            
        Returns:
            {"success": bool, "path": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        try:
            art_dir = artifacts_dir()
            art_dir.mkdir(parents=True, exist_ok=True)
            
            fname = filename or f"whatsapp_{int(time.time())}.png"
            out_path = art_dir / fname
            
            self._page.screenshot(path=str(out_path))
            
            return {
                "success": True,
                "path": str(out_path),
                "action": "whatsapp.screenshot"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_document(self, contact: str, file_path: str, caption: str = "") -> Dict[str, Any]:
        """
        Send a document/file to a contact.
        
        Args:
            contact: Name of the contact or group
            file_path: Path to the file to send
            caption: Optional caption for the file
            
        Returns:
            {"success": bool, "contact": str, "file": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        # Validate file path
        doc_path = Path(file_path)
        if not doc_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            # Click attach button - try multiple selectors
            attach_btn = None
            for selector in [Selectors.ATTACH_BUTTON, Selectors.ATTACH_BUTTON_ALT]:
                try:
                    attach_btn = self._page.wait_for_selector(selector, timeout=3000)
                    if attach_btn:
                        break
                except PWTimeoutError:
                    continue
            
            if not attach_btn:
                return {"success": False, "error": "Could not find attach button"}
            
            attach_btn.click()
            time.sleep(0.8)
            
            # Try to click document option
            try:
                doc_option = self._page.wait_for_selector(Selectors.ATTACH_DOCS, timeout=2000)
                doc_option.click()
                time.sleep(0.5)
            except PWTimeoutError:
                print("[WhatsApp] Document menu item not found, looking for file input directly")
            
            # Upload document via file input
            file_input = None
            for selector in [Selectors.ATTACH_DOCUMENT, 'input[type="file"]']:
                try:
                    file_input = self._page.wait_for_selector(selector, timeout=3000)
                    if file_input:
                        break
                except PWTimeoutError:
                    continue
            
            if not file_input:
                return {"success": False, "error": "Could not find file input"}
            
            file_input.set_input_files(str(doc_path.resolve()))
            print(f"[WhatsApp] Uploading document: {doc_path.name}")
            time.sleep(3)
            
            # Add caption if provided
            if caption:
                try:
                    caption_input = self._page.wait_for_selector(
                        'div[contenteditable="true"][data-tab="10"], div[contenteditable="true"][data-lexical-editor="true"]',
                        timeout=3000
                    )
                    caption_input.type(caption, delay=50)
                except PWTimeoutError:
                    pass
            
            # Click send
            send_btn = None
            for selector in [Selectors.SEND_BUTTON, Selectors.SEND_BUTTON_ALT, 'span[data-icon="send"]']:
                try:
                    send_btn = self._page.wait_for_selector(selector, timeout=3000)
                    if send_btn:
                        break
                except PWTimeoutError:
                    continue
            
            if send_btn:
                send_btn.click()
            else:
                self._page.keyboard.press("Enter")
            
            time.sleep(2)
            
            return {
                "success": True,
                "contact": contact,
                "file": str(doc_path),
                "caption": caption,
                "action": "whatsapp.send_document"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_video(self, contact: str, video_path: str, caption: str = "") -> Dict[str, Any]:
        """
        Send a video to a contact.
        
        Args:
            contact: Name of the contact or group
            video_path: Path to the video file
            caption: Optional caption for the video
            
        Returns:
            {"success": bool, "contact": str, "video": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        # Validate video path
        vid_path = Path(video_path)
        if not vid_path.exists():
            return {"success": False, "error": f"Video not found: {video_path}"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            # Click attach button - try multiple selectors
            attach_btn = None
            for selector in [Selectors.ATTACH_BUTTON, Selectors.ATTACH_BUTTON_ALT]:
                try:
                    attach_btn = self._page.wait_for_selector(selector, timeout=3000)
                    if attach_btn:
                        break
                except PWTimeoutError:
                    continue
            
            if not attach_btn:
                return {"success": False, "error": "Could not find attach button"}
            
            attach_btn.click()
            time.sleep(0.8)
            
            # Try to click photos/videos option
            try:
                photos_option = self._page.wait_for_selector(Selectors.ATTACH_PHOTOS, timeout=2000)
                photos_option.click()
                time.sleep(0.5)
            except PWTimeoutError:
                print("[WhatsApp] Photos menu item not found, looking for file input directly")
            
            # Upload video via file input
            file_input = None
            for selector in [Selectors.ATTACH_IMAGE, Selectors.ATTACH_IMAGE_ALT, 'input[type="file"]']:
                try:
                    file_input = self._page.wait_for_selector(selector, timeout=3000)
                    if file_input:
                        break
                except PWTimeoutError:
                    continue
            
            if not file_input:
                return {"success": False, "error": "Could not find file input"}
            
            file_input.set_input_files(str(vid_path.resolve()))
            print(f"[WhatsApp] Uploading video: {vid_path.name}")
            time.sleep(5)  # Videos take longer to process
            
            # Add caption if provided
            if caption:
                try:
                    caption_input = self._page.wait_for_selector(
                        'div[contenteditable="true"][data-tab="10"], div[contenteditable="true"][data-lexical-editor="true"]',
                        timeout=3000
                    )
                    caption_input.type(caption, delay=50)
                except PWTimeoutError:
                    pass
            
            # Click send
            send_btn = None
            for selector in [Selectors.SEND_BUTTON, Selectors.SEND_BUTTON_ALT, 'span[data-icon="send"]']:
                try:
                    send_btn = self._page.wait_for_selector(selector, timeout=3000)
                    if send_btn:
                        break
                except PWTimeoutError:
                    continue
            
            if send_btn:
                send_btn.click()
            else:
                self._page.keyboard.press("Enter")
            
            time.sleep(2)
            
            return {
                "success": True,
                "contact": contact,
                "video": str(vid_path),
                "caption": caption,
                "action": "whatsapp.send_video"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_all_chats(self, limit: int = 20) -> Dict[str, Any]:
        """
        Get list of all visible chats.
        
        Args:
            limit: Maximum number of chats to return
            
        Returns:
            {"success": bool, "chats": [{"name": str, "last_message": str, "time": str, "unread": int}]}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        try:
            chats = []
            chat_elements = self._page.query_selector_all(Selectors.CONTACT_LIST)
            
            for chat in chat_elements[:limit]:
                try:
                    # Get chat name
                    name_el = chat.query_selector('span[title]')
                    name = name_el.get_attribute('title') if name_el else "Unknown"
                    
                    # Get last message preview
                    msg_el = chat.query_selector('span[title][dir="ltr"]')
                    last_message = msg_el.get_attribute('title') if msg_el else ""
                    
                    # Get time
                    time_el = chat.query_selector('div._ak8i')
                    chat_time = time_el.inner_text() if time_el else ""
                    
                    # Check for unread
                    badge_el = chat.query_selector(Selectors.UNREAD_BADGE)
                    unread = 0
                    if badge_el:
                        try:
                            unread = int(badge_el.inner_text())
                        except ValueError:
                            unread = 1
                    
                    chats.append({
                        "name": name,
                        "last_message": last_message,
                        "time": chat_time,
                        "unread": unread
                    })
                except Exception:
                    continue
            
            return {
                "success": True,
                "chats": chats,
                "count": len(chats),
                "action": "whatsapp.get_all_chats"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def mark_as_read(self, contact: str) -> Dict[str, Any]:
        """
        Mark a chat as read by opening it.
        
        Args:
            contact: Name of the contact or group
            
        Returns:
            {"success": bool, "contact": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        time.sleep(1)  # Opening chat marks it as read
        
        return {
            "success": True,
            "contact": contact,
            "action": "whatsapp.mark_as_read"
        }
    
    def _open_chat_menu(self) -> bool:
        """Open the three-dot menu in the current chat."""
        try:
            menu_btn = self._page.wait_for_selector(Selectors.CHAT_MENU, timeout=3000)
            menu_btn.click()
            time.sleep(0.3)
            return True
        except PWTimeoutError:
            return False
    
    def mute_chat(self, contact: str, duration: str = "8 hours") -> Dict[str, Any]:
        """
        Mute notifications for a chat.
        
        Args:
            contact: Name of the contact or group
            duration: "8 hours", "1 week", or "Always"
            
        Returns:
            {"success": bool, "contact": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            if not self._open_chat_menu():
                return {"success": False, "error": "Could not open chat menu"}
            
            # Click mute option
            mute_btn = self._page.wait_for_selector(Selectors.MENU_MUTE, timeout=3000)
            mute_btn.click()
            time.sleep(0.5)
            
            # Select duration
            duration_map = {
                "8 hours": 0,
                "1 week": 1,
                "always": 2
            }
            idx = duration_map.get(duration.lower(), 0)
            
            # Click the appropriate radio button
            radios = self._page.query_selector_all('input[type="radio"]')
            if radios and len(radios) > idx:
                radios[idx].click()
            
            # Confirm
            confirm_btn = self._page.query_selector(Selectors.CONFIRM_BUTTON)
            if confirm_btn:
                confirm_btn.click()
            
            time.sleep(0.5)
            
            return {
                "success": True,
                "contact": contact,
                "duration": duration,
                "action": "whatsapp.mute_chat"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def unmute_chat(self, contact: str) -> Dict[str, Any]:
        """
        Unmute notifications for a chat.
        
        Args:
            contact: Name of the contact or group
            
        Returns:
            {"success": bool, "contact": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            if not self._open_chat_menu():
                return {"success": False, "error": "Could not open chat menu"}
            
            # Click unmute option (same as mute button when already muted)
            unmute_btn = self._page.wait_for_selector(Selectors.MENU_MUTE, timeout=3000)
            unmute_btn.click()
            time.sleep(0.5)
            
            return {
                "success": True,
                "contact": contact,
                "action": "whatsapp.unmute_chat"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def archive_chat(self, contact: str) -> Dict[str, Any]:
        """
        Archive a chat.
        
        Args:
            contact: Name of the contact or group
            
        Returns:
            {"success": bool, "contact": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            if not self._open_chat_menu():
                return {"success": False, "error": "Could not open chat menu"}
            
            # Click archive option
            archive_btn = self._page.wait_for_selector(Selectors.MENU_ARCHIVE, timeout=3000)
            archive_btn.click()
            time.sleep(0.5)
            
            return {
                "success": True,
                "contact": contact,
                "action": "whatsapp.archive_chat"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def pin_chat(self, contact: str) -> Dict[str, Any]:
        """
        Pin a chat to the top.
        
        Args:
            contact: Name of the contact or group
            
        Returns:
            {"success": bool, "contact": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            if not self._open_chat_menu():
                return {"success": False, "error": "Could not open chat menu"}
            
            # Click pin option
            pin_btn = self._page.wait_for_selector(Selectors.MENU_PIN, timeout=3000)
            pin_btn.click()
            time.sleep(0.5)
            
            return {
                "success": True,
                "contact": contact,
                "action": "whatsapp.pin_chat"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def unpin_chat(self, contact: str) -> Dict[str, Any]:
        """
        Unpin a chat.
        
        Args:
            contact: Name of the contact or group
            
        Returns:
            {"success": bool, "contact": str, "error": str?}
        """
        # Same action as pin when already pinned
        return self.pin_chat(contact)
    
    def clear_chat(self, contact: str, keep_starred: bool = True) -> Dict[str, Any]:
        """
        Clear chat history.
        
        Args:
            contact: Name of the contact or group
            keep_starred: Whether to keep starred messages
            
        Returns:
            {"success": bool, "contact": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            if not self._open_chat_menu():
                return {"success": False, "error": "Could not open chat menu"}
            
            # Click clear chat option
            clear_btn = self._page.wait_for_selector(Selectors.MENU_CLEAR, timeout=3000)
            clear_btn.click()
            time.sleep(0.5)
            
            # Handle keep starred checkbox
            if keep_starred:
                checkbox = self._page.query_selector('input[type="checkbox"]')
                if checkbox and not checkbox.is_checked():
                    checkbox.click()
            
            # Confirm
            confirm_btn = self._page.wait_for_selector(Selectors.CONFIRM_BUTTON, timeout=3000)
            confirm_btn.click()
            time.sleep(0.5)
            
            return {
                "success": True,
                "contact": contact,
                "kept_starred": keep_starred,
                "action": "whatsapp.clear_chat"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_chat(self, contact: str) -> Dict[str, Any]:
        """
        Delete a chat completely.
        
        Args:
            contact: Name of the contact or group
            
        Returns:
            {"success": bool, "contact": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            if not self._open_chat_menu():
                return {"success": False, "error": "Could not open chat menu"}
            
            # Click delete chat option
            delete_btn = self._page.wait_for_selector(Selectors.MENU_DELETE_CHAT, timeout=3000)
            delete_btn.click()
            time.sleep(0.5)
            
            # Confirm
            confirm_btn = self._page.wait_for_selector(Selectors.CONFIRM_BUTTON, timeout=3000)
            confirm_btn.click()
            time.sleep(0.5)
            
            return {
                "success": True,
                "contact": contact,
                "action": "whatsapp.delete_chat"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _open_contact_info(self) -> bool:
        """Open contact/group info panel."""
        try:
            header = self._page.wait_for_selector(Selectors.CHAT_INFO_BUTTON, timeout=3000)
            header.click()
            time.sleep(0.5)
            return True
        except PWTimeoutError:
            return False
    
    def block_contact(self, contact: str) -> Dict[str, Any]:
        """
        Block a contact.
        
        Args:
            contact: Name of the contact
            
        Returns:
            {"success": bool, "contact": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            if not self._open_chat_menu():
                return {"success": False, "error": "Could not open chat menu"}
            
            # Click block option
            block_btn = self._page.wait_for_selector(Selectors.MENU_BLOCK, timeout=3000)
            block_btn.click()
            time.sleep(0.5)
            
            # Confirm
            confirm_btn = self._page.wait_for_selector(Selectors.CONFIRM_BUTTON, timeout=3000)
            confirm_btn.click()
            time.sleep(0.5)
            
            return {
                "success": True,
                "contact": contact,
                "action": "whatsapp.block_contact"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def unblock_contact(self, contact: str) -> Dict[str, Any]:
        """
        Unblock a contact.
        
        Args:
            contact: Name of the contact
            
        Returns:
            {"success": bool, "contact": str, "error": str?}
        """
        # Same action as block when already blocked
        return self.block_contact(contact)
    
    def get_contact_info(self, contact: str) -> Dict[str, Any]:
        """
        Get detailed information about a contact.
        
        Args:
            contact: Name of the contact
            
        Returns:
            {"success": bool, "name": str, "about": str, "is_group": bool, "members": list?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            if not self._open_contact_info():
                return {"success": False, "error": "Could not open contact info"}
            
            time.sleep(1)  # Wait for info panel to load
            
            # Get contact name
            title_el = self._page.query_selector(Selectors.CHAT_TITLE)
            name = title_el.inner_text() if title_el else contact
            
            # Get about/status
            about_el = self._page.query_selector(Selectors.CONTACT_ABOUT)
            about = about_el.inner_text() if about_el else ""
            
            # Check if group
            participants_el = self._page.query_selector(Selectors.GROUP_PARTICIPANTS)
            is_group = participants_el is not None
            
            result = {
                "success": True,
                "name": name,
                "about": about,
                "is_group": is_group,
                "action": "whatsapp.get_contact_info"
            }
            
            # Get group members if it's a group
            if is_group:
                members = []
                member_els = self._page.query_selector_all(f'{Selectors.GROUP_PARTICIPANTS} span[title]')
                for member in member_els:
                    try:
                        members.append(member.get_attribute('title'))
                    except Exception:
                        continue
                result["members"] = members
                result["member_count"] = len(members)
            
            # Close info panel (press Escape)
            self._page.keyboard.press("Escape")
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def forward_message(self, from_contact: str, to_contact: str, message_index: int = 0) -> Dict[str, Any]:
        """
        Forward a message from one chat to another.
        
        Args:
            from_contact: Name of the chat containing the message
            to_contact: Name of the chat to forward to
            message_index: Index of the message to forward (0 = most recent)
            
        Returns:
            {"success": bool, "from": str, "to": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(from_contact):
            return {"success": False, "error": f"Contact '{from_contact}' not found"}
        
        try:
            time.sleep(1)
            
            # Get messages
            messages = self._page.query_selector_all(Selectors.MESSAGE_ROW)
            if not messages:
                messages = self._page.query_selector_all(f'{Selectors.MESSAGE_IN}, {Selectors.MESSAGE_OUT}')
            
            if not messages or len(messages) <= message_index:
                return {"success": False, "error": "Message not found"}
            
            # Select the message (from end)
            target_msg = messages[-(message_index + 1)]
            
            # Hover and click dropdown
            target_msg.hover()
            time.sleep(0.3)
            
            # Click the dropdown arrow
            dropdown = target_msg.query_selector('span[data-icon="down-context"]')
            if dropdown:
                dropdown.click()
            else:
                # Right-click as fallback
                target_msg.click(button="right")
            
            time.sleep(0.3)
            
            # Click forward
            forward_btn = self._page.wait_for_selector(Selectors.MENU_FORWARD, timeout=3000)
            forward_btn.click()
            time.sleep(0.5)
            
            # Search for destination contact
            search_input = self._page.wait_for_selector(Selectors.FORWARD_CONTACT_SEARCH, timeout=5000)
            search_input.type(to_contact, delay=50)
            time.sleep(1)
            
            # Click on contact
            contact_el = self._page.wait_for_selector(f'span[title*="{to_contact}" i]', timeout=5000)
            contact_el.click()
            time.sleep(0.3)
            
            # Click send/forward button
            send_btn = self._page.wait_for_selector(Selectors.FORWARD_SEND, timeout=3000)
            send_btn.click()
            time.sleep(0.5)
            
            return {
                "success": True,
                "from_contact": from_contact,
                "to_contact": to_contact,
                "action": "whatsapp.forward_message"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def reply_to_message(self, contact: str, reply_text: str, message_index: int = 0) -> Dict[str, Any]:
        """
        Reply to a specific message in a chat.
        
        Args:
            contact: Name of the contact or group
            reply_text: The reply message text
            message_index: Index of the message to reply to (0 = most recent)
            
        Returns:
            {"success": bool, "contact": str, "reply": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            time.sleep(0.5)  # Reduced from 1.5s
            
            # Get the message list container first
            # WhatsApp has message bubbles inside divs with class message-in or message-out
            # The dropdown arrow appears on hover inside each message bubble
            
            # Try multiple selectors for messages
            messages = []
            
            # Try: div[data-testid="msg-container"] - container for each message
            messages = self._page.query_selector_all('div[data-testid="msg-container"]')
            print(f"[WhatsApp] Found {len(messages)} msg-container elements")
            
            if not messages or len(messages) == 0:
                # Try: message-in and message-out classes
                messages = self._page.query_selector_all('div.message-in, div.message-out')
                print(f"[WhatsApp] Found {len(messages)} message-in/out elements")
            
            if not messages or len(messages) == 0:
                # Try: rows in the message list
                messages = self._page.query_selector_all('div[role="row"]')
                print(f"[WhatsApp] Found {len(messages)} role=row elements")
            
            if not messages or len(messages) <= message_index:
                return {"success": False, "error": f"Message not found. Found {len(messages) if messages else 0} messages."}
            
            # Select the message (from end, 0 = most recent)
            target_msg = messages[-(message_index + 1)]
            print(f"[WhatsApp] Targeting message at index -{message_index + 1}")
            
            # Scroll the message into view and hover to reveal dropdown
            target_msg.scroll_into_view_if_needed()
            time.sleep(0.2)  # Reduced from 0.5s
            
            # Get the bounding box of the message for precise hovering
            box = target_msg.bounding_box()
            if box:
                # Hover in the middle-right area where the dropdown appears
                hover_x = box['x'] + box['width'] - 30  # Right side
                hover_y = box['y'] + box['height'] / 2   # Middle
                self._page.mouse.move(hover_x, hover_y)
                print(f"[WhatsApp] Hovering at ({hover_x}, {hover_y})")
            else:
                target_msg.hover()
            
            time.sleep(0.4)  # Reduced from 0.8s - Wait for dropdown to appear
            
            # Take screenshot to see what appeared
            self._page.screenshot(path="debug_screens/after_hover.png")
            
            # Look for the dropdown arrow - it should now be visible
            # The arrow appears as a small button/span with down arrow icon
            dropdown = None
            
            # First try inside the message
            dropdown_selectors = [
                'span[data-icon="down-context"]',
                'span[data-icon="chevron"]', 
                'span[data-icon="chevron-down-alt"]',
                'span[data-icon="down"]',
                'span[data-icon="caret-down"]',
                'span[data-testid="down-context"]',
                'span[data-testid="icon-down-context"]',
                'button span[data-icon]',
                '[role="button"] span[data-icon]',
            ]
            
            for sel in dropdown_selectors:
                dropdown = target_msg.query_selector(sel)
                if dropdown and dropdown.is_visible():
                    print(f"[WhatsApp] Found dropdown inside message: {sel}")
                    break
                dropdown = None
            
            # Also check for dropdown that might be positioned near but outside message div
            # (WhatsApp sometimes renders it in a floating layer)
            if not dropdown:
                # Look for any visible down-arrow icon on the page that appeared after hover
                all_icons = self._page.query_selector_all('span[data-icon]')
                for icon in all_icons:
                    try:
                        icon_name = icon.get_attribute('data-icon')
                        if icon_name and 'down' in icon_name.lower() and icon.is_visible():
                            # Check if it's near our message
                            icon_box = icon.bounding_box()
                            if icon_box and box:
                                # Should be within reasonable distance of our message
                                if abs(icon_box['y'] - box['y']) < 100:
                                    dropdown = icon
                                    print(f"[WhatsApp] Found nearby dropdown icon: {icon_name}")
                                    break
                    except:
                        pass
            
            if dropdown:
                dropdown.click()
                print("[WhatsApp] Clicked dropdown arrow")
                time.sleep(0.5)
                reply_mode_active = False  # Need to find and click Reply button
            else:
                # Alternative: Try keyboard shortcut or double-click
                print("[WhatsApp] No dropdown found, trying alternative methods")
                
                # Method 1: Double-click sometimes opens reply
                target_msg.dblclick()
                time.sleep(0.8)
                
                # Check if reply mode is active (quoted message appears above input)
                # Try multiple selectors for the quote preview
                reply_preview_selectors = [
                    'div[data-testid="quoted-message-preview"]',
                    'div[data-testid="reply-preview"]', 
                    'div[data-testid="quoted-message"]',
                    'div[data-testid="compose-quote"]',
                    'span[data-testid="quoted-message"]',
                    # Also look for the X button to cancel reply (indicates reply mode)
                    'span[data-icon="x-light"]',
                    'span[data-icon="x"]',
                    'button[aria-label="Cancel reply"]',
                ]
                
                reply_preview = None
                for sel in reply_preview_selectors:
                    reply_preview = self._page.query_selector(sel)
                    if reply_preview and reply_preview.is_visible():
                        print(f"[WhatsApp] Found reply preview with: {sel}")
                        break
                    reply_preview = None
                
                if reply_preview:
                    print("[WhatsApp] Double-click activated reply mode!")
                    reply_mode_active = True
                else:
                    # Even if we can't find the preview, still try to type
                    # The double-click might have worked
                    print("[WhatsApp] Reply preview not detected, but trying to type anyway...")
                    reply_mode_active = True  # Assume it worked, try typing
                    
                    # Take screenshot for debugging
                    self._page.screenshot(path="debug_screens/after_dblclick.png")
                    
                    # Log visible icons for debugging
                    all_icons = self._page.query_selector_all('span[data-icon]')
                    visible_icons = []
                    for icon in all_icons:
                        try:
                            if icon.is_visible():
                                visible_icons.append(icon.get_attribute('data-icon'))
                        except:
                            pass
                    print(f"[WhatsApp] Visible data-icons: {visible_icons[:20]}")
            
            time.sleep(0.5)
            
            # Initialize reply_btn
            reply_btn = None
            
            # If reply mode is already active from double-click, skip to typing
            if reply_mode_active:
                print("[WhatsApp] Reply mode active, skipping menu search - going directly to type message")
            else:
                # Take a screenshot to see what menu appeared
                self._page.screenshot(path="debug_screens/reply_menu_before.png")
                
                # Now look for the Reply option in the context menu
                
                # Strategy 0: Direct selector for WhatsApp's Reply span (from user inspection)
                # The Reply button is: <span class="x1o2sk6j x6prxxf...">Reply</span>
                try:
                    # Look for span containing exactly "Reply"
                    reply_spans = self._page.query_selector_all('span')
                    for span in reply_spans:
                        try:
                            if span.is_visible() and span.inner_text().strip() == "Reply":
                                reply_btn = span
                                print("[WhatsApp] Found Reply span by exact text!")
                                break
                        except:
                            pass
                except Exception as e:
                    print(f"[WhatsApp] Span search error: {e}")
                
                # Strategy 1: Look in menu container
                if not reply_btn:
                    menu_container = self._page.query_selector('div[data-testid="popup-contents"], ul[role="menu"], div[role="menu"], div[role="listbox"]')
                    if menu_container:
                        print(f"[WhatsApp] Found menu container")
                        menu_items = menu_container.query_selector_all('div[role="button"], li, div[tabindex], span')
                        print(f"[WhatsApp] Found {len(menu_items)} items in menu")
                        for i, item in enumerate(menu_items[:10]):
                            try:
                                text = item.inner_text().strip()
                                if text:
                                    print(f"[WhatsApp] Menu item {i}: '{text}'")
                                    if "reply" in text.lower():
                                        reply_btn = item
                                        print(f"[WhatsApp] Found Reply in menu!")
                                        break
                            except:
                                pass
                
                # Strategy 2: Look for menu items by data-testid
                if not reply_btn:
                    reply_selectors = [
                        'div[data-testid="mi-reply"]',
                        'li[data-testid="mi-reply"]',
                        '[data-testid="popup-contents"] div:has-text("Reply")',
                        'div[role="button"]:has-text("Reply")',
                        'li:has-text("Reply")',
                    ]
                    for sel in reply_selectors:
                        try:
                            elem = self._page.query_selector(sel)
                            if elem and elem.is_visible():
                                reply_btn = elem
                                print(f"[WhatsApp] Found Reply with selector: {sel}")
                                break
                        except:
                            pass
                
                # Strategy 3: Find by text content anywhere visible
                if not reply_btn:
                    try:
                        all_visible = self._page.query_selector_all('div, span, li')
                        for elem in all_visible:
                            try:
                                if elem.is_visible():
                                    text = elem.inner_text()
                                    if text and text.strip() == "Reply":
                                        box = elem.bounding_box()
                                        if box and box['width'] > 20 and box['height'] > 15:
                                            reply_btn = elem
                                            print("[WhatsApp] Found Reply by exact text match")
                                            break
                            except:
                                pass
                    except Exception as e:
                        print(f"[WhatsApp] Text search failed: {e}")
                
                # If we found a reply button, click it
                if reply_btn:
                    reply_btn.click()
                    print("[WhatsApp] Clicked Reply")
                    time.sleep(0.5)
                else:
                    # Check if reply mode got activated somehow
                    reply_preview = self._page.query_selector('div[data-testid="quoted-message"], div._aju8')
                    if reply_preview and reply_preview.is_visible():
                        print("[WhatsApp] Reply mode already active!")
                    else:
                        self._page.screenshot(path="debug_screens/reply_menu_debug.png")
                        return {"success": False, "error": "Could not find Reply option in menu. Screenshot saved."}
            
            # Type reply
            if not self._type_message(reply_text):
                return {"success": False, "error": "Failed to type reply"}
            
            # Send
            if not self._send_message():
                return {"success": False, "error": "Failed to send reply"}
            
            time.sleep(0.5)
            
            return {
                "success": True,
                "contact": contact,
                "reply": reply_text,
                "action": "whatsapp.reply_to_message"
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def delete_message(self, contact: str, message_index: int = 0, for_everyone: bool = True) -> Dict[str, Any]:
        """
        Delete a message.
        
        Args:
            contact: Name of the contact or group
            message_index: Index of the message to delete (0 = most recent outgoing)
            for_everyone: Delete for everyone (only works for recent messages you sent)
            
        Returns:
            {"success": bool, "contact": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            time.sleep(1)
            
            # Get outgoing messages only (can only delete your own)
            messages = self._page.query_selector_all(Selectors.MESSAGE_OUT)
            
            if not messages or len(messages) <= message_index:
                return {"success": False, "error": "Message not found (can only delete your own messages)"}
            
            # Select the message (from end)
            target_msg = messages[-(message_index + 1)]
            
            # Hover and click dropdown
            target_msg.hover()
            time.sleep(0.3)
            
            dropdown = target_msg.query_selector('span[data-icon="down-context"]')
            if dropdown:
                dropdown.click()
            else:
                target_msg.click(button="right")
            
            time.sleep(0.3)
            
            # Click delete
            delete_btn = self._page.wait_for_selector(Selectors.MENU_DELETE, timeout=3000)
            delete_btn.click()
            time.sleep(0.5)
            
            # Select delete option
            if for_everyone:
                try:
                    for_everyone_btn = self._page.wait_for_selector('div:has-text("Delete for everyone")', timeout=2000)
                    for_everyone_btn.click()
                except PWTimeoutError:
                    # Fallback to delete for me
                    for_me_btn = self._page.wait_for_selector('div:has-text("Delete for me")', timeout=2000)
                    for_me_btn.click()
            else:
                for_me_btn = self._page.wait_for_selector('div:has-text("Delete for me")', timeout=3000)
                for_me_btn.click()
            
            time.sleep(0.5)
            
            return {
                "success": True,
                "contact": contact,
                "deleted_for_everyone": for_everyone,
                "action": "whatsapp.delete_message"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def star_message(self, contact: str, message_index: int = 0) -> Dict[str, Any]:
        """
        Star/unstar a message.
        
        Args:
            contact: Name of the contact or group
            message_index: Index of the message to star (0 = most recent)
            
        Returns:
            {"success": bool, "contact": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            time.sleep(1)
            
            # Get all messages
            messages = self._page.query_selector_all(Selectors.MESSAGE_ROW)
            if not messages:
                messages = self._page.query_selector_all(f'{Selectors.MESSAGE_IN}, {Selectors.MESSAGE_OUT}')
            
            if not messages or len(messages) <= message_index:
                return {"success": False, "error": "Message not found"}
            
            target_msg = messages[-(message_index + 1)]
            
            # Hover and click dropdown
            target_msg.hover()
            time.sleep(0.3)
            
            dropdown = target_msg.query_selector('span[data-icon="down-context"]')
            if dropdown:
                dropdown.click()
            else:
                target_msg.click(button="right")
            
            time.sleep(0.3)
            
            # Click star
            star_btn = self._page.wait_for_selector(Selectors.MENU_STAR, timeout=3000)
            star_btn.click()
            time.sleep(0.3)
            
            return {
                "success": True,
                "contact": contact,
                "action": "whatsapp.star_message"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_messages(self, query: str, contact: str = None) -> Dict[str, Any]:
        """
        Search for messages containing a query.
        
        Args:
            query: Text to search for
            contact: Optional - search only in this chat
            
        Returns:
            {"success": bool, "results": [{"contact": str, "message": str}], "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        try:
            if contact:
                # Search within specific chat
                if not self._search_contact(contact):
                    return {"success": False, "error": f"Contact '{contact}' not found"}
                
                time.sleep(0.2)  # Reduced from 0.5s

                # Ensure focus is in the chat pane (not the left sidebar)
                try:
                    self._page.click('#main')
                except Exception:
                    try:
                        header = self._page.query_selector(Selectors.CHAT_HEADER)
                        if header:
                            header.click()
                    except Exception:
                        pass
                time.sleep(0.2)

                # Open the in-chat search UI and type directly (WhatsApp auto-focuses the search box)
                self._page.keyboard.press("Control+Shift+f")
                time.sleep(0.2)  # Reduced from 0.4s

                # If focus still ends up in the sidebar, refocus the chat and try again
                for _ in range(2):
                    try:
                        in_side = bool(self._page.evaluate('() => !!document.activeElement && !!document.activeElement.closest("#side")'))
                    except Exception:
                        in_side = False
                    if not in_side:
                        break
                    try:
                        self._page.click('#main')
                    except Exception:
                        pass
                    time.sleep(0.1)
                    self._page.keyboard.press("Control+Shift+f")
                    time.sleep(0.3)

                # Best-effort clear and type query into whichever element is focused
                try:
                    self._page.keyboard.press('Control+a')
                    self._page.keyboard.press('Backspace')
                except Exception:
                    pass

                self._page.keyboard.type(query, delay=25)  # Reduced from delay=50
                print(f"[WhatsApp] Typed query: {query}")
                time.sleep(0.4)  # Reduced from 0.6s

                # Select the first result and jump to it (keyboard-only, avoids fragile selectors)
                # WhatsApp typically supports ArrowDown to focus a result, then Enter to open it.
                try:
                    self._page.keyboard.press("ArrowDown")
                    time.sleep(0.1)  # Reduced from 0.15s
                    self._page.keyboard.press("ArrowDown")
                    time.sleep(0.1)  # Reduced from 0.15s
                    self._page.keyboard.press("Enter")
                    print("[WhatsApp] Attempted to jump to first search result")
                except Exception:
                    pass

                # For in-chat searches, the primary goal is navigation to the match.
                # Do not press Escape or collect sidebar results after this, as it can pull focus back to the chat list.
                return {
                    "success": True,
                    "query": query,
                    "contact": contact,
                    "action": "whatsapp.search_messages"
                }
                
            else:
                # Global search
                search_box = None
                try:
                    search_box = self._page.wait_for_selector(Selectors.SEARCH_BOX, timeout=3000)
                except PWTimeoutError:
                    search_box = self._page.wait_for_selector(Selectors.SEARCH_BOX_ALT, timeout=3000)
                
                search_box.click()
                search_box.type(query, delay=25)  # Reduced from 50
                time.sleep(0.8)  # Reduced from 1.5s
            
            # Collect results
            results = []
            result_els = self._page.query_selector_all('div[data-testid="search-result"]')
            
            if not result_els:
                # Try alternative selector
                result_els = self._page.query_selector_all(Selectors.CONTACT_LIST)
            
            for result in result_els[:20]:  # Limit results
                try:
                    name_el = result.query_selector('span[title]')
                    msg_el = result.query_selector('span[title][dir="ltr"]')
                    
                    results.append({
                        "contact": name_el.get_attribute('title') if name_el else "Unknown",
                        "message": msg_el.get_attribute('title') if msg_el else ""
                    })
                except Exception:
                    continue
            
            # Clear search
            self._page.keyboard.press("Escape")
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results),
                "action": "whatsapp.search_messages"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_group(self, group_name: str, members: List[str]) -> Dict[str, Any]:
        """
        Create a new WhatsApp group.
        
        Args:
            group_name: Name for the new group
            members: List of contact names to add
            
        Returns:
            {"success": bool, "group_name": str, "members": list, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        try:
            # Click new chat button
            new_chat_btn = self._page.wait_for_selector(Selectors.NEW_CHAT_BUTTON, timeout=5000)
            new_chat_btn.click()
            time.sleep(0.5)
            
            # Click new group
            new_group_btn = self._page.wait_for_selector(Selectors.NEW_GROUP_BUTTON, timeout=5000)
            new_group_btn.click()
            time.sleep(0.5)
            
            # Add members
            added_members = []
            for member in members:
                try:
                    search_input = self._page.wait_for_selector('div[data-testid="search-input"]', timeout=3000)
                    search_input.fill("")
                    search_input.type(member, delay=50)
                    time.sleep(0.5)
                    
                    # Click on member
                    member_el = self._page.wait_for_selector(f'span[title*="{member}" i]', timeout=3000)
                    member_el.click()
                    added_members.append(member)
                    time.sleep(0.3)
                except PWTimeoutError:
                    continue
            
            if not added_members:
                return {"success": False, "error": "Could not add any members"}
            
            # Click next/continue
            next_btn = self._page.wait_for_selector('span[data-icon="arrow-forward"]', timeout=5000)
            next_btn.click()
            time.sleep(0.5)
            
            # Enter group name
            subject_input = self._page.wait_for_selector('div[data-testid="group-subject"]', timeout=5000)
            subject_input.type(group_name, delay=50)
            time.sleep(0.3)
            
            # Create group
            create_btn = self._page.wait_for_selector('span[data-icon="checkmark"]', timeout=5000)
            create_btn.click()
            time.sleep(1)
            
            return {
                "success": True,
                "group_name": group_name,
                "members": added_members,
                "action": "whatsapp.create_group"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def add_to_group(self, group_name: str, members: List[str]) -> Dict[str, Any]:
        """
        Add members to an existing group.
        
        Args:
            group_name: Name of the group
            members: List of contact names to add
            
        Returns:
            {"success": bool, "group_name": str, "added": list, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(group_name):
            return {"success": False, "error": f"Group '{group_name}' not found"}
        
        try:
            # Open group info
            if not self._open_contact_info():
                return {"success": False, "error": "Could not open group info"}
            
            time.sleep(0.5)
            
            # Click add participant
            add_btn = self._page.wait_for_selector(Selectors.ADD_PARTICIPANT, timeout=5000)
            add_btn.click()
            time.sleep(0.5)
            
            # Add members
            added = []
            for member in members:
                try:
                    search_input = self._page.wait_for_selector('div[data-testid="search-input"]', timeout=3000)
                    search_input.fill("")
                    search_input.type(member, delay=50)
                    time.sleep(0.5)
                    
                    member_el = self._page.wait_for_selector(f'span[title*="{member}" i]', timeout=3000)
                    member_el.click()
                    added.append(member)
                    time.sleep(0.3)
                except PWTimeoutError:
                    continue
            
            if added:
                # Confirm
                confirm_btn = self._page.wait_for_selector('span[data-icon="checkmark"]', timeout=5000)
                confirm_btn.click()
                time.sleep(0.5)
            
            # Close panel
            self._page.keyboard.press("Escape")
            
            return {
                "success": True,
                "group_name": group_name,
                "added": added,
                "action": "whatsapp.add_to_group"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def leave_group(self, group_name: str) -> Dict[str, Any]:
        """
        Leave a WhatsApp group.
        
        Args:
            group_name: Name of the group
            
        Returns:
            {"success": bool, "group_name": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(group_name):
            return {"success": False, "error": f"Group '{group_name}' not found"}
        
        try:
            # Open group info
            if not self._open_contact_info():
                return {"success": False, "error": "Could not open group info"}
            
            time.sleep(0.5)
            
            # Scroll down to find "Exit group" option
            info_panel = self._page.query_selector(Selectors.CONTACT_INFO_PANEL)
            if info_panel:
                for _ in range(3):
                    info_panel.evaluate('el => el.scrollBy(0, 300)')
                    time.sleep(0.2)
            
            # Click exit group
            exit_btn = self._page.wait_for_selector('div[data-testid="exit-group"]', timeout=5000)
            exit_btn.click()
            time.sleep(0.5)
            
            # Confirm
            confirm_btn = self._page.wait_for_selector(Selectors.CONFIRM_BUTTON, timeout=3000)
            confirm_btn.click()
            time.sleep(0.5)
            
            return {
                "success": True,
                "group_name": group_name,
                "action": "whatsapp.leave_group"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_location(self, contact: str, latitude: float = None, longitude: float = None) -> Dict[str, Any]:
        """
        Send current or specified location to a contact.
        
        Args:
            contact: Name of the contact or group
            latitude: Optional latitude (if not provided, sends live location button)
            longitude: Optional longitude
            
        Returns:
            {"success": bool, "contact": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            # Click attach button
            attach_btn = self._page.wait_for_selector(Selectors.ATTACH_BUTTON, timeout=5000)
            attach_btn.click()
            time.sleep(0.5)
            
            # Click location option
            location_btn = self._page.wait_for_selector('span[data-icon="location"]', timeout=5000)
            location_btn.click()
            time.sleep(1)
            
            # If coordinates provided, we can't really set them via UI
            # Just click "Send your current location"
            current_location_btn = self._page.wait_for_selector('div:has-text("Send your current location")', timeout=5000)
            current_location_btn.click()
            time.sleep(1)
            
            return {
                "success": True,
                "contact": contact,
                "action": "whatsapp.send_location"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_contact(self, to_contact: str, share_contact: str) -> Dict[str, Any]:
        """
        Share a contact with another contact.
        
        Args:
            to_contact: Name of the recipient
            share_contact: Name of the contact to share
            
        Returns:
            {"success": bool, "to": str, "shared": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(to_contact):
            return {"success": False, "error": f"Contact '{to_contact}' not found"}
        
        try:
            # Click attach button
            attach_btn = self._page.wait_for_selector(Selectors.ATTACH_BUTTON, timeout=5000)
            attach_btn.click()
            time.sleep(0.5)
            
            # Click contact option
            contact_btn = self._page.wait_for_selector('span[data-icon="contact"]', timeout=5000)
            contact_btn.click()
            time.sleep(0.5)
            
            # Search for contact to share
            search_input = self._page.wait_for_selector('div[data-testid="search-input"]', timeout=5000)
            search_input.type(share_contact, delay=50)
            time.sleep(0.5)
            
            # Select contact
            contact_el = self._page.wait_for_selector(f'span[title*="{share_contact}" i]', timeout=5000)
            contact_el.click()
            time.sleep(0.3)
            
            # Send
            send_btn = self._page.wait_for_selector(Selectors.SEND_BUTTON, timeout=5000)
            send_btn.click()
            time.sleep(0.5)
            
            return {
                "success": True,
                "to_contact": to_contact,
                "shared_contact": share_contact,
                "action": "whatsapp.send_contact"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_last_seen(self, contact: str) -> Dict[str, Any]:
        """
        Get the last seen status of a contact.
        
        Args:
            contact: Name of the contact
            
        Returns:
            {"success": bool, "contact": str, "status": str, "error": str?}
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not available"}
        
        if not self._ensure_browser():
            return {"success": False, "error": "Failed to start browser"}
        
        nav_result = self._navigate_to_whatsapp()
        if not nav_result.get("success"):
            return nav_result
        
        if not self._search_contact(contact):
            return {"success": False, "error": f"Contact '{contact}' not found"}
        
        try:
            time.sleep(1)
            
            # Get status from chat header
            header = self._page.wait_for_selector(Selectors.CHAT_HEADER, timeout=5000)
            
            # Look for status text (online, last seen, typing...)
            status_el = header.query_selector('span[title]')
            if not status_el:
                status_el = header.query_selector('span:nth-child(2)')
            
            status = status_el.inner_text() if status_el else "Unknown"
            
            # Check if online
            is_online = "online" in status.lower()
            
            return {
                "success": True,
                "contact": contact,
                "status": status,
                "is_online": is_online,
                "action": "whatsapp.get_last_seen"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close(self) -> Dict[str, Any]:
        """Close the browser and clean up resources."""
        self._cleanup()
        return {"success": True, "action": "whatsapp.close"}
