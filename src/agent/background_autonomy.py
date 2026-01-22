"""
Background Autonomy - Proactive agent that monitors and suggests.

This enables KAYAS to:
- Monitor the environment (screen, time, calendar, emails)
- Track persistent goals
- Make proactive suggestions without being asked
- Learn patterns and anticipate needs

The key insight: a true assistant doesn't just respond - it notices things
and speaks up when relevant.
"""
from __future__ import annotations

import threading
import time
import queue
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path


@dataclass
class Goal:
    """A persistent goal the agent is tracking."""
    
    id: str
    description: str
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    priority: int = 5  # 1-10, higher = more important
    status: str = "active"  # active, completed, abandoned
    check_interval_minutes: int = 30
    last_checked: Optional[datetime] = None
    
    def is_due_for_check(self) -> bool:
        if not self.last_checked:
            return True
        elapsed = datetime.now() - self.last_checked
        return elapsed.total_seconds() > (self.check_interval_minutes * 60)


@dataclass
class Signal:
    """A signal from the environment that might need attention."""
    
    source: str  # "calendar", "screen", "time", "email", "pattern"
    message: str
    priority: int = 5  # 1-10
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at


class BackgroundMonitor:
    """
    Monitors the environment and generates signals for the agent.
    
    This runs in a background thread and periodically checks:
    - Screen activity (what app is focused, how long)
    - Time patterns (breaks, sleep reminders)
    - Calendar events (upcoming meetings)
    - Persistent goals (deadlines, check-ins)
    """
    
    def __init__(
        self,
        screen_perceiver=None,
        calendar_exec=None,
        profile_manager=None,
        check_interval_seconds: int = 60,
    ):
        self.screen_perceiver = screen_perceiver
        self.calendar_exec = calendar_exec
        self.profile_manager = profile_manager
        self.check_interval = check_interval_seconds
        
        # Signal queue - agent polls this for proactive interventions
        self.signal_queue: queue.Queue[Signal] = queue.Queue()
        
        # Goals being tracked
        self.goals: Dict[str, Goal] = {}
        
        # Pattern tracking
        self.screen_history: List[Dict[str, Any]] = []
        self.last_interaction: Optional[datetime] = None
        self.session_start: datetime = datetime.now()
        self._first_check_done = False  # For initial proactive message
        
        # Control
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the background monitoring thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print("[BackgroundMonitor] Started monitoring")
    
    def stop(self):
        """Stop the background monitoring thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        print("[BackgroundMonitor] Stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop - runs in background thread."""
        while self._running:
            try:
                self._check_time_patterns()
                self._check_screen_activity()
                self._check_goals()
                self._check_calendar()
            except Exception as e:
                # Don't crash the monitor on errors
                pass
            
            time.sleep(self.check_interval)
    
    def _check_time_patterns(self):
        """Generate time-based signals (breaks, sleep, greetings, etc)."""
        now = datetime.now()
        hour = now.hour
        
        # Late night warning (11pm - 5am)
        if hour >= 23 or hour < 5:
            self._emit_signal(Signal(
                source="time",
                message="It's quite late. Consider wrapping up for the night.",
                priority=7,
                expires_at=now + timedelta(hours=1),
            ))
        
        # Afternoon focus check (2-4pm - common energy dip)
        elif 14 <= hour < 16:
            session_duration = now - self.session_start
            if session_duration.total_seconds() > 60 * 60:  # 1+ hour session
                self._emit_signal(Signal(
                    source="time",
                    message="Afternoon energy dip time - maybe grab some water or stretch?",
                    priority=5,
                    expires_at=now + timedelta(hours=1),
                ))
        
        # Initial check-in (after 2 minutes of session)
        session_duration = now - self.session_start
        if not self._first_check_done and session_duration.total_seconds() > 120:
            self._first_check_done = True
            self._emit_signal(Signal(
                source="time",
                message="Still here if you need anything! Just say the word.",
                priority=5,
                expires_at=now + timedelta(minutes=10),
            ))
        
        # Work session length (2+ hours)
        session_duration = now - self.session_start
        if session_duration.total_seconds() > 2 * 60 * 60:  # 2 hours
            if self.last_interaction:
                time_since_break = now - self.last_interaction
                if time_since_break.total_seconds() < 30 * 60:  # Active in last 30 min
                    self._emit_signal(Signal(
                        source="time",
                        message="You've been working for a while. Maybe take a short break?",
                        priority=5,
                        expires_at=now + timedelta(minutes=30),
                    ))
    
    def _check_screen_activity(self):
        """Monitor what apps are being used and for how long."""
        if not self.screen_perceiver:
            return
        
        try:
            state = self.screen_perceiver.get_current_state()
            active_app = state.get("active_window", "")
            
            # Track history
            self.screen_history.append({
                "app": active_app,
                "timestamp": datetime.now(),
            })
            
            # Keep last 100 entries
            if len(self.screen_history) > 100:
                self.screen_history = self.screen_history[-100:]
            
            # Detect prolonged social media use
            social_apps = ["youtube", "twitter", "instagram", "tiktok", "reddit"]
            if any(app in active_app.lower() for app in social_apps):
                # Count how long they've been on social media
                social_time = self._count_recent_app_time(social_apps, minutes=30)
                if social_time > 20:  # More than 20 minutes in last 30
                    self._emit_signal(Signal(
                        source="screen",
                        message=f"You've been browsing for about {social_time} minutes. Want to get back to something else?",
                        priority=4,
                        expires_at=datetime.now() + timedelta(minutes=15),
                    ))
        except Exception:
            pass
    
    def _count_recent_app_time(self, app_keywords: List[str], minutes: int) -> int:
        """Count minutes spent on apps matching keywords in recent history."""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        count = 0
        
        for entry in self.screen_history:
            if entry["timestamp"] < cutoff:
                continue
            app = entry.get("app", "").lower()
            if any(kw in app for kw in app_keywords):
                count += 1  # Each entry is roughly 1 minute (check_interval)
        
        return count
    
    def _check_goals(self):
        """Check on persistent goals and remind about deadlines."""
        now = datetime.now()
        
        for goal_id, goal in self.goals.items():
            if goal.status != "active":
                continue
            
            # Deadline approaching
            if goal.deadline:
                time_left = goal.deadline - now
                if time_left.total_seconds() < 60 * 60 * 24:  # Less than 24 hours
                    self._emit_signal(Signal(
                        source="goal",
                        message=f"Reminder: '{goal.description}' is due soon.",
                        priority=goal.priority,
                        context={"goal_id": goal_id},
                    ))
            
            # Periodic check-in
            if goal.is_due_for_check():
                goal.last_checked = now
                self._emit_signal(Signal(
                    source="goal",
                    message=f"How's '{goal.description}' going?",
                    priority=max(3, goal.priority - 2),
                    context={"goal_id": goal_id},
                ))
    
    def _check_calendar(self):
        """Check for upcoming calendar events."""
        if not self.calendar_exec:
            return
        
        try:
            # This would integrate with calendar_exec to get upcoming events
            # For now, placeholder
            pass
        except Exception:
            pass
    
    def _emit_signal(self, signal: Signal):
        """Add a signal to the queue if not duplicate."""
        # Simple duplicate prevention - check if similar signal exists
        try:
            # Non-blocking check of recent signals
            recent = []
            while True:
                try:
                    s = self.signal_queue.get_nowait()
                    if not s.is_expired():
                        recent.append(s)
                except queue.Empty:
                    break
            
            # Put back non-expired signals
            for s in recent:
                self.signal_queue.put(s)
            
            # Check for duplicates
            is_duplicate = any(
                s.source == signal.source and s.message == signal.message
                for s in recent
            )
            
            if not is_duplicate:
                self.signal_queue.put(signal)
        except Exception:
            self.signal_queue.put(signal)
    
    def get_pending_signals(self) -> List[Signal]:
        """Get all pending signals (called by agent)."""
        signals = []
        while True:
            try:
                signal = self.signal_queue.get_nowait()
                if not signal.is_expired():
                    signals.append(signal)
            except queue.Empty:
                break
        return signals
    
    def add_goal(self, description: str, deadline: datetime = None, priority: int = 5) -> str:
        """Add a persistent goal to track."""
        import uuid
        goal_id = str(uuid.uuid4())[:8]
        self.goals[goal_id] = Goal(
            id=goal_id,
            description=description,
            deadline=deadline,
            priority=priority,
        )
        return goal_id
    
    def complete_goal(self, goal_id: str):
        """Mark a goal as completed."""
        if goal_id in self.goals:
            self.goals[goal_id].status = "completed"
    
    def record_interaction(self):
        """Record that an interaction just happened (for break tracking)."""
        self.last_interaction = datetime.now()


class ProactiveEngine:
    """
    Decides when and how to make proactive suggestions.
    
    This bridges the BackgroundMonitor signals with the CognitiveAgent's
    response generation. It decides:
    - Should we interrupt the user?
    - How urgent is this?
    - What's the best way to phrase it?
    """
    
    def __init__(self, llm=None, background_monitor: BackgroundMonitor = None):
        self.llm = llm
        self.monitor = background_monitor
        
        # Intervention settings
        self.min_priority_to_interrupt = 5  # Lower threshold - priority >= 5 can interrupt
        self.last_proactive_message: Optional[datetime] = None
        self.cooldown_minutes = 5  # Reduced cooldown for more responsiveness
    
    def should_intervene(self) -> Optional[str]:
        """
        Check if we should make a proactive intervention.
        
        Returns a suggestion message if we should, None otherwise.
        """
        if not self.monitor:
            return None
        
        # Respect cooldown
        if self.last_proactive_message:
            elapsed = datetime.now() - self.last_proactive_message
            if elapsed.total_seconds() < self.cooldown_minutes * 60:
                return None
        
        # Get pending signals
        signals = self.monitor.get_pending_signals()
        if not signals:
            return None
        
        # Filter by priority
        urgent_signals = [s for s in signals if s.priority >= self.min_priority_to_interrupt]
        if not urgent_signals:
            # Put lower priority signals back (they might become relevant later)
            for s in signals:
                self.monitor.signal_queue.put(s)
            return None
        
        # Pick highest priority signal
        best_signal = max(urgent_signals, key=lambda s: s.priority)
        
        # Generate natural message using LLM if available
        if self.llm:
            return self._generate_proactive_message(best_signal)
        else:
            self.last_proactive_message = datetime.now()
            return best_signal.message
    
    def _generate_proactive_message(self, signal: Signal) -> str:
        """Use LLM to make the proactive message feel natural."""
        prompt = f"""You are Kayas, a caring AI assistant. 
You noticed something and want to gently mention it to the user.

What you noticed: {signal.message}
Priority: {"high" if signal.priority >= 7 else "medium"}
Context: {signal.context}

Generate a brief, friendly message. Be natural - don't sound like an alarm.
Examples of good phrasing:
- "Hey, quick thought..."
- "Just noticed..."
- "Not to interrupt, but..."

Keep it to 1-2 sentences max. Don't be preachy."""

        try:
            response = self.llm.generate(prompt=prompt, temperature=0.8, max_tokens=100)
            self.last_proactive_message = datetime.now()
            
            # Strip thinking tags if present (vLLM/Qwen3 outputs these)
            import re
            response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
            response = re.sub(r'<think>.*', '', response, flags=re.DOTALL).strip()
            
            return response if response else signal.message
        except Exception:
            self.last_proactive_message = datetime.now()
            return signal.message
    
    def get_context_for_response(self) -> List[str]:
        """
        Get low-priority signals to include as context in responses.
        
        These don't warrant interruption but can be woven into
        responses when the user is already talking.
        """
        if not self.monitor:
            return []
        
        signals = self.monitor.get_pending_signals()
        low_priority = [s for s in signals if s.priority < self.min_priority_to_interrupt]
        
        # Put back in queue (they'll be used as context)
        for s in low_priority:
            self.monitor.signal_queue.put(s)
        
        return [s.message for s in low_priority[:3]]  # Max 3 context items
