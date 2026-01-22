"""
Temporal Memory - Cross-Session Topic Tracking for JARVIS.

This module enables JARVIS to remember what you've been working on
across sessions, days, and weeks. Instead of just knowing "you're on Chrome",
it knows "you've been researching AWQ for 3 days, 4 hours total".

Components:
1. TopicTracker - Extracts and tracks topics from observations
2. TopicStore - SQLite storage for cross-session persistence
3. TemporalContext - Rich context for Analyst decisions
"""
from __future__ import annotations

import sqlite3
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path


@dataclass
class Topic:
    """A topic the user has been working on."""
    name: str
    category: str  # "coding", "research", "entertainment", etc.
    first_seen: datetime
    last_seen: datetime
    total_minutes: float = 0
    session_count: int = 1
    related_topics: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "total_minutes": round(self.total_minutes, 1),
            "session_count": self.session_count,
            "related_topics": self.related_topics,
        }


class TopicStore:
    """SQLite storage for topic history."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path.home() / ".kayas" / "topics.db")
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    category TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    total_minutes REAL DEFAULT 0,
                    session_count INTEGER DEFAULT 1,
                    related_topics TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_topic_name 
                ON topics(name)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_topic_last_seen 
                ON topics(last_seen)
            """)
            conn.commit()
    
    def upsert_topic(self, topic: Topic):
        """Insert or update a topic."""
        with sqlite3.connect(self.db_path) as conn:
            # Check if exists
            existing = conn.execute(
                "SELECT id, total_minutes, session_count FROM topics WHERE name = ?",
                (topic.name,)
            ).fetchone()
            
            if existing:
                # Update existing
                conn.execute("""
                    UPDATE topics 
                    SET last_seen = ?, 
                        total_minutes = total_minutes + ?,
                        category = ?,
                        related_topics = ?
                    WHERE name = ?
                """, (
                    topic.last_seen.isoformat(),
                    topic.total_minutes,
                    topic.category,
                    ",".join(topic.related_topics),
                    topic.name,
                ))
            else:
                # Insert new
                conn.execute("""
                    INSERT INTO topics 
                    (name, category, first_seen, last_seen, total_minutes, session_count, related_topics)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    topic.name,
                    topic.category,
                    topic.first_seen.isoformat(),
                    topic.last_seen.isoformat(),
                    topic.total_minutes,
                    topic.session_count,
                    ",".join(topic.related_topics),
                ))
            conn.commit()
    
    def increment_session(self, topic_name: str):
        """Increment session count for a topic (new session started)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE topics SET session_count = session_count + 1 WHERE name = ?",
                (topic_name,)
            )
            conn.commit()
    
    def get_topic(self, name: str) -> Optional[Topic]:
        """Get a single topic by name."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM topics WHERE name = ?", (name,)
            ).fetchone()
            
            if row:
                return self._row_to_topic(dict(row))
        return None
    
    def get_recent_topics(self, days: int = 7) -> List[Topic]:
        """Get topics from the last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM topics 
                WHERE last_seen > ?
                ORDER BY last_seen DESC
            """, (cutoff,)).fetchall()
            
            return [self._row_to_topic(dict(row)) for row in rows]
    
    def get_top_topics(self, limit: int = 10) -> List[Topic]:
        """Get most-worked-on topics by total time."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM topics 
                ORDER BY total_minutes DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [self._row_to_topic(dict(row)) for row in rows]
    
    def _row_to_topic(self, row: dict) -> Topic:
        """Convert database row to Topic object."""
        return Topic(
            name=row["name"],
            category=row.get("category", ""),
            first_seen=datetime.fromisoformat(row["first_seen"]),
            last_seen=datetime.fromisoformat(row["last_seen"]),
            total_minutes=row.get("total_minutes", 0),
            session_count=row.get("session_count", 1),
            related_topics=row.get("related_topics", "").split(",") if row.get("related_topics") else [],
        )


class TopicTracker:
    """
    Extracts and tracks topics from window titles over time.
    
    This is the core of temporal memory - it converts raw observations
    into meaningful topics that persist across sessions.
    """
    
    def __init__(self, store: TopicStore = None, llm = None):
        self.store = store or TopicStore()
        self.llm = llm
        
        # Track current session topics
        self.session_topics: Dict[str, float] = {}  # topic -> minutes this session
        self.session_start = datetime.now()
        self.last_update = datetime.now()
    
    def extract_topics_from_titles(self, titles: List[str]) -> List[Dict[str, str]]:
        """
        Extract meaningful topics from window titles.
        
        Uses pattern matching for common cases, LLM for complex ones.
        """
        topics = []
        
        for title in titles:
            if not title:
                continue
                
            title_lower = title.lower()
            
            # Programming topics
            if any(x in title_lower for x in ['github', 'gitlab', 'stackoverflow']):
                # Extract repo or question topic
                topics.append({"name": self._extract_code_topic(title), "category": "coding"})
            
            # Documentation/Research
            elif any(x in title_lower for x in ['documentation', 'docs', 'api', 'guide']):
                topics.append({"name": self._extract_doc_topic(title), "category": "research"})
            
            # AI/ML specific
            elif any(x in title_lower for x in ['hugging face', 'openai', 'langchain', 'llama', 'gpt', 'transformers', 'pytorch', 'tensorflow']):
                topics.append({"name": self._extract_ai_topic(title), "category": "AI/ML"})
            
            # YouTube
            elif 'youtube' in title_lower:
                topics.append({"name": self._extract_video_topic(title), "category": "video"})
            
            # Generic extraction from meaningful titles
            elif ' - ' in title:
                parts = title.split(' - ')
                if len(parts) >= 2 and len(parts[0]) > 5:
                    topics.append({"name": parts[0].strip()[:50], "category": "unknown"})
        
        # Deduplicate
        seen = set()
        unique_topics = []
        for t in topics:
            if t["name"] and t["name"] not in seen:
                seen.add(t["name"])
                unique_topics.append(t)
        
        return unique_topics[:5]  # Keep top 5
    
    def _extract_code_topic(self, title: str) -> str:
        """Extract coding topic from title."""
        # GitHub: "repo/file - GitHub"
        if 'github' in title.lower():
            parts = title.split(' · ')
            if parts:
                return parts[0].strip()[:40]
        
        # StackOverflow: "Question title - Stack Overflow"
        if 'stackoverflow' in title.lower():
            parts = title.split(' - ')
            if parts:
                return parts[0].strip()[:50]
        
        return title[:40]
    
    def _extract_doc_topic(self, title: str) -> str:
        """Extract documentation topic."""
        # Remove common suffixes
        clean = re.sub(r'\s*[-|·]\s*(Documentation|Docs|API|Guide|Reference).*$', '', title, flags=re.I)
        return clean.strip()[:50]
    
    def _extract_ai_topic(self, title: str) -> str:
        """Extract AI/ML topic."""
        # Common patterns
        clean = re.sub(r'\s*[-|·]\s*(Hugging Face|GitHub|Colab).*$', '', title, flags=re.I)
        return clean.strip()[:50]
    
    def _extract_video_topic(self, title: str) -> str:
        """Extract video topic."""
        clean = re.sub(r'\s*[-|·]\s*YouTube.*$', '', title, flags=re.I)
        return clean.strip()[:50]
    
    def update_from_observations(self, observations: List[Dict[str, Any]], interval_minutes: float = 0.5):
        """
        Update topic tracking from recent observations.
        
        Args:
            observations: Recent observation data from Observer
            interval_minutes: Time between observations (default 30s = 0.5min)
        """
        if not observations:
            return
        
        # Get unique window titles
        titles = list(set(obs.get("window_title", "") for obs in observations[:20]))
        
        # Extract topics
        extracted = self.extract_topics_from_titles(titles)
        
        now = datetime.now()
        
        for topic_data in extracted:
            topic_name = topic_data["name"]
            if not topic_name:
                continue
            
            # Update session tracking
            if topic_name not in self.session_topics:
                self.session_topics[topic_name] = 0
            
            # Add time (estimate based on how many observations mention related titles)
            time_for_topic = interval_minutes * len(observations) / max(len(extracted), 1)
            self.session_topics[topic_name] += time_for_topic
            
            # Update persistent storage
            existing = self.store.get_topic(topic_name)
            if existing:
                existing.last_seen = now
                existing.total_minutes = time_for_topic  # Will be added in upsert
                self.store.upsert_topic(existing)
            else:
                new_topic = Topic(
                    name=topic_name,
                    category=topic_data.get("category", "unknown"),
                    first_seen=now,
                    last_seen=now,
                    total_minutes=time_for_topic,
                    session_count=1,
                )
                self.store.upsert_topic(new_topic)
        
        self.last_update = now
    
    def get_temporal_context(self) -> Dict[str, Any]:
        """
        Get rich temporal context for Analyst decisions.
        
        This is what makes JARVIS say "You've been researching X for 3 days"
        instead of just "You're using Chrome".
        """
        recent_topics = self.store.get_recent_topics(days=7)
        top_topics = self.store.get_top_topics(limit=5)
        
        # Format for LLM
        context = {
            "session_duration_minutes": (datetime.now() - self.session_start).total_seconds() / 60,
            "topics_this_session": list(self.session_topics.keys())[:5],
            "recent_topics_7_days": [
                {
                    "name": t.name,
                    "total_hours": round(t.total_minutes / 60, 1),
                    "sessions": t.session_count,
                    "days_ago": (datetime.now() - t.last_seen).days,
                }
                for t in recent_topics[:5]
            ],
            "most_worked_on": [
                {"name": t.name, "total_hours": round(t.total_minutes / 60, 1)}
                for t in top_topics[:3]
            ],
        }
        
        return context
    
    def format_for_analyst(self) -> str:
        """Format temporal context as text for Analyst prompt."""
        ctx = self.get_temporal_context()
        
        lines = []
        lines.append(f"Session duration: {round(ctx['session_duration_minutes'])} minutes")
        
        if ctx.get("topics_this_session"):
            lines.append(f"Topics this session: {', '.join(ctx['topics_this_session'])}")
        
        if ctx.get("recent_topics_7_days"):
            lines.append("\nTopics over the past week:")
            for t in ctx["recent_topics_7_days"]:
                days_text = f"{t['days_ago']}d ago" if t['days_ago'] > 0 else "today"
                lines.append(f"  - {t['name']}: {t['total_hours']}hrs over {t['sessions']} sessions ({days_text})")
        
        if ctx.get("most_worked_on"):
            lines.append("\nMost worked on overall:")
            for t in ctx["most_worked_on"]:
                lines.append(f"  - {t['name']}: {t['total_hours']} total hours")
        
        return "\n".join(lines)
