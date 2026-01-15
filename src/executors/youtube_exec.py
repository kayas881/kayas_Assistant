"""
YouTube Browser Automation Executor

Provides real browser automation for YouTube - search, play, browse subscriptions,
check for new uploads, and more. Uses your existing YouTube login via session cookies.

This is NOT an API wrapper - it controls the actual browser like a real user.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import time
import json
import re

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


@dataclass
class YouTubeConfig:
    """Configuration for YouTube automation."""
    headless: bool = False  # Usually want to see YouTube
    timeout_ms: int = 15000
    viewport_width: int = 1280
    viewport_height: int = 800
    session_name: str = "youtube"  # Persists login across sessions


# YouTube CSS Selectors (may need updates if YouTube changes)
class YouTubeSelectors:
    """CSS selectors for YouTube elements."""
    # Search
    SEARCH_INPUT = 'input#search, input[name="search_query"], ytd-searchbox input'
    SEARCH_BUTTON = 'button#search-icon-legacy, #search-icon-legacy'
    
    # Video elements (search results page)
    VIDEO_RENDERER = 'ytd-video-renderer, ytd-rich-item-renderer'
    VIDEO_TITLE = '#video-title, a#video-title, h3 a#video-title, #title-wrapper #video-title'
    VIDEO_CHANNEL = '#channel-name a, #text.ytd-channel-name a, ytd-channel-name a, #channel-info a'
    VIDEO_VIEWS = '#metadata-line span:first-child, #metadata span:first-child'
    VIDEO_TIME = 'ytd-thumbnail-overlay-time-status-renderer, span.ytd-thumbnail-overlay-time-status-renderer, #time-status'
    VIDEO_THUMBNAIL = 'a#thumbnail, ytd-thumbnail a'
    
    # Player
    PLAYER = '#movie_player'
    PLAY_BUTTON = '.ytp-play-button'
    VIDEO_PLAYING = '.ytp-play-button[data-title-no-tooltip="Pause"]'
    
    # Navigation
    HOME_BUTTON = 'a[title="Home"], #logo'
    SUBSCRIPTIONS_TAB = 'a[title="Subscriptions"], a[href="/feed/subscriptions"]'
    SUBSCRIPTION_VIDEOS = 'ytd-grid-video-renderer, ytd-video-renderer, ytd-rich-item-renderer'
    
    # Channel page
    CHANNEL_VIDEOS_TAB = 'yt-tab-shape[tab-title="Videos"], tp-yt-paper-tab:has-text("Videos")'
    CHANNEL_NAME = '#channel-name, #text.ytd-channel-name'
    
    # Notifications / New uploads indicator
    NEW_BADGE = 'ytd-badge-supported-renderer'
    
    # Like/Subscribe (for future)
    LIKE_BUTTON = '#top-level-buttons-computed button:first-child, like-button-view-model button'
    SUBSCRIBE_BUTTON = '#subscribe-button button, ytd-subscribe-button-renderer button'


class YouTubeExecutor:
    """
    YouTube browser automation executor.
    
    Provides natural-language-friendly methods for interacting with YouTube
    as a real user would.
    """
    
    def __init__(self, config: YouTubeConfig = None):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright required. Install with: pip install playwright && python -m playwright install")
        
        self.config = config or YouTubeConfig()
        self._sessions_dir = Path('.agent') / 'browser_sessions'
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self._sessions_dir / f"{self.config.session_name}.json"
        
        # Playwright instances (managed per-call for now)
        self._playwright = None
        self._browser = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
    
    def _ensure_browser(self) -> Page:
        """Ensure browser is running and return the page."""
        if self._page is not None:
            return self._page
        
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.config.headless)
        
        # Load session if exists
        context_kwargs = {
            "viewport": {"width": self.config.viewport_width, "height": self.config.viewport_height},
        }
        
        if self._state_file.exists():
            try:
                context_kwargs["storage_state"] = str(self._state_file)
            except Exception:
                pass
        
        self._context = self._browser.new_context(**context_kwargs)
        self._context.set_default_timeout(self.config.timeout_ms)
        self._page = self._context.new_page()
        
        return self._page
    
    def _save_session(self):
        """Save browser session (cookies, localStorage) for future use."""
        if self._context:
            try:
                self._context.storage_state(path=str(self._state_file))
            except Exception:
                pass
    
    def close(self):
        """Close browser and save session."""
        self._save_session()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
    
    def _wait_for_page_load(self, page: Page, timeout_ms: int = 5000):
        """Wait for YouTube to finish loading."""
        try:
            page.wait_for_load_state("networkidle", timeout=timeout_ms)
        except:
            pass  # Best effort
    
    def _extract_video_info(self, element) -> Dict[str, Any]:
        """Extract video information from a video element."""
        try:
            title_el = element.query_selector(YouTubeSelectors.VIDEO_TITLE)
            title = title_el.inner_text() if title_el else "Unknown"
            
            link_el = element.query_selector('a#thumbnail, a#video-title')
            url = ""
            if link_el:
                href = link_el.get_attribute('href')
                if href:
                    url = f"https://www.youtube.com{href}" if href.startswith('/') else href
            
            channel_el = element.query_selector(YouTubeSelectors.VIDEO_CHANNEL)
            channel = channel_el.inner_text() if channel_el else "Unknown"
            
            views_el = element.query_selector(YouTubeSelectors.VIDEO_VIEWS)
            views = views_el.inner_text() if views_el else ""
            
            duration_el = element.query_selector(YouTubeSelectors.VIDEO_TIME)
            duration = duration_el.inner_text() if duration_el else ""
            
            return {
                "title": title.strip(),
                "channel": channel.strip(),
                "url": url,
                "views": views.strip(),
                "duration": duration.strip(),
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ==================== Public Methods ====================
    
    def open_youtube(self) -> Dict[str, Any]:
        """Open YouTube homepage."""
        try:
            page = self._ensure_browser()
            page.goto("https://www.youtube.com")
            self._wait_for_page_load(page)
            self._save_session()
            
            return {
                "success": True,
                "message": "YouTube opened",
                "logged_in": self._check_logged_in(page)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _check_logged_in(self, page: Page) -> bool:
        """Check if user is logged into YouTube."""
        try:
            # Look for avatar button (signed in) vs Sign In button
            avatar = page.query_selector('button#avatar-btn, #avatar-btn')
            return avatar is not None
        except:
            return False
    
    def search(self, query: str, play_first: bool = False) -> Dict[str, Any]:
        """
        Search YouTube for videos.
        
        Args:
            query: Search query
            play_first: If True, automatically play the first result
        
        Returns:
            Search results with video info
        """
        try:
            page = self._ensure_browser()
            page.goto("https://www.youtube.com")
            self._wait_for_page_load(page)
            
            # Find and fill search box
            search_input = page.wait_for_selector(YouTubeSelectors.SEARCH_INPUT)
            search_input.fill(query)
            search_input.press("Enter")
            
            # Wait for results to load
            time.sleep(2)  # Give YouTube time to load results
            self._wait_for_page_load(page)
            
            # Try to extract results (best effort - may fail if YouTube changes)
            video_elements = page.query_selector_all(YouTubeSelectors.VIDEO_RENDERER)[:10]
            results = []
            for el in video_elements:
                info = self._extract_video_info(el)
                if info.get("title") and not info.get("error"):
                    results.append(info)
            
            # Play first if requested and we found clickable elements
            if play_first and video_elements:
                first_video = video_elements[0]
                thumbnail = first_video.query_selector(YouTubeSelectors.VIDEO_THUMBNAIL)
                if thumbnail:
                    thumbnail.click()
                    self._wait_for_page_load(page)
                    time.sleep(1)
                    
                    # Try to get the title from the video page
                    try:
                        title_el = page.query_selector('h1.ytd-watch-metadata yt-formatted-string, h1 yt-formatted-string')
                        video_title = title_el.inner_text() if title_el else results[0].get('title', 'video') if results else 'video'
                    except:
                        video_title = results[0].get('title', 'video') if results else 'video'
                    
                    return {
                        "success": True,
                        "action": "playing",
                        "title": video_title,
                        "message": f"Now playing: {video_title}"
                    }
            
            self._save_session()
            
            # Always return success if we got to the search page
            # The user can see results in the browser even if extraction failed
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results),
                "message": f"Searched YouTube for '{query}'. {'Found ' + str(len(results)) + ' videos.' if results else 'Results are showing in the browser - pick one!'}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def play_video(self, url: str = None, title: str = None) -> Dict[str, Any]:
        """
        Play a specific video by URL or search and play by title.
        
        Args:
            url: Direct YouTube video URL
            title: Video title to search for
        """
        try:
            page = self._ensure_browser()
            
            if url:
                page.goto(url)
                self._wait_for_page_load(page)
                
                # Get video title
                title_el = page.query_selector('h1.ytd-video-primary-info-renderer, h1.ytd-watch-metadata yt-formatted-string')
                video_title = title_el.inner_text() if title_el else "Unknown"
                
                self._save_session()
                return {
                    "success": True,
                    "action": "playing",
                    "title": video_title,
                    "url": url
                }
            elif title:
                return self.search(title, play_first=True)
            else:
                return {"success": False, "error": "Need either url or title"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_channel(self, channel_name: str, play_latest: bool = False) -> Dict[str, Any]:
        """
        Check a channel for their latest videos.
        
        Args:
            channel_name: Name of the channel to check
            play_latest: If True, play their most recent video
        """
        try:
            page = self._ensure_browser()
            
            # Search for the channel
            page.goto(f"https://www.youtube.com/results?search_query={channel_name}")
            self._wait_for_page_load(page)
            time.sleep(1)
            
            # Look for channel link and click it
            channel_link = page.query_selector('a#main-link.channel-link, ytd-channel-renderer a#main-link')
            if not channel_link:
                # Try finding channel in regular results
                channel_link = page.query_selector(f'a[href*="/@"]:has-text("{channel_name}")')
            
            if channel_link:
                channel_link.click()
                self._wait_for_page_load(page)
                time.sleep(1)
            else:
                return {"success": False, "error": f"Channel '{channel_name}' not found"}
            
            # Try clicking Videos tab
            try:
                videos_tab = page.query_selector('yt-tab-shape[tab-title="Videos"]')
                if videos_tab:
                    videos_tab.click()
                    time.sleep(1)
            except:
                pass
            
            # Get latest videos
            video_elements = page.query_selector_all('ytd-rich-item-renderer, ytd-grid-video-renderer')[:5]
            videos = []
            for el in video_elements:
                info = self._extract_video_info(el)
                if info.get("title"):
                    videos.append(info)
            
            result = {
                "success": True,
                "channel": channel_name,
                "latest_videos": videos,
            }
            
            # Play latest if requested
            if play_latest and video_elements:
                thumbnail = video_elements[0].query_selector('a#thumbnail')
                if thumbnail:
                    thumbnail.click()
                    self._wait_for_page_load(page)
                    result["action"] = "playing"
                    result["now_playing"] = videos[0] if videos else None
                    result["message"] = f"Playing latest from {channel_name}"
            
            self._save_session()
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_subscriptions(self, limit: int = 10) -> Dict[str, Any]:
        """
        Check subscriptions feed for new videos.
        
        Returns videos from channels you're subscribed to.
        """
        try:
            page = self._ensure_browser()
            page.goto("https://www.youtube.com/feed/subscriptions")
            self._wait_for_page_load(page)
            time.sleep(1)
            
            if not self._check_logged_in(page):
                return {
                    "success": False,
                    "error": "Not logged in. Please open YouTube and sign in first."
                }
            
            # Get subscription videos
            video_elements = page.query_selector_all('ytd-rich-item-renderer, ytd-grid-video-renderer')[:limit]
            videos = []
            for el in video_elements:
                info = self._extract_video_info(el)
                if info.get("title"):
                    videos.append(info)
            
            self._save_session()
            return {
                "success": True,
                "source": "subscriptions",
                "videos": videos,
                "count": len(videos)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_recommendations(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get YouTube's recommended videos for you.
        """
        try:
            page = self._ensure_browser()
            page.goto("https://www.youtube.com")
            self._wait_for_page_load(page)
            time.sleep(1)
            
            video_elements = page.query_selector_all('ytd-rich-item-renderer')[:limit]
            videos = []
            for el in video_elements:
                info = self._extract_video_info(el)
                if info.get("title"):
                    videos.append(info)
            
            self._save_session()
            return {
                "success": True,
                "source": "recommendations",
                "videos": videos,
                "count": len(videos)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def play_from_subscriptions(self, channel_filter: str = None) -> Dict[str, Any]:
        """
        Play a video from subscriptions.
        
        Args:
            channel_filter: Optional - only play from this channel
        """
        try:
            subs = self.check_subscriptions(limit=20)
            if not subs.get("success"):
                return subs
            
            videos = subs.get("videos", [])
            if not videos:
                return {"success": False, "error": "No subscription videos found"}
            
            # Filter by channel if specified
            if channel_filter:
                channel_filter_lower = channel_filter.lower()
                videos = [v for v in videos if channel_filter_lower in v.get("channel", "").lower()]
                if not videos:
                    return {"success": False, "error": f"No videos from '{channel_filter}' in subscriptions"}
            
            # Play first match
            video = videos[0]
            if video.get("url"):
                return self.play_video(url=video["url"])
            
            return {"success": False, "error": "Could not find video URL"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def control_playback(self, action: str) -> Dict[str, Any]:
        """
        Control video playback.
        
        Args:
            action: One of 'play', 'pause', 'fullscreen', 'mute', 'unmute'
        """
        try:
            if not self._page:
                return {"success": False, "error": "No video open. Play a video first."}
            
            page = self._page
            
            if action == "play":
                page.keyboard.press("k")  # YouTube shortcut
            elif action == "pause":
                page.keyboard.press("k")
            elif action == "fullscreen":
                page.keyboard.press("f")
            elif action == "mute":
                page.keyboard.press("m")
            elif action == "unmute":
                page.keyboard.press("m")
            elif action == "next":
                page.keyboard.press("Shift+n")
            elif action == "previous":
                page.keyboard.press("Shift+p")
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
            
            return {"success": True, "action": action}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def like_video(self) -> Dict[str, Any]:
        """Like the currently playing video."""
        try:
            if not self._page:
                return {"success": False, "error": "No video open"}
            
            page = self._page
            like_btn = page.query_selector(YouTubeSelectors.LIKE_BUTTON)
            if like_btn:
                like_btn.click()
                return {"success": True, "action": "liked"}
            return {"success": False, "error": "Like button not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance for easy access
_youtube_instance: Optional[YouTubeExecutor] = None

def get_youtube_executor() -> YouTubeExecutor:
    """Get or create the YouTube executor singleton."""
    global _youtube_instance
    if _youtube_instance is None:
        _youtube_instance = YouTubeExecutor()
    return _youtube_instance
