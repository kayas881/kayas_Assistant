# Voice and conversation components
# Lazy imports - only load when explicitly requested
# This prevents double initialization when importing specific modules

__all__ = [
    "VoiceAgent",
    "VoiceConfig", 
    "ConversationManager",
    "ConversationConfig",
    "ChatAgent",
    "ChatAgentConfig",
    "ChatGUI",
]

def __getattr__(name):
    """Lazy import to avoid double initialization."""
    if name in ("VoiceAgent", "VoiceConfig"):
        from .voice_agent import VoiceAgent, VoiceConfig
        return VoiceAgent if name == "VoiceAgent" else VoiceConfig
    elif name in ("ConversationManager", "ConversationConfig"):
        from .conversation import ConversationManager, ConversationConfig
        return ConversationManager if name == "ConversationManager" else ConversationConfig
    elif name in ("ChatAgent", "ChatAgentConfig"):
        from .chat_agent import ChatAgent, ChatAgentConfig
        return ChatAgent if name == "ChatAgent" else ChatAgentConfig
    elif name == "ChatGUI":
        from .gui import ChatGUI
        return ChatGUI
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")