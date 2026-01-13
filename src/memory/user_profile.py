# -*- coding: utf-8 -*-
"""
User Profile System - Learns and remembers user preferences, patterns, and personality.
Makes Kayas feel like a friend who actually knows you.
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import Counter


@dataclass
class UserProfile:
    """Represents everything Kayas knows about the user."""
    
    # Basic info
    name: str = ""
    nickname: str = ""  # What Kayas calls them
    timezone: str = ""
    
    # Personality traits observed
    communication_style: str = ""  # "formal", "casual", "brief", "detailed"
    humor_preference: str = ""  # "sarcastic", "wholesome", "none"
    decision_style: str = ""  # "quick", "deliberate", "asks_for_advice"
    
    # Emotional patterns
    stress_indicators: List[str] = field(default_factory=list)  # Words/patterns when stressed
    happy_indicators: List[str] = field(default_factory=list)
    
    # Preferences
    preferred_apps: Dict[str, str] = field(default_factory=dict)  # category -> app
    work_hours: Dict[str, str] = field(default_factory=dict)  # start, end
    do_not_disturb_hours: Dict[str, str] = field(default_factory=dict)
    
    # Habits and patterns
    common_tasks: List[str] = field(default_factory=list)
    productivity_patterns: Dict[str, Any] = field(default_factory=dict)
    
    # Goals and aspirations (for proactive suggestions)
    current_goals: List[str] = field(default_factory=list)
    avoided_topics: List[str] = field(default_factory=list)  # Things not to bring up
    
    # Interaction stats
    total_interactions: int = 0
    first_interaction: str = ""
    last_interaction: str = ""


@dataclass
class ContactRelationship:
    """Represents a relationship with a contact."""
    
    name: str
    relationship_type: str = ""  # "friend", "family", "colleague", "ex", "boss", etc.
    nickname: str = ""  # How user refers to them
    notes: str = ""  # User-added notes
    
    # Emotional context
    sentiment: str = "neutral"  # "positive", "negative", "complicated", "neutral"
    caution_level: str = "none"  # "none", "gentle", "warn", "block"
    caution_reason: str = ""
    
    # Interaction patterns
    last_contact: str = ""
    typical_topics: List[str] = field(default_factory=list)
    message_count: int = 0
    
    # Special flags
    is_important: bool = False
    avoid_late_night: bool = False  # Don't suggest contacting late
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "relationship_type": self.relationship_type,
            "nickname": self.nickname,
            "notes": self.notes,
            "sentiment": self.sentiment,
            "caution_level": self.caution_level,
            "caution_reason": self.caution_reason,
            "last_contact": self.last_contact,
            "typical_topics": self.typical_topics,
            "message_count": self.message_count,
            "is_important": self.is_important,
            "avoid_late_night": self.avoid_late_night,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContactRelationship":
        return cls(
            name=data.get("name", ""),
            relationship_type=data.get("relationship_type", ""),
            nickname=data.get("nickname", ""),
            notes=data.get("notes", ""),
            sentiment=data.get("sentiment", "neutral"),
            caution_level=data.get("caution_level", "none"),
            caution_reason=data.get("caution_reason", ""),
            last_contact=data.get("last_contact", ""),
            typical_topics=data.get("typical_topics", []),
            message_count=data.get("message_count", 0),
            is_important=data.get("is_important", False),
            avoid_late_night=data.get("avoid_late_night", False),
        )


class UserProfileManager:
    """
    Manages the user profile and relationship memory.
    Persists to SQLite for durability.
    """
    
    def __init__(self, db_path: Path = None):
        from ..agent.config import db_path as get_db_path
        self.db_path = db_path or get_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._profile: Optional[UserProfile] = None
        self._contacts_cache: Dict[str, ContactRelationship] = {}
    
    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)
    
    def _init_db(self) -> None:
        with self._connect() as conn:
            c = conn.cursor()
            
            # User profile table
            c.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)
            
            # Contact relationships table
            c.execute("""
                CREATE TABLE IF NOT EXISTS contact_relationships (
                    name TEXT PRIMARY KEY,
                    data_json TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # Interaction patterns (for learning)
            c.execute("""
                CREATE TABLE IF NOT EXISTS interaction_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT,
                    pattern_key TEXT,
                    count INTEGER DEFAULT 1,
                    last_seen TEXT,
                    metadata_json TEXT
                )
            """)
            
            # Emotional check-ins
            c.execute("""
                CREATE TABLE IF NOT EXISTS emotional_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    detected_mood TEXT,
                    confidence REAL,
                    context TEXT
                )
            """)
            
            # User feedback/corrections
            c.execute("""
                CREATE TABLE IF NOT EXISTS user_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    original_response TEXT,
                    correction TEXT,
                    category TEXT
                )
            """)
            
            conn.commit()
    
    # ========== Profile Management ==========
    
    def get_profile(self) -> UserProfile:
        """Get the current user profile."""
        if self._profile:
            return self._profile
        
        profile = UserProfile()
        
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT key, value FROM user_profile")
            for key, value in c.fetchall():
                if hasattr(profile, key):
                    try:
                        # Try to parse JSON for complex types
                        parsed = json.loads(value)
                        setattr(profile, key, parsed)
                    except (json.JSONDecodeError, TypeError):
                        setattr(profile, key, value)
        
        self._profile = profile
        return profile
    
    def update_profile(self, **kwargs) -> None:
        """Update profile fields."""
        profile = self.get_profile()
        now = datetime.utcnow().isoformat()
        
        with self._connect() as conn:
            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
                    # Serialize complex types
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value)
                    conn.execute(
                        "INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES (?, ?, ?)",
                        (key, str(value), now)
                    )
            conn.commit()
    
    def increment_interactions(self) -> None:
        """Track interaction count."""
        profile = self.get_profile()
        now = datetime.utcnow().isoformat()
        
        if not profile.first_interaction:
            self.update_profile(first_interaction=now)
        
        self.update_profile(
            total_interactions=profile.total_interactions + 1,
            last_interaction=now
        )
    
    # ========== Contact Relationships ==========
    
    def get_contact(self, name: str) -> Optional[ContactRelationship]:
        """Get relationship info for a contact."""
        name_lower = name.lower().strip()
        
        # Check cache
        if name_lower in self._contacts_cache:
            return self._contacts_cache[name_lower]
        
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT data_json FROM contact_relationships WHERE LOWER(name) = ?",
                (name_lower,)
            )
            row = c.fetchone()
            if row:
                data = json.loads(row[0])
                contact = ContactRelationship.from_dict(data)
                self._contacts_cache[name_lower] = contact
                return contact
        
        return None
    
    def set_contact(self, contact: ContactRelationship) -> None:
        """Save or update a contact relationship."""
        name_lower = contact.name.lower().strip()
        now = datetime.utcnow().isoformat()
        
        with self._connect() as conn:
            # Check if exists
            c = conn.cursor()
            c.execute("SELECT 1 FROM contact_relationships WHERE LOWER(name) = ?", (name_lower,))
            exists = c.fetchone() is not None
            
            if exists:
                conn.execute(
                    "UPDATE contact_relationships SET data_json = ?, updated_at = ? WHERE LOWER(name) = ?",
                    (json.dumps(contact.to_dict()), now, name_lower)
                )
            else:
                conn.execute(
                    "INSERT INTO contact_relationships (name, data_json, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (contact.name, json.dumps(contact.to_dict()), now, now)
                )
            conn.commit()
        
        self._contacts_cache[name_lower] = contact
    
    def get_all_contacts(self) -> List[ContactRelationship]:
        """Get all saved contact relationships."""
        contacts = []
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT data_json FROM contact_relationships")
            for row in c.fetchall():
                data = json.loads(row[0])
                contacts.append(ContactRelationship.from_dict(data))
        return contacts
    
    def update_contact_interaction(self, name: str) -> None:
        """Update last contact time and increment message count."""
        contact = self.get_contact(name)
        if contact:
            contact.last_contact = datetime.utcnow().isoformat()
            contact.message_count += 1
            self.set_contact(contact)
    
    # ========== Pattern Learning ==========
    
    def log_pattern(self, pattern_type: str, pattern_key: str, metadata: Dict = None) -> None:
        """Log an interaction pattern for learning."""
        now = datetime.utcnow().isoformat()
        
        with self._connect() as conn:
            c = conn.cursor()
            
            # Check if pattern exists
            c.execute(
                "SELECT id, count FROM interaction_patterns WHERE pattern_type = ? AND pattern_key = ?",
                (pattern_type, pattern_key)
            )
            row = c.fetchone()
            
            if row:
                conn.execute(
                    "UPDATE interaction_patterns SET count = ?, last_seen = ?, metadata_json = ? WHERE id = ?",
                    (row[1] + 1, now, json.dumps(metadata or {}), row[0])
                )
            else:
                conn.execute(
                    "INSERT INTO interaction_patterns (pattern_type, pattern_key, count, last_seen, metadata_json) VALUES (?, ?, 1, ?, ?)",
                    (pattern_type, pattern_key, now, json.dumps(metadata or {}))
                )
            conn.commit()
    
    def get_common_patterns(self, pattern_type: str, limit: int = 10) -> List[Dict]:
        """Get most common patterns of a type."""
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT pattern_key, count, last_seen FROM interaction_patterns WHERE pattern_type = ? ORDER BY count DESC LIMIT ?",
                (pattern_type, limit)
            )
            return [{"key": row[0], "count": row[1], "last_seen": row[2]} for row in c.fetchall()]
    
    # ========== Emotional Awareness ==========
    
    def log_mood(self, mood: str, confidence: float, context: str = "") -> None:
        """Log a detected mood."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO emotional_log (timestamp, detected_mood, confidence, context) VALUES (?, ?, ?, ?)",
                (datetime.utcnow().isoformat(), mood, confidence, context)
            )
            conn.commit()
    
    def get_recent_moods(self, hours: int = 24) -> List[Dict]:
        """Get moods detected in the last N hours."""
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT detected_mood, confidence, context, timestamp FROM emotional_log WHERE timestamp > ? ORDER BY timestamp DESC",
                (cutoff,)
            )
            return [
                {"mood": row[0], "confidence": row[1], "context": row[2], "timestamp": row[3]}
                for row in c.fetchall()
            ]
    
    def get_dominant_mood(self, hours: int = 24) -> Optional[str]:
        """Get the most common mood in the last N hours."""
        moods = self.get_recent_moods(hours)
        if not moods:
            return None
        
        mood_counts = Counter(m["mood"] for m in moods)
        return mood_counts.most_common(1)[0][0]
    
    # ========== User Corrections ==========
    
    def log_correction(self, original: str, correction: str, category: str = "") -> None:
        """Log when user corrects Kayas - for learning."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO user_corrections (timestamp, original_response, correction, category) VALUES (?, ?, ?, ?)",
                (datetime.utcnow().isoformat(), original, correction, category)
            )
            conn.commit()
    
    # ========== Context Building ==========
    
    def get_context_summary(self) -> str:
        """Build a context summary for the LLM."""
        profile = self.get_profile()
        parts = []
        
        # User info
        if profile.name:
            parts.append(f"User's name: {profile.name}")
        if profile.nickname:
            parts.append(f"Call them: {profile.nickname}")
        
        # Communication preferences
        if profile.communication_style:
            parts.append(f"Communication style: {profile.communication_style}")
        if profile.humor_preference:
            parts.append(f"Humor: {profile.humor_preference}")
        
        # Stats
        if profile.total_interactions > 0:
            parts.append(f"We've had {profile.total_interactions} interactions")
        
        # Current goals
        if profile.current_goals:
            parts.append(f"Current goals: {', '.join(profile.current_goals[:3])}")
        
        # Recent mood
        mood = self.get_dominant_mood(hours=4)
        if mood:
            parts.append(f"Recent mood: {mood}")
        
        # Common tasks
        common = self.get_common_patterns("task", limit=3)
        if common:
            parts.append(f"Common tasks: {', '.join(p['key'] for p in common)}")
        
        return "\n".join(parts) if parts else ""
    
    def get_contact_context(self, contact_name: str) -> str:
        """Get context about a specific contact for messaging."""
        contact = self.get_contact(contact_name)
        if not contact:
            return ""
        
        parts = []
        
        if contact.relationship_type:
            parts.append(f"Relationship: {contact.relationship_type}")
        
        if contact.sentiment != "neutral":
            parts.append(f"Relationship status: {contact.sentiment}")
        
        if contact.notes:
            parts.append(f"Notes: {contact.notes}")
        
        if contact.caution_level != "none":
            parts.append(f"⚠️ Caution ({contact.caution_level}): {contact.caution_reason}")
        
        if contact.avoid_late_night:
            parts.append("Avoid contacting late at night")
        
        return "\n".join(parts) if parts else ""


# Singleton instance
_profile_manager: Optional[UserProfileManager] = None


def get_profile_manager() -> UserProfileManager:
    """Get the singleton profile manager."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = UserProfileManager()
    return _profile_manager
