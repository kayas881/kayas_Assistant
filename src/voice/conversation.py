"""
Conversation manager for handling multi-turn chat with context and tool integration.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
import json
import time
import uuid

from .direct_agent import DirectAgent
from ..memory.sqlite_memory import SQLiteMemory, MemoryConfig
from ..memory.vector_memory import VectorMemory, VectorMemoryConfig
from ..agent.config import db_path, chroma_dir, embed_model


@dataclass
class ConversationConfig:
    max_history: int = 20
    context_window: int = 4000  # tokens
    save_conversations: bool = True
    use_vector_memory: bool = True
    conversation_timeout: float = 300.0  # 5 minutes of inactivity


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: float
    metadata: Dict[str, Any]


class ConversationManager:
    def __init__(self, cfg: ConversationConfig | None = None):
        self.cfg = cfg or ConversationConfig()
        self.conversation_id = str(uuid.uuid4())
        self.messages: List[Message] = []
        self.last_activity = time.time()
        
        # Initialize memory systems
        if self.cfg.save_conversations:
            self.memory = SQLiteMemory(MemoryConfig(db_path=db_path()))
        else:
            self.memory = None
            
        if self.cfg.use_vector_memory:
            self.vector_memory = VectorMemory(VectorMemoryConfig(
                persist_dir=chroma_dir(),
                embed_model=embed_model()
            ))
        else:
            self.vector_memory = None
            
        # Initialize direct agent
        self.agent = DirectAgent()

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] | None = None) -> Message:
        """Add a message to the conversation."""
        message = Message(
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        self.messages.append(message)
        self.last_activity = time.time()
        
        # Trim history if needed
        if len(self.messages) > self.cfg.max_history:
            self.messages = self.messages[-self.cfg.max_history:]
        
        # Save to persistent memory
        if self.memory:
            try:
                self.memory.log_message(
                    run_id=self.conversation_id,
                    role=role,
                    content=content
                )
            except Exception as e:
                print(f"Failed to save message to memory: {e}")
        
        return message

    def get_context(self) -> str:
        """Build context string from recent messages."""
        if not self.messages:
            return ""
            
        context_parts = []
        total_length = 0
        
        # Add messages in reverse order until we hit the context window
        for message in reversed(self.messages):
            message_text = f"{message.role}: {message.content}\n"
            if total_length + len(message_text) > self.cfg.context_window:
                break
            context_parts.append(message_text)
            total_length += len(message_text)
        
        # Reverse to get chronological order
        context_parts.reverse()
        return "".join(context_parts)

    def process_user_input(self, user_input: str) -> str:
        """Process user input and generate a response."""
        # Add user message
        self.add_message("user", user_input)
        
        # Check for special commands
        if user_input.lower().strip() in ["exit", "quit", "bye", "goodbye"]:
            response = "Goodbye! It was nice talking with you."
            self.add_message("assistant", response)
            return response
        
        if user_input.lower().strip() in ["help", "what can you do"]:
            response = self._get_help_text()
            self.add_message("assistant", response)
            return response
        
        # Search vector memory for relevant context
        relevant_context = ""
        if self.vector_memory:
            try:
                results = self.vector_memory.query(user_input, k=3)
                if results:
                    relevant_context = "\n".join([doc.get('document', '') for doc in results[:2]])
            except Exception as e:
                print(f"Vector memory search failed: {e}")
        
        # Build enhanced prompt with context
        context = self.get_context()
        enhanced_prompt = self._build_enhanced_prompt(user_input, context, relevant_context)
        
        try:
            # Run the direct agent with the user input AND conversation context
            result = self.agent.run(user_input, conversation_context=context)
            
            # Extract response from agent result
            response = result.get("response", "I completed the task successfully.")
            
            # Add assistant response
            self.add_message("assistant", response, {"agent_result": result})
            
            # Store in vector memory for future reference
            if self.vector_memory:
                try:
                    doc_text = f"User: {user_input}\nAssistant: {response}"
                    self.vector_memory.add(
                        texts=[doc_text],
                        metadatas=[{
                            "type": "conversation",
                            "conversation_id": self.conversation_id,
                            "timestamp": time.time()
                        }],
                        ids=[f"conv-{self.conversation_id}-{len(self.messages)}"]
                    )
                except Exception as e:
                    print(f"Failed to store in vector memory: {e}")
            
            return response
            
        except Exception as e:
            error_response = f"I encountered an error: {str(e)}"
            self.add_message("assistant", error_response, {"error": str(e)})
            return error_response

    def _build_enhanced_prompt(self, user_input: str, context: str, relevant_context: str) -> str:
        """Build an enhanced prompt with context and history."""
        prompt_parts = []
        
        # System context
        prompt_parts.append(
            "You are Kayas, a helpful AI assistant with access to desktop automation, "
            "web browsing, calendar, messaging, and other tools. You can help with tasks "
            "like taking screenshots, clicking on screen elements, managing emails, "
            "browsing websites, and much more."
        )
        
        # Add relevant context from memory
        if relevant_context:
            prompt_parts.append(f"\nRelevant previous context:\n{relevant_context}")
        
        # Add recent conversation history
        if context:
            prompt_parts.append(f"\nRecent conversation:\n{context}")
        
        # Current user input
        prompt_parts.append(f"\nUser: {user_input}")
        prompt_parts.append("\nAssistant:")
        
        return "\n".join(prompt_parts)

    def _get_help_text(self) -> str:
        """Get help text describing capabilities."""
        return """I'm Kayas, your AI assistant! Here's what I can help you with:

🖥️ Desktop Control:
- Take screenshots and analyze your screen
- Click on buttons, text, or images
- Type text and use keyboard shortcuts
- Control windows and applications

🌐 Web Browsing:
- Visit websites and interact with forms
- Fill out forms and submit data
- Take screenshots of web pages
- Manage browser sessions and login flows

📅 Calendar & Communication:
- Manage Google Calendar events
- Send Slack messages and check channels
- Control Spotify playback
- Send emails

🤖 General Tasks:
- Create and edit files
- Search your local files
- Answer questions and provide information
- Execute complex multi-step workflows

Just tell me what you'd like to do in natural language, and I'll help you accomplish it!

Examples:
- "Take a screenshot of my desktop"
- "Click on the Start button"
- "Open Google and search for Python tutorials"
- "Create a calendar event for tomorrow at 2 PM"
- "Play some jazz music on Spotify"
"""

    def is_conversation_active(self) -> bool:
        """Check if conversation is still active (not timed out)."""
        return (time.time() - self.last_activity) < self.cfg.conversation_timeout

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation."""
        return {
            "conversation_id": self.conversation_id,
            "message_count": len(self.messages),
            "last_activity": self.last_activity,
            "is_active": self.is_conversation_active(),
            "duration": time.time() - (self.messages[0].timestamp if self.messages else time.time())
        }