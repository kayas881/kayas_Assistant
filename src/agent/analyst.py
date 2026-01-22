"""
Analyst - The Brain of Self-Learning JARVIS.

This module does the intelligent work:
1. Periodically analyzes observation data
2. Builds and updates the user model
3. Decides when to intervene using LLM reasoning
4. Tracks intervention success/failure

The key insight: NO HARDCODED RULES. The LLM decides everything based
on the observation data and user model.
"""
from __future__ import annotations

import threading
import time
import yaml
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path


@dataclass
class UserModel:
    """A living model of the user that grows over time."""
    
    # Schedule patterns
    typical_start_time: str = ""
    typical_end_time: str = ""
    break_patterns: List[str] = field(default_factory=list)
    
    # App usage patterns
    primary_work_apps: List[str] = field(default_factory=list)
    distraction_apps: List[str] = field(default_factory=list)
    
    # Communication preferences
    intervention_tolerance: str = "medium"  # low, medium, high
    preferred_tone: str = "casual"  # formal, casual, playful
    
    # Learned patterns (LLM-discovered)
    patterns: List[str] = field(default_factory=list)
    
    # Intervention history
    successful_interventions: List[str] = field(default_factory=list)
    failed_interventions: List[str] = field(default_factory=list)
    
    def to_yaml(self) -> str:
        return yaml.dump({
            "schedule": {
                "typical_start_time": self.typical_start_time,
                "typical_end_time": self.typical_end_time,
                "break_patterns": self.break_patterns,
            },
            "app_usage": {
                "primary_work_apps": self.primary_work_apps,
                "distraction_apps": self.distraction_apps,
            },
            "preferences": {
                "intervention_tolerance": self.intervention_tolerance,
                "preferred_tone": self.preferred_tone,
            },
            "learned_patterns": self.patterns,
            "intervention_history": {
                "what_works": self.successful_interventions[-10:],
                "what_doesnt": self.failed_interventions[-10:],
            }
        }, default_flow_style=False)
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> "UserModel":
        try:
            data = yaml.safe_load(yaml_str)
            model = cls()
            if data and isinstance(data, dict):
                schedule = data.get("schedule", {})
                model.typical_start_time = schedule.get("typical_start_time", "")
                model.typical_end_time = schedule.get("typical_end_time", "")
                model.break_patterns = schedule.get("break_patterns", [])
                
                apps = data.get("app_usage", {})
                model.primary_work_apps = apps.get("primary_work_apps", [])
                model.distraction_apps = apps.get("distraction_apps", [])
                
                prefs = data.get("preferences", {})
                model.intervention_tolerance = prefs.get("intervention_tolerance", "medium")
                model.preferred_tone = prefs.get("preferred_tone", "casual")
                
                model.patterns = data.get("learned_patterns", [])
                
                history = data.get("intervention_history", {})
                model.successful_interventions = history.get("what_works", [])
                model.failed_interventions = history.get("what_doesnt", [])
            return model
        except Exception:
            return cls()


class Analyst:
    """
    The brain that analyzes observations and makes decisions.
    
    Key responsibilities:
    1. Pattern discovery - Find patterns in user behavior
    2. Model updating - Keep the user model current
    3. Intervention decisions - Decide when and what to say
    """
    
    def __init__(
        self,
        llm,
        observation_store,
        model_path: str = None,
        analysis_interval_minutes: int = 10,
    ):
        self.llm = llm
        self.store = observation_store
        self.model_path = model_path or str(Path.home() / ".kayas" / "user_model.yaml")
        self.analysis_interval = analysis_interval_minutes
        
        # Load or create user model
        self.user_model = self._load_model()
        
        # Temporal memory - track topics across sessions
        self.topic_tracker = None
        try:
            from .temporal_memory import TopicTracker
            self.topic_tracker = TopicTracker(llm=llm)
            print("[Analyst] Temporal memory enabled (cross-session topic tracking)")
        except Exception as e:
            print(f"[Analyst] Temporal memory unavailable: {e}")
        
        # Control
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Intervention tracking - learns from ignored messages
        self.last_intervention: Optional[datetime] = None
        self.last_intervention_message: Optional[str] = None
        self.intervention_cooldown_minutes = 10  # Increased from 5 - less chatty
        self.consecutive_ignored = 0  # Track ignored interventions
        self.max_ignored_before_silence = 3  # After 3 ignored, go quieter
    
    def _load_model(self) -> UserModel:
        """Load user model from disk."""
        try:
            if Path(self.model_path).exists():
                with open(self.model_path, "r") as f:
                    return UserModel.from_yaml(f.read())
        except Exception:
            pass
        return UserModel()
    
    def _save_model(self):
        """Save user model to disk."""
        try:
            Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.model_path, "w") as f:
                f.write(self.user_model.to_yaml())
        except Exception:
            pass
    
    def start(self):
        """Start the analysis thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self._thread.start()
        print("[Analyst] Started pattern analysis")
    
    def stop(self):
        """Stop the analysis thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self._save_model()
        print("[Analyst] Stopped")
    
    def _analysis_loop(self):
        """Main analysis loop - runs periodically."""
        while self._running:
            try:
                # Analyze recent observations
                self._analyze_patterns()
            except Exception as e:
                pass
            
            # Sleep for interval (check every second for fast shutdown)
            for _ in range(self.analysis_interval * 60):
                if not self._running:
                    break
                time.sleep(1)
    
    def _analyze_patterns(self):
        """Use LLM to analyze observations and update user model."""
        # Get observation summary
        summary = self.store.get_summary(minutes=60)
        if summary.get("total_observations", 0) < 5:
            return  # Not enough data yet
        
        # Update topic tracking (temporal memory)
        if self.topic_tracker:
            observations = self.store.get_recent(minutes=30)
            self.topic_tracker.update_from_observations(observations)
        
        # Format for LLM
        prompt = f"""You are analyzing user activity patterns to understand them better.

RECENT ACTIVITY (last 60 minutes):
{self._format_summary(summary)}

CURRENT USER MODEL:
{self.user_model.to_yaml()}

Based on this data, identify any new patterns or update existing ones.
Focus on:
1. What apps do they use most for work?
2. What apps seem like distractions?
3. Any time-based patterns?
4. Anything notable about their current behavior?

Respond in this format:
PATTERNS:
- [list any patterns you notice]

UPDATES:
- [any updates to the user model]

Keep it brief - 2-3 bullet points max."""

        try:
            response = self.llm.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=300,
            )
            
            # Strip thinking tags
            import re
            response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
            response = re.sub(r'<think>.*', '', response, flags=re.DOTALL).strip()
            
            # Parse patterns from response
            self._update_model_from_analysis(response)
            self._save_model()
            
        except Exception as e:
            pass
    
    def _format_summary(self, summary: Dict[str, Any]) -> str:
        """Format observation summary for LLM with rich context."""
        lines = []
        lines.append(f"Time span: {summary.get('time_span_minutes', 0)} minutes")
        lines.append(f"Dominant app: {summary.get('dominant_app', 'unknown')}")
        
        if summary.get("app_usage_minutes"):
            lines.append("App usage:")
            for app, mins in sorted(summary["app_usage_minutes"].items(), key=lambda x: -x[1]):
                lines.append(f"  - {app}: {mins} min")
        
        if summary.get("activity_breakdown"):
            lines.append(f"Activity: {summary['activity_breakdown']}")
        
        # DEEP CONTEXT: What they're actually looking at
        if summary.get("recent_window_titles"):
            lines.append("\nRecent window titles (what they're working on):")
            for title in summary["recent_window_titles"][:5]:
                lines.append(f"  - \"{title}\"")
        
        if summary.get("detected_topics"):
            lines.append(f"\nDetected topics: {', '.join(summary['detected_topics'])}")
        
        return "\n".join(lines)
    
    def _update_model_from_analysis(self, analysis: str):
        """Update user model based on LLM analysis."""
        # Extract patterns (simple parsing)
        if "PATTERNS:" in analysis:
            pattern_section = analysis.split("PATTERNS:")[1]
            if "UPDATES:" in pattern_section:
                pattern_section = pattern_section.split("UPDATES:")[0]
            
            # Extract bullet points
            for line in pattern_section.strip().split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    pattern = line[1:].strip()
                    if pattern and pattern not in self.user_model.patterns:
                        self.user_model.patterns.append(pattern)
                        # Keep only last 20 patterns
                        self.user_model.patterns = self.user_model.patterns[-20:]
    
    def should_intervene(self) -> Optional[str]:
        """
        Ask the LLM if we should say something right now.
        
        This is the core of autonomous behavior - the LLM decides
        based on full context, not hardcoded rules.
        
        Returns:
            Message to say, or None if should stay silent.
        """
        # If user has ignored us multiple times, be quieter
        if self.consecutive_ignored >= self.max_ignored_before_silence:
            # Double the cooldown when being ignored
            effective_cooldown = self.intervention_cooldown_minutes * 2
        else:
            effective_cooldown = self.intervention_cooldown_minutes
        
        # Respect cooldown
        if self.last_intervention:
            elapsed = datetime.now() - self.last_intervention
            if elapsed.total_seconds() < effective_cooldown * 60:
                return None
        
        # Get recent activity
        summary = self.store.get_summary(minutes=30)
        if summary.get("total_observations", 0) < 3:
            return None  # Not enough data
        
        # Current context
        now = datetime.now()
        hour = now.hour
        
        # Get temporal context (topics over time)
        temporal_context = ""
        if self.topic_tracker:
            temporal_context = self.topic_tracker.format_for_analyst()
        
        # Get vision context (what's actually on screen)
        vision_context = ""
        if hasattr(self, 'observer') and self.observer:
            vision_context = self.observer.get_screen_context()
        
        # Build the decision prompt - add /nothink to prevent thinking tags
        prompt = f"""/nothink
You are JARVIS, a caring AI companion. You're observing your user.

CURRENT TIME: {now.strftime("%H:%M")} ({now.strftime("%A")})

RECENT ACTIVITY (last 30 min):
{self._format_summary(summary)}

WHAT I CAN SEE ON SCREEN:
{vision_context if vision_context else "No visual analysis yet"}

TEMPORAL CONTEXT (topics over time):
{temporal_context if temporal_context else "Still building history..."}

WHAT I KNOW ABOUT THIS USER:
{self.user_model.to_yaml() if self.user_model.patterns else "Still learning about them..."}

QUESTION:
Based on all this context, should you say something to the user right now?

Consider:
- Reference what you can SEE on their screen
- "I see you're reading about X" is very personal
- Offer specific help based on visible content
- Be natural and conversational

Respond with EXACTLY this format (no other text):
DECISION: SPEAK
REASON: [brief reason]
MESSAGE: [your friendly message]

Or if truly nothing to say:
DECISION: SILENT
REASON: [reason]
MESSAGE: none"""

        try:
            response = self.llm.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=200,
            )
            
            # Handle thinking tags - extract content AFTER </think> if present
            import re
            raw_response = response
            
            # If there's a closing think tag, get everything after it
            if '</think>' in response:
                response = response.split('</think>')[-1].strip()
            else:
                # Otherwise strip any open think tags
                response = re.sub(r'<think>.*', '', response, flags=re.DOTALL).strip()
            
            # Debug: show what LLM decided
            if response:
                print(f"[Analyst] LLM decision: {response[:150]}...")
            else:
                print(f"[Analyst] LLM returned empty (raw was {len(raw_response)} chars)")
            
            # Parse response
            if "DECISION: SPEAK" in response.upper() or "DECISION:SPEAK" in response.upper():
                # Extract message
                if "MESSAGE:" in response:
                    message = response.split("MESSAGE:")[1].strip()
                    message = message.split("\n")[0].strip()  # First line only
                    
                    if message and message.lower() != "none":
                        self.last_intervention = datetime.now()
                        self.last_intervention_message = message
                        self.consecutive_ignored += 1  # Assume ignored until user responds
                        return message
            
            return None
            
        except Exception as e:
            return None
    
    def record_intervention_result(self, message: str, user_responded: bool, positive: bool = True):
        """
        Record how an intervention went for learning.
        
        Call this when user interacts after a proactive message to track
        whether they're engaging or ignoring.
        """
        if user_responded:
            # User engaged - reset ignored count
            self.consecutive_ignored = 0
            if positive:
                self.user_model.successful_interventions.append(message[:50])
        else:
            # User ignored - increase count
            self.consecutive_ignored += 1
            self.user_model.failed_interventions.append(message[:50])
        
        self._save_model()
    
    def mark_ignored(self):
        """Mark the last intervention as ignored (called if no user response within window)."""
        self.consecutive_ignored += 1
        if self.last_intervention_message:
            self.user_model.failed_interventions.append(self.last_intervention_message[:50])
            self._save_model()
    
    def mark_responded(self):
        """Mark that user responded to intervention (resets ignored count)."""
        self.consecutive_ignored = 0
        if self.last_intervention_message:
            self.user_model.successful_interventions.append(self.last_intervention_message[:50])
            self._save_model()


# Convenience function
def start_analyst(llm, observation_store) -> Analyst:
    """Start and return an Analyst instance."""
    analyst = Analyst(llm=llm, observation_store=observation_store)
    analyst.start()
    return analyst
