"""
Observer - Continuous Observation Layer for Self-Learning JARVIS.

This module captures everything about the user's computer activity:
- Active window/app
- Window titles
- Idle time
- Activity level

All observations are stored in SQLite for later analysis by the Analyst.
The key insight: we're not defining rules. We're collecting data that
the LLM will use to discover its own patterns.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class Observation:
    """A single moment of observation."""
    timestamp: datetime
    active_app: str
    window_title: str
    idle_seconds: float
    activity_level: str  # "active", "idle", "away"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "active_app": self.active_app,
            "window_title": self.window_title,
            "idle_seconds": self.idle_seconds,
            "activity_level": self.activity_level,
        }


class ObservationStore:
    """SQLite storage for observations."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path.home() / ".kayas" / "observations.db")
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    active_app TEXT,
                    window_title TEXT,
                    idle_seconds REAL,
                    activity_level TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_obs_timestamp 
                ON observations(timestamp)
            """)
            
            # User model storage
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_model (
                    id INTEGER PRIMARY KEY,
                    model_yaml TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Intervention tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interventions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    message TEXT,
                    reason TEXT,
                    user_response TEXT,
                    outcome TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def store(self, obs: Observation):
        """Store a single observation."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO observations 
                (timestamp, active_app, window_title, idle_seconds, activity_level)
                VALUES (?, ?, ?, ?, ?)
            """, (
                obs.timestamp.isoformat(),
                obs.active_app,
                obs.window_title,
                obs.idle_seconds,
                obs.activity_level,
            ))
            conn.commit()
    
    def get_recent(self, minutes: int = 60) -> list:
        """Get observations from the last N minutes."""
        cutoff = datetime.now().timestamp() - (minutes * 60)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM observations 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (cutoff_iso,)).fetchall()
            return [dict(row) for row in rows]
    
    def get_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Get a summary of recent activity with rich context."""
        observations = self.get_recent(minutes)
        if not observations:
            return {"total_observations": 0}
        
        # Count time per app
        app_time = {}
        for obs in observations:
            app = obs.get("active_app", "unknown")
            app_time[app] = app_time.get(app, 0) + 1
        
        # Convert to minutes (assuming 30s intervals)
        app_minutes = {k: round(v * 0.5, 1) for k, v in app_time.items()}
        
        # Dominant app
        dominant_app = max(app_time.keys(), key=lambda k: app_time[k]) if app_time else None
        
        # Activity breakdown
        activity_counts = {}
        for obs in observations:
            level = obs.get("activity_level", "unknown")
            activity_counts[level] = activity_counts.get(level, 0) + 1
        
        # DEEP CONTEXT: Recent window titles (what they're actually doing)
        recent_titles = []
        seen_titles = set()
        for obs in observations[:20]:  # Last 20 observations (10 min)
            title = obs.get("window_title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                recent_titles.append(title[:100])  # Truncate long titles
                if len(recent_titles) >= 5:  # Keep top 5 unique titles
                    break
        
        # Extract topics from titles for richer context
        topics = self._extract_topics(recent_titles)
        
        return {
            "total_observations": len(observations),
            "time_span_minutes": minutes,
            "app_usage_minutes": app_minutes,
            "dominant_app": dominant_app,
            "activity_breakdown": activity_counts,
            "recent_window_titles": recent_titles,
            "detected_topics": topics,
        }
    
    def _extract_topics(self, titles: list) -> list:
        """Extract meaningful topics from window titles."""
        topics = []
        keywords = []
        
        for title in titles:
            title_lower = title.lower()
            
            # Programming/coding
            if any(x in title_lower for x in ['python', 'javascript', 'react', 'node', 'api', 'code', 'github', 'stackoverflow']):
                if 'coding' not in topics:
                    topics.append('coding')
            
            # Research/docs
            if any(x in title_lower for x in ['documentation', 'docs', 'guide', 'tutorial', 'how to', 'learn']):
                if 'researching' not in topics:
                    topics.append('researching')
            
            # Video/entertainment
            if any(x in title_lower for x in ['youtube', 'netflix', 'video', 'watch']):
                if 'watching videos' not in topics:
                    topics.append('watching videos')
            
            # Social
            if any(x in title_lower for x in ['twitter', 'reddit', 'discord', 'slack', 'whatsapp']):
                if 'social/messaging' not in topics:
                    topics.append('social/messaging')
            
            # Email
            if any(x in title_lower for x in ['gmail', 'outlook', 'mail', 'inbox']):
                if 'email' not in topics:
                    topics.append('email')
            
            # AI/ML
            if any(x in title_lower for x in ['openai', 'langchain', 'llm', 'gpt', 'claude', 'gemini', 'ai', 'machine learning']):
                if 'AI/ML work' not in topics:
                    topics.append('AI/ML work')
        
        return topics
    
    def cleanup_old(self, days: int = 7):
        """Remove observations older than N days."""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM observations WHERE timestamp < ?", (cutoff_iso,))
            conn.commit()


class Observer:
    """
    Continuous observation thread with vision capabilities.
    
    Runs in the background, capturing the user's activity every 30 seconds.
    Uses SMART TRIGGERING for vision: only analyzes when context changes
    or enough time has passed, and skips when user is idle.
    """
    
    def __init__(self, store: ObservationStore = None, interval_seconds: int = 30, vision_llm=None):
        self.store = store or ObservationStore()
        self.interval = interval_seconds
        
        # Vision capabilities for deep screen understanding
        self.vision_llm = vision_llm
        self.vision_interval = 300  # Max time between analyses (5 min)
        self.vision_min_interval = 180  # Min time between analyses (3 min) - prevents backlog
        self._last_vision_time = 0
        self._last_screen_context = ""  # Cached vision description
        
        # Smart triggering: track context for change detection
        self._last_vision_app = ""  # Last app when vision ran
        self._last_vision_title = ""  # Last window title when vision ran
        self.idle_threshold = 120  # Skip vision if idle > 2 minutes
        
        # Control
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Last activity tracking for idle detection
        self._last_mouse_pos = None
        self._last_activity_time = time.time()
    
    def start(self):
        """Start the observation thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._observe_loop, daemon=True)
        self._thread.start()
        print("[Observer] Started continuous observation")
    
    def stop(self):
        """Stop the observation thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        print("[Observer] Stopped")
    
    def _observe_loop(self):
        """Main observation loop with SMART vision triggering."""
        while self._running:
            try:
                obs = self._capture()
                self.store.store(obs)
                
                # Smart vision triggering
                if self.vision_llm:
                    self._smart_vision_trigger(obs)
                        
            except Exception as e:
                # Don't crash on errors - observation should be resilient
                pass
            
            time.sleep(self.interval)
    
    def _smart_vision_trigger(self, obs: Observation):
        """
        Smart triggering for vision analysis:
        - Skip if user is idle (saves API calls)
        - Trigger immediately if app/context changed significantly
        - Otherwise wait for max interval
        """
        now = time.time()
        time_since_last = now - self._last_vision_time
        
        # Skip if user is idle/away
        if obs.activity_level in ("idle", "away") or obs.idle_seconds > self.idle_threshold:
            return
        
        # Check if context changed significantly
        context_changed = False
        current_app = obs.active_app
        current_title = obs.window_title
        
        # Significant change: different app entirely
        if current_app != self._last_vision_app and self._last_vision_app:
            context_changed = True
        
        # Significant change: very different title (different page/document)
        if self._last_vision_title and current_title:
            # Simple heuristic: if first 20 chars are different, it's a new context
            if current_title[:20].lower() != self._last_vision_title[:20].lower():
                context_changed = True
        
        # Decide whether to trigger
        should_trigger = False
        
        if context_changed and time_since_last >= self.vision_min_interval:
            # Context changed and min interval passed
            should_trigger = True
            print(f"[Observer] Vision trigger: context changed ({self._last_vision_app} → {current_app})")
        elif time_since_last >= self.vision_interval:
            # Max interval reached
            should_trigger = True
        
        if should_trigger:
            self._analyze_screen()
            self._last_vision_time = now
            self._last_vision_app = current_app
            self._last_vision_title = current_title
    
    def _capture(self) -> Observation:
        """Capture current state."""
        now = datetime.now()
        
        # Get active window
        active_app = "unknown"
        window_title = ""
        try:
            import pygetwindow as gw
            active = gw.getActiveWindow()
            if active:
                window_title = active.title or ""
                # Extract app name from title or process
                active_app = self._extract_app_name(window_title)
        except Exception:
            pass
        
        # Calculate idle time
        idle_seconds = 0
        try:
            import pyautogui
            current_pos = pyautogui.position()
            if self._last_mouse_pos == current_pos:
                idle_seconds = time.time() - self._last_activity_time
            else:
                self._last_mouse_pos = current_pos
                self._last_activity_time = time.time()
                idle_seconds = 0
        except Exception:
            pass
        
        # Determine activity level
        if idle_seconds > 300:  # 5 min
            activity_level = "away"
        elif idle_seconds > 60:  # 1 min
            activity_level = "idle"
        else:
            activity_level = "active"
        
        return Observation(
            timestamp=now,
            active_app=active_app,
            window_title=window_title[:200],  # Truncate long titles
            idle_seconds=idle_seconds,
            activity_level=activity_level,
        )
    
    def _extract_app_name(self, title: str) -> str:
        """Extract application name from window title."""
        title_lower = title.lower()
        
        # Common patterns
        if "visual studio code" in title_lower or "- code" in title_lower:
            return "vscode"
        if "chrome" in title_lower:
            return "chrome"
        if "firefox" in title_lower:
            return "firefox"
        if "youtube" in title_lower:
            return "youtube"
        if "discord" in title_lower:
            return "discord"
        if "slack" in title_lower:
            return "slack"
        if "spotify" in title_lower:
            return "spotify"
        if "terminal" in title_lower or "powershell" in title_lower or "cmd" in title_lower:
            return "terminal"
        if "explorer" in title_lower:
            return "explorer"
        if "word" in title_lower:
            return "word"
        if "excel" in title_lower:
            return "excel"
        if "notion" in title_lower:
            return "notion"
        if "twitter" in title_lower or "x.com" in title_lower:
            return "twitter"
        if "reddit" in title_lower:
            return "reddit"
        
        # Fallback: first word or unknown
        parts = title.split(" - ")
        if len(parts) > 1:
            return parts[-1].strip().lower()[:20]
        
        return title[:20].lower() if title else "unknown"
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current observation without storing."""
        obs = self._capture()
        return obs.to_dict()
    
    def _analyze_screen(self):
        """
        Capture and analyze screen with vision model.
        Runs in a BACKGROUND THREAD so it doesn't block observation.
        """
        if not self.vision_llm:
            return
        
        # Skip if already analyzing (prevents backlog)
        if getattr(self, '_vision_in_progress', False):
            return
        
        # Run in background thread
        def _async_analyze():
            self._vision_in_progress = True
            try:
                import pyautogui
                from PIL import Image
                from pathlib import Path
                import tempfile
                
                # Capture screenshot
                screenshot = pyautogui.screenshot()
                
                # Resize smaller for faster upload (720p is enough)
                max_size = 720  # Reduced from 1280 for faster processing
                if screenshot.width > max_size or screenshot.height > max_size:
                    ratio = min(max_size / screenshot.width, max_size / screenshot.height)
                    new_size = (int(screenshot.width * ratio), int(screenshot.height * ratio))
                    screenshot = screenshot.resize(new_size, Image.Resampling.LANCZOS)
                
                # Save temporarily (use JPEG for smaller size)
                temp_path = Path(tempfile.gettempdir()) / "kayas_screen.jpg"
                screenshot.save(temp_path, "JPEG", quality=70)
                
                # Analyze with vision model (this is the slow part)
                description = self.vision_llm.analyze_activity(str(temp_path))
                
                if description:
                    self._last_screen_context = description
                    print(f"[Observer] Vision: {description[:100]}...")
                
                # Privacy: delete screenshot immediately
                temp_path.unlink(missing_ok=True)
                
            except Exception as e:
                # Vision is optional - don't crash if it fails
                pass
            finally:
                self._vision_in_progress = False
        
        # Start background thread
        vision_thread = threading.Thread(target=_async_analyze, daemon=True)
        vision_thread.start()
    
    def get_screen_context(self) -> str:
        """Get the last vision analysis result."""
        return self._last_screen_context


# Convenience function
def start_observer(vision_llm=None) -> Observer:
    """Start and return an Observer instance."""
    obs = Observer(vision_llm=vision_llm)
    obs.start()
    return obs
