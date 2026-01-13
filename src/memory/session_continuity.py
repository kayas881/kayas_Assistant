# -*- coding: utf-8 -*-
"""
Session Continuity System for Kayas.

Handles persistence across restarts:
- Remembers user profile
- Recalls last session context
- Generates appropriate welcome-back messages
- Maintains relationship awareness
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path


class SessionContinuity:
    """
    Manages session continuity across restarts.
    
    Makes Kayas feel like the same friend who remembers everything,
    not a fresh instance every time.
    """
    
    def __init__(self, memory=None, profile_manager=None):
        """
        Initialize session continuity.
        
        Args:
            memory: SQLiteMemory instance for conversation history
            profile_manager: UserProfileManager for user profile
        """
        self.memory = memory
        self.profile_manager = profile_manager
        self._session_start = datetime.now()
        self._is_returning_user = False
        self._last_session_info: Optional[Dict] = None
    
    def check_returning_user(self) -> bool:
        """Check if this is a returning user (has previous interactions)."""
        if self.memory:
            count = self.memory.get_message_count()
            self._is_returning_user = count > 0
            return self._is_returning_user
        return False
    
    def get_session_context(self) -> Dict[str, Any]:
        """
        Get context from the last session.
        
        Returns dict with:
        - is_returning: bool
        - hours_since_last: float (hours since last interaction)
        - last_topics: list of recent topics
        - user_name: str (if known)
        - relationship_count: int
        """
        context = {
            "is_returning": False,
            "hours_since_last": None,
            "last_topics": [],
            "user_name": None,
            "nickname": None,
            "relationship_count": 0,
            "total_interactions": 0,
        }
        
        # Get memory context
        if self.memory:
            try:
                session_info = self.memory.get_last_session_summary()
                self._last_session_info = session_info
                
                if session_info.get("last_interaction"):
                    context["is_returning"] = True
                    
                    # Calculate time since last interaction
                    last_time = datetime.fromisoformat(session_info["last_interaction"])
                    delta = datetime.now() - last_time
                    context["hours_since_last"] = delta.total_seconds() / 3600
                    
                    context["last_topics"] = session_info.get("recent_topics", [])
                
                context["total_interactions"] = self.memory.get_message_count()
            except Exception as e:
                print(f"[SessionContinuity] Error getting session info: {e}")
        
        # Get profile context
        if self.profile_manager:
            try:
                profile = self.profile_manager.get_profile()
                context["user_name"] = profile.name
                context["nickname"] = profile.nickname
                context["relationship_count"] = len(self.profile_manager.get_all_contacts())
            except Exception as e:
                print(f"[SessionContinuity] Error getting profile: {e}")
        
        return context
    
    def generate_welcome_message(self) -> str:
        """
        Generate an appropriate welcome message based on context.
        
        Returns a personalized greeting that acknowledges the relationship.
        """
        ctx = self.get_session_context()
        
        # First-time user
        if not ctx["is_returning"]:
            return self._first_time_greeting()
        
        # Returning user - personalize based on context
        name = ctx.get("nickname") or ctx.get("user_name")
        hours = ctx.get("hours_since_last", 0)
        
        # Just restarted (< 1 hour)
        if hours and hours < 1:
            if name:
                return f"Back already, {name}? I'm here."
            return "I'm back. Where were we?"
        
        # Same day (< 12 hours)
        elif hours and hours < 12:
            if name:
                return f"Hey {name}! What's up?"
            return "Hey! What can I do for you?"
        
        # Next day (12-36 hours)
        elif hours and hours < 36:
            greeting = self._time_appropriate_greeting()
            if name:
                return f"{greeting}, {name}! Ready when you are."
            return f"{greeting}! What are we working on today?"
        
        # Been a while (> 36 hours)
        else:
            if name:
                return f"Hey {name}! It's been a minute. Good to see you back."
            return "Hey! It's been a while. What can I help with?"
    
    def _first_time_greeting(self) -> str:
        """Greeting for brand new users."""
        return (
            "Hey! I'm Kayas, your AI companion. I can help with just about anything on your computer - "
            "files, browsing, messages, research, you name it.\n\n"
            "A few things to get started:\n"
            "• Tell me your name: 'my name is [name]'\n"
            "• Or a nickname: 'call me [nickname]'\n"
            "• I can remember relationships: '[name] is my [relationship]'\n\n"
            "What would you like to do?"
        )
    
    def _time_appropriate_greeting(self) -> str:
        """Get time-appropriate greeting."""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "Good morning"
        elif 12 <= hour < 17:
            return "Good afternoon"
        elif 17 <= hour < 21:
            return "Good evening"
        else:
            return "Hey"
    
    def get_context_for_prompt(self) -> str:
        """
        Get session context formatted for injection into system prompt.
        
        This helps the LLM maintain continuity.
        """
        ctx = self.get_session_context()
        parts = []
        
        if ctx["is_returning"]:
            parts.append("This is a returning user you've talked to before.")
            
            if ctx["total_interactions"]:
                parts.append(f"You've had {ctx['total_interactions']} messages together.")
            
            if ctx["user_name"]:
                name_to_use = ctx.get("nickname") or ctx["user_name"]
                parts.append(f"Their name is {ctx['user_name']}, call them {name_to_use}.")
            
            if ctx["relationship_count"]:
                parts.append(f"You know about {ctx['relationship_count']} people in their life.")
            
            hours = ctx.get("hours_since_last")
            if hours:
                if hours < 1:
                    parts.append("They just restarted the app a moment ago.")
                elif hours < 12:
                    parts.append("You talked earlier today.")
                elif hours < 36:
                    parts.append("You talked yesterday.")
                else:
                    parts.append(f"It's been {int(hours / 24)} days since you last talked.")
            
            # Add recent topics if available
            if ctx["last_topics"]:
                topics_preview = [t[:50] for t in ctx["last_topics"][:3]]
                parts.append(f"Recent topics: {', '.join(topics_preview)}")
        else:
            parts.append("This is a new user you haven't met before.")
        
        return "\n".join(parts)
    
    def log_session_start(self) -> None:
        """Log that a new session has started."""
        # This could be expanded to track session patterns
        self._session_start = datetime.now()


# Singleton
_session_continuity: Optional[SessionContinuity] = None


def get_session_continuity(memory=None, profile_manager=None) -> SessionContinuity:
    """Get or create the session continuity manager."""
    global _session_continuity
    
    if _session_continuity is None:
        _session_continuity = SessionContinuity(memory, profile_manager)
    elif memory and not _session_continuity.memory:
        _session_continuity.memory = memory
    elif profile_manager and not _session_continuity.profile_manager:
        _session_continuity.profile_manager = profile_manager
    
    return _session_continuity
