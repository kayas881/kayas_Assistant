# Memory module exports
from .sqlite_memory import SQLiteMemory
from .vector_memory import VectorMemory
from .user_profile import UserProfileManager, UserProfile, ContactRelationship, get_profile_manager

__all__ = [
    "SQLiteMemory",
    "VectorMemory", 
    "UserProfileManager",
    "UserProfile",
    "ContactRelationship",
    "get_profile_manager",
]