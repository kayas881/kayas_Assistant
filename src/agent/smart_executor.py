"""
Smart Executor - Uses LLM function calling instead of regex parsing.

This replaces the fragile regex-based action parsing with native function calling.
When the LLM doesn't understand, it asks for clarification instead of falling back
to the perception engine.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
import json
import re
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    """Result of executing an action."""
    success: bool
    response: str
    action_taken: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    needs_clarification: bool = False
    clarification_options: Optional[List[str]] = None


# Tool definitions for function calling
TOOL_DEFINITIONS = [
    # Filesystem tools
    {
        "type": "function",
        "function": {
            "name": "filesystem_create_file",
            "description": "Create a new file with optional content. Use for creating notes, documents, scripts, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to create (e.g., 'notes.txt', 'script.py')"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file. Can be empty."
                    }
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "filesystem_append_file",
            "description": "Append content to an existing file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the file"},
                    "content": {"type": "string", "description": "Content to append"}
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "filesystem_create_folder",
            "description": "Create a new folder/directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path of the folder to create"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "filesystem_rename",
            "description": "Rename a file or folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Current path of file/folder"},
                    "new_name": {"type": "string", "description": "New name for the file/folder"}
                },
                "required": ["path", "new_name"]
            }
        }
    },
    
    # Web tools
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information. Use for research, finding answers, looking things up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Maximum results to return", "default": 5}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_deep_research",
            "description": "Do deep research on a topic with multiple sources and citations. Use for complex questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The research question"},
                    "max_sources": {"type": "integer", "description": "Maximum sources to use", "default": 8}
                },
                "required": ["question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch_page",
            "description": "Fetch and read the content of a specific URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"}
                },
                "required": ["url"]
            }
        }
    },
    
    # Browser tools
    {
        "type": "function",
        "function": {
            "name": "browser_open",
            "description": "Open a website in the browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to open"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_search",
            "description": "Open browser and search for something on Google.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    },
    
    # Process tools
    {
        "type": "function",
        "function": {
            "name": "process_start_program",
            "description": "Start/open a program or application (e.g., notepad, chrome, spotify).",
            "parameters": {
                "type": "object",
                "properties": {
                    "program": {"type": "string", "description": "Program name or path (e.g., 'notepad.exe', 'chrome')"},
                    "args": {"type": "array", "items": {"type": "string"}, "description": "Command line arguments"}
                },
                "required": ["program"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "process_list",
            "description": "List running processes on the system.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter": {"type": "string", "description": "Optional filter for process name"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "process_kill",
            "description": "Kill/terminate a running process.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Process name to kill"}
                },
                "required": ["name"]
            }
        }
    },
    
    # Clipboard tools
    {
        "type": "function",
        "function": {
            "name": "clipboard_copy",
            "description": "Copy text to the clipboard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to copy to clipboard"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clipboard_paste",
            "description": "Get text from the clipboard.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    
    # System info tools
    {
        "type": "function",
        "function": {
            "name": "system_info",
            "description": "Get system information (CPU, memory, disk usage).",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["cpu", "memory", "disk", "all"],
                        "description": "Category of info to get"
                    }
                }
            }
        }
    },
    
    # WhatsApp tools
    {
        "type": "function",
        "function": {
            "name": "whatsapp_send_message",
            "description": "Send a WhatsApp message to a contact or group.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact": {"type": "string", "description": "Contact name or phone number"},
                    "message": {"type": "string", "description": "Message to send"}
                },
                "required": ["contact", "message"]
            }
        }
    },
    
    # Calendar tools
    {
        "type": "function",
        "function": {
            "name": "calendar_list_events",
            "description": "List upcoming calendar events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "Number of days ahead to check", "default": 7}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_create_event",
            "description": "Create a new calendar event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Event title"},
                    "start_time": {"type": "string", "description": "Start time (e.g., '2024-01-15 14:00')"},
                    "end_time": {"type": "string", "description": "End time"},
                    "description": {"type": "string", "description": "Event description"}
                },
                "required": ["summary", "start_time", "end_time"]
            }
        }
    },
    
    # Spotify tools
    {
        "type": "function",
        "function": {
            "name": "spotify_play",
            "description": "Play music on Spotify.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Song, artist, or playlist to play"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_pause",
            "description": "Pause Spotify playback.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    
    # Screenshot/Desktop tools
    {
        "type": "function",
        "function": {
            "name": "desktop_screenshot",
            "description": "Take a screenshot of the current screen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Filename to save screenshot as"}
                }
            }
        }
    },
    
    # Email tools
    {
        "type": "function",
        "function": {
            "name": "email_send",
            "description": "Send an email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    
    # File Explorer tools
    {
        "type": "function",
        "function": {
            "name": "explorer_open",
            "description": "Open Windows File Explorer.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "explorer_downloads",
            "description": "Open the Downloads folder in File Explorer.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "explorer_documents",
            "description": "Open the Documents folder in File Explorer.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "explorer_desktop",
            "description": "Open the Desktop folder in File Explorer.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "explorer_pictures",
            "description": "Open the Pictures folder in File Explorer.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "explorer_navigate",
            "description": "Navigate to a specific folder path in File Explorer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Folder path to navigate to (e.g., 'C:\\Users\\John\\Projects')"}
                },
                "required": ["path"]
            }
        }
    },
    
    # Local file search
    {
        "type": "function",
        "function": {
            "name": "local_search",
            "description": "Search for files on the local computer by name or content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (filename or content to search for)"}
                },
                "required": ["query"]
            }
        }
    },
    
    # Vision/OCR tools
    {
        "type": "function",
        "function": {
            "name": "vision_describe",
            "description": "Use AI to describe what's shown in an image or the current screen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "Path to image file. If empty, captures current screen."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ocr_read_screen",
            "description": "Read and extract all text from the current screen using OCR.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ocr_read_image",
            "description": "Read and extract text from an image file using OCR.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "Path to the image file"}
                },
                "required": ["image_path"]
            }
        }
    },
    
    # File delete/archive
    {
        "type": "function",
        "function": {
            "name": "filesystem_delete_file",
            "description": "Delete a file (moves to archive by default for safety).",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the file to delete"}
                },
                "required": ["filename"]
            }
        }
    },
    
    # Conversation/clarification (special)
    {
        "type": "function",
        "function": {
            "name": "ask_clarification",
            "description": "Ask the user for clarification when the request is ambiguous or unclear.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The clarifying question to ask"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Suggested options for the user to choose from"
                    }
                },
                "required": ["question"]
            }
        }
    },
    
    # Pure conversation (no action needed)
    {
        "type": "function",
        "function": {
            "name": "respond_conversationally",
            "description": "Respond to the user conversationally when no action is needed. Use for greetings, questions about yourself, advice, opinions, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "response": {"type": "string", "description": "Your conversational response to the user"}
                },
                "required": ["response"]
            }
        }
    },
    
    # User profile management
    {
        "type": "function",
        "function": {
            "name": "update_user_profile",
            "description": "Update information about the user when they tell you their name, preferences, or correct previous information. Use this whenever the user shares personal info like 'my name is X', 'I'm X', 'call me X', 'I prefer X', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "User's actual name"},
                    "nickname": {"type": "string", "description": "What to call the user (if different from name)"},
                    "response": {"type": "string", "description": "Your response acknowledging the update"}
                },
                "required": ["response"]
            }
        }
    },
    
    # Contact relationship management
    {
        "type": "function",
        "function": {
            "name": "set_contact_relationship",
            "description": "Remember a relationship the user tells you about. Use when user says things like '[Name] is my [relationship]', 'my friend [Name]', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string", "description": "Name of the contact"},
                    "relationship_type": {"type": "string", "description": "Type of relationship (friend, family, colleague, boss, ex, etc.)"},
                    "notes": {"type": "string", "description": "Any notes about this person"},
                    "response": {"type": "string", "description": "Your response acknowledging you've remembered this"}
                },
                "required": ["contact_name", "relationship_type", "response"]
            }
        }
    }
]


class SmartExecutor:
    """
    Executes user requests using LLM function calling instead of regex parsing.
    
    Flow:
    1. User request + context → LLM with function calling
    2. LLM returns structured function call (or asks for clarification)
    3. Execute the function
    4. Return result with personality
    
    Now with enhanced personality and relationship awareness!
    """
    
    def __init__(self, llm, router, memory=None, vector_memory=None):
        """
        Initialize the smart executor.
        
        Args:
            llm: The LLM (GroqLLM) for function calling
            router: The action router for executing functions
            memory: SQLite memory for conversation history
            vector_memory: Vector memory for semantic search
        """
        self.llm = llm
        self.router = router
        self.memory = memory
        self.vector_memory = vector_memory
        
        # Import personality module
        from .personality import KAYAS_SYSTEM_PROMPT, create_contextual_prompt, detect_mood_indicators, get_contact_warning
        self.base_personality_prompt = KAYAS_SYSTEM_PROMPT
        self._create_contextual_prompt = create_contextual_prompt
        self._detect_mood = detect_mood_indicators
        self._get_contact_warning = get_contact_warning
        
        # Initialize user profile manager
        self._profile_manager = None
        try:
            from ..memory.user_profile import get_profile_manager
            self._profile_manager = get_profile_manager()
        except Exception as e:
            print(f"[SmartExecutor] Could not load user profile: {e}")
        
        # Initialize profile commands handler
        self._profile_commands = None
        try:
            from .profile_commands import get_profile_commands
            self._profile_commands = get_profile_commands()
        except Exception as e:
            print(f"[SmartExecutor] Could not load profile commands: {e}")
        
        # Initialize session continuity
        self._session_continuity = None
        try:
            from ..memory.session_continuity import get_session_continuity
            self._session_continuity = get_session_continuity(memory, self._profile_manager)
        except Exception as e:
            print(f"[SmartExecutor] Could not load session continuity: {e}")
    
    @property
    def profile_manager(self):
        """Lazy-load profile manager."""
        if self._profile_manager is None:
            try:
                from ..memory.user_profile import get_profile_manager
                self._profile_manager = get_profile_manager()
            except Exception:
                pass
        return self._profile_manager
    
    def _get_relevant_context(self, request: str) -> str:
        """
        Get relevant context from memory for this request.
        
        Priority 3: Memory-Driven Context
        """
        context_parts = []
        
        # Get recent conversation history
        if self.memory:
            try:
                recent = self.memory.get_recent_messages(limit=10)
                if recent:
                    context_parts.append("Recent conversation:")
                    for msg in recent[-5:]:  # Last 5 messages
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")[:200]  # Truncate
                        context_parts.append(f"  {role}: {content}")
            except Exception:
                pass
        
        # Get semantically relevant memories
        if self.vector_memory:
            try:
                relevant = self.vector_memory.search(request, top_k=3)
                if relevant:
                    context_parts.append("\nRelevant past context:")
                    for item in relevant:
                        if isinstance(item, dict):
                            content = item.get("content", str(item))[:150]
                        else:
                            content = str(item)[:150]
                        context_parts.append(f"  - {content}")
            except Exception:
                pass
        
        return "\n".join(context_parts) if context_parts else ""
    
    def _build_system_prompt(self, context: str, user_request: str = "") -> str:
        """Build the full system prompt with personality, profile, and context."""
        # Use enhanced contextual prompt if profile manager is available
        if self.profile_manager and user_request:
            prompt = self._create_contextual_prompt(
                user_message=user_request,
                profile_manager=self.profile_manager
            )
        else:
            prompt = self.base_personality_prompt
        
        prompt += "\n\n"
        
        # Add session continuity context (helps LLM know relationship history)
        if self._session_continuity:
            try:
                session_ctx = self._session_continuity.get_context_for_prompt()
                if session_ctx:
                    prompt += f"## Relationship with this user:\n{session_ctx}\n\n"
            except Exception:
                pass
        
        if context:
            prompt += f"## Context from past conversations:\n{context}\n\n"
        
        prompt += """## Important Instructions:
- If the request is clear, use the appropriate function to execute it
- If the request is ambiguous or unclear, use ask_clarification to ask the user
- If no action is needed (greeting, question, advice), use respond_conversationally
- Never guess when unsure - ask for clarification instead
- Remember past context when making decisions
- Give your honest opinion when asked for advice
- Be helpful but also be a friend who cares
- If messaging someone, check relationship context and warn about late-night or emotional messages"""
        
        return prompt
    
    def execute(self, request: str, conversation_history: str = "") -> ExecutionResult:
        """
        Execute a user request using function calling.
        
        This is the main entry point that replaces regex-based parsing.
        
        Args:
            request: The user's request
            conversation_history: Recent conversation for context
        
        Returns:
            ExecutionResult with success status and response
        """
        # ========== Profile Commands (shortcut) ==========
        # Handle profile/relationship commands directly without LLM
        if self._profile_commands:
            profile_response = self._profile_commands.process_command(request)
            if profile_response:
                return ExecutionResult(
                    success=True,
                    response=profile_response,
                    action_taken={"type": "profile_command"}
                )
        
        # Detect mood for emotional awareness
        mood = self._detect_mood(request)
        if mood and self.profile_manager:
            self.profile_manager.log_mood(mood, 0.7, request[:100])
        
        # Priority 3: Get relevant memory context
        memory_context = self._get_relevant_context(request)
        full_context = f"{conversation_history}\n{memory_context}" if memory_context else conversation_history
        
        # Build system prompt with personality, profile, and context
        system_prompt = self._build_system_prompt(full_context, user_request=request)
        
        try:
            # Priority 1: Use function calling instead of regex
            result = self.llm.generate_with_functions(
                prompt=request,
                system=system_prompt,
                tools=TOOL_DEFINITIONS,
                temperature=0.3  # Lower temperature for more consistent tool selection
            )
            
            if result.get("type") == "function_call":
                return self._handle_function_call(result["function"], request)
            else:
                # LLM responded with text (conversational response)
                text = result.get("text", "I'm not sure how to help with that. Could you rephrase?")
                # Strip thinking tags for clean output
                text = self._strip_thinking_tags(text)
                return ExecutionResult(
                    success=True,
                    response=text
                )
        
        except Exception as e:
            # Priority 4: Better error recovery
            return self._handle_error(str(e), request)
    
    def _handle_function_call(self, function_call: Dict[str, Any], original_request: str) -> ExecutionResult:
        """
        Handle a function call from the LLM.
        
        Args:
            function_call: The function call from LLM {name, arguments}
            original_request: Original user request for context
        
        Returns:
            ExecutionResult with the outcome
        """
        func_name = function_call.get("name", "")
        args_str = function_call.get("arguments", "{}")
        
        # Normalize function names - handle model variations
        # Some models use dots instead of underscores, or different naming patterns
        func_name_aliases = {
            "browser.search": "browser_search",
            "web.search": "web_search",
            "filesystem.create_file": "filesystem_create_file",
            "filesystem.append_file": "filesystem_append_file",
            "process.start_program": "process_start_program",
            "process.list": "process_list",
            "clipboard.copy": "clipboard_copy",
            "clipboard.paste": "clipboard_paste",
            "explorer.open": "explorer_open",
            "explorer.navigate": "explorer_navigate",
        }
        func_name = func_name_aliases.get(func_name, func_name)
        
        # Parse arguments
        try:
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
        except json.JSONDecodeError:
            args = {}
        
        # Handle special functions
        if func_name == "ask_clarification":
            # Priority 2: Ask for clarification instead of perception engine
            return ExecutionResult(
                success=True,
                response=args.get("question", "Could you clarify what you'd like me to do?"),
                needs_clarification=True,
                clarification_options=args.get("options", [])
            )
        
        if func_name == "respond_conversationally":
            # Pure conversation, no action
            # Strip any thinking tags from the response
            response = args.get("response", "")
            response = self._strip_thinking_tags(response)
            return ExecutionResult(
                success=True,
                response=response,
                action_taken={"type": "conversation"}
            )
        
        # Handle profile updates from LLM
        if func_name == "update_user_profile":
            return self._handle_profile_update(args)
        
        if func_name == "set_contact_relationship":
            return self._handle_set_relationship(args)
        
        
        # Map function names to tool calls
        tool_mapping = {
            "filesystem_create_file": ("filesystem.create_file", {"filename": args.get("filename"), "content": args.get("content", "")}),
            "filesystem_append_file": ("filesystem.append_file", {"filename": args.get("filename"), "content": args.get("content")}),
            "filesystem_create_folder": ("filesystem.create_folder", {"path": args.get("path")}),
            "filesystem_rename": ("filesystem.rename", {"path": args.get("path"), "new_name": args.get("new_name")}),
            "filesystem_delete_file": ("filesystem.delete_file", {"filename": args.get("filename")}),
            "web_search": ("web.search", {"query": args.get("query"), "max_results": args.get("max_results", 5)}),
            "web_deep_research": ("web.deep_research", {"question": args.get("question"), "max_sources": args.get("max_sources", 8)}),
            "web_fetch_page": ("web.fetch", {"url": args.get("url")}),
            "browser_open": ("browser.open_url", {"url": args.get("url")}),
            "browser_search": ("web.search", {"query": args.get("query"), "max_results": 5}),  # Use web.search for browser search
            "process_start_program": ("process.start_program", {"program": args.get("program"), "args": args.get("args", [])}),
            "process_list": ("process.list", {"filter": args.get("filter")}),
            "process_kill": ("process.kill", {"name": args.get("name")}),
            "clipboard_copy": ("clipboard.copy_text", {"text": args.get("text")}),
            "clipboard_paste": ("clipboard.paste_text", {}),
            "system_info": ("process.get_system_info", {}),
            "whatsapp_send_message": ("whatsapp.send_message", {"contact": args.get("contact"), "message": args.get("message")}),
            "calendar_list_events": ("calendar.list_events", {"days_ahead": args.get("days_ahead", 7)}),
            "calendar_create_event": ("calendar.create_event", args),
            "spotify_play": ("spotify.play_query", {"query": args.get("query")}),
            "spotify_pause": ("spotify.pause", {}),
            "desktop_screenshot": ("desktop.screenshot", {"filename": args.get("filename", "screenshot.png")}),
            "email_send": ("email.send", {"to": args.get("to"), "subject": args.get("subject"), "body": args.get("body")}),
            # Explorer tools
            "explorer_open": ("explorer.open", {}),
            "explorer_downloads": ("explorer.downloads", {}),
            "explorer_documents": ("explorer.documents", {}),
            "explorer_desktop": ("explorer.desktop", {}),
            "explorer_pictures": ("explorer.pictures", {}),
            "explorer_navigate": ("explorer.navigate", {"path": args.get("path")}),
            # Local search
            "local_search": ("local.search", {"query": args.get("query")}),
            # Vision/OCR
            "vision_describe": ("vision.describe", {"image_path": args.get("image_path", "")}),
            "ocr_read_screen": ("ocr.read_screen", {}),
            "ocr_read_image": ("ocr.read_file", {"image_path": args.get("image_path")}),
        }
        
        if func_name not in tool_mapping:
            return ExecutionResult(
                success=False,
                response=f"I don't know how to execute '{func_name}'. Could you try asking differently?",
                error=f"Unknown function: {func_name}"
            )
        
        tool, tool_args = tool_mapping[func_name]
        
        # ========== Relationship Awareness for Messaging ==========
        # Check for messaging actions and apply relationship context
        messaging_functions = ["whatsapp_send_message", "email_send"]
        if func_name in messaging_functions:
            contact_name = tool_args.get("contact") or tool_args.get("to", "")
            message_content = tool_args.get("message") or tool_args.get("body", "")
            
            # Check relationship and potentially warn
            warning = self._check_messaging_context(contact_name, message_content)
            if warning:
                # Return warning instead of sending - let user confirm
                return ExecutionResult(
                    success=True,
                    response=warning,
                    needs_clarification=True,
                    action_taken={"type": "messaging_warning", "contact": contact_name}
                )
            
            # Update contact interaction stats
            if self.profile_manager:
                self.profile_manager.update_contact_interaction(contact_name)
        
        # Execute the action through the router
        try:
            action_result = self.router.route({
                "tool": tool,
                "args": tool_args
            })
            
            # Generate a friendly response based on the result
            response = self._generate_response(func_name, tool_args, action_result, original_request)
            
            return ExecutionResult(
                success=not action_result.get("error"),
                response=response,
                action_taken={"function": func_name, "args": tool_args, "result": action_result},
                error=action_result.get("error")
            )
        
        except Exception as e:
            # Priority 4: Error recovery with LLM suggestion
            return self._handle_error(str(e), original_request, func_name, tool_args)
    
    def _strip_thinking_tags(self, text: str) -> str:
        """Remove Qwen3 <think>...</think> blocks from text."""
        if not text:
            return text
        import re
        cleaned = re.sub(r'<think>.*?</think>\s*', '', text, flags=re.DOTALL)
        return cleaned.strip()
    
    def _check_messaging_context(self, contact_name: str, message: str) -> Optional[str]:
        """
        Check messaging context for relationship awareness.
        Returns a warning string if the user should be cautioned, None otherwise.
        """
        if not self.profile_manager or not contact_name:
            return None
        
        contact = self.profile_manager.get_contact(contact_name)
        if not contact:
            return None  # Unknown contact, no warning
        
        # Get warning based on relationship type
        warning = self._get_contact_warning(
            relationship_type=contact.relationship_type,
            contact_name=contact_name,
            situation="default"  # Will auto-detect late night
        )
        
        # Add caution-level specific warnings
        if contact.caution_level == "warn":
            if contact.caution_reason:
                warning = f"⚠️ {contact.caution_reason}\n\n{warning or 'You sure you want to send this?'}"
            else:
                warning = warning or "Just checking - you sure about this?"
        
        elif contact.caution_level == "block":
            return f"🛑 I won't send this. {contact.caution_reason or 'You told me not to let you message this person.'}"
        
        # Check for late night + avoid_late_night flag
        from .personality import get_time_context
        if get_time_context() == "late_night" and contact.avoid_late_night:
            warning = f"It's late... you sure you want to message {contact_name} right now? Maybe sleep on it?"
        
        return warning
    
    def _handle_profile_update(self, args: Dict) -> ExecutionResult:
        """Handle profile update from LLM."""
        if not self.profile_manager:
            response = args.get("response", "Got it!")
            return ExecutionResult(success=True, response=response)
        
        # Update profile with provided fields
        update_kwargs = {}
        if args.get("name"):
            update_kwargs["name"] = args["name"]
        if args.get("nickname"):
            update_kwargs["nickname"] = args["nickname"]
        
        if update_kwargs:
            self.profile_manager.update_profile(**update_kwargs)
            # Also set nickname to name if not specified separately
            if "name" in update_kwargs and "nickname" not in update_kwargs:
                self.profile_manager.update_profile(nickname=update_kwargs["name"])
        
        response = self._strip_thinking_tags(args.get("response", "Got it! I'll remember that."))
        return ExecutionResult(
            success=True,
            response=response,
            action_taken={"type": "profile_update", "updates": update_kwargs}
        )
    
    def _handle_set_relationship(self, args: Dict) -> ExecutionResult:
        """Handle setting a contact relationship from LLM."""
        if not self.profile_manager:
            response = args.get("response", "Noted!")
            return ExecutionResult(success=True, response=response)
        
        contact_name = args.get("contact_name", "")
        relationship_type = args.get("relationship_type", "")
        notes = args.get("notes", "")
        
        if contact_name and relationship_type:
            from ..memory.user_profile import ContactRelationship
            
            # Check if contact exists
            contact = self.profile_manager.get_contact(contact_name)
            if contact:
                contact.relationship_type = relationship_type
                if notes:
                    contact.notes = notes
            else:
                contact = ContactRelationship(
                    name=contact_name,
                    relationship_type=relationship_type,
                    notes=notes
                )
                
                # Set default flags for certain relationship types
                if relationship_type.lower() in ["ex", "ex-girlfriend", "ex-boyfriend"]:
                    contact.sentiment = "complicated"
                    contact.caution_level = "gentle"
                    contact.avoid_late_night = True
            
            self.profile_manager.set_contact(contact)
        
        response = self._strip_thinking_tags(args.get("response", "I'll remember that!"))
        return ExecutionResult(
            success=True,
            response=response,
            action_taken={"type": "set_relationship", "contact": contact_name, "relationship": relationship_type}
        )
    
    def _generate_response(self, func_name: str, args: Dict, result: Dict, original_request: str) -> str:
        """Generate a friendly response for the action result."""
        
        # Handle None result
        if result is None:
            result = {}
        
        # Check for errors first
        if result.get("error"):
            return f"I tried to do that but ran into an issue: {result['error']}. Would you like me to try something else?"
        
        # Generate responses based on function type
        responses = {
            "filesystem_create_file": lambda: f"Done! I created the file '{args.get('filename')}' for you.",
            "filesystem_append_file": lambda: f"Added that content to '{args.get('filename')}'.",
            "filesystem_create_folder": lambda: f"Created the folder '{args.get('path')}'.",
            "filesystem_rename": lambda: f"Renamed '{args.get('path')}' to '{args.get('new_name')}'.",
            "filesystem_delete_file": lambda: f"Deleted '{args.get('filename')}'.",
            "web_search": lambda: self._format_search_results(result),
            "web_deep_research": lambda: result.get("answer", "Here's what I found from my research."),
            "browser_open": lambda: f"Opened {args.get('url')} in your browser.",
            "browser_search": lambda: f"Searching for '{args.get('query')}' in your browser.",
            "process_start_program": lambda: f"Started {args.get('program')} for you.",
            "clipboard_copy": lambda: f"Copied that to your clipboard: \"{args.get('text')[:50]}{'...' if len(args.get('text', '')) > 50 else ''}\"",
            "clipboard_paste": lambda: f"Here's what's in your clipboard: {result.get('text', 'Nothing found')}",
            "whatsapp_send_message": lambda: f"Message sent to {args.get('contact')}!",
            "spotify_play": lambda: f"Playing '{args.get('query')}' on Spotify for you.",
            "desktop_screenshot": lambda: f"Took a screenshot and saved it.",
            "email_send": lambda: f"Email sent to {args.get('to')}!",
            # Explorer responses
            "explorer_open": lambda: "Opened File Explorer for you.",
            "explorer_downloads": lambda: "Opened your Downloads folder.",
            "explorer_documents": lambda: "Opened your Documents folder.",
            "explorer_desktop": lambda: "Opened your Desktop folder.",
            "explorer_pictures": lambda: "Opened your Pictures folder.",
            "explorer_navigate": lambda: f"Opened '{args.get('path')}' in File Explorer.",
            # Local search
            "local_search": lambda: self._format_local_search_results(result),
            # Vision/OCR
            "vision_describe": lambda: result.get("description", "Here's what I see in the image."),
            "ocr_read_screen": lambda: f"I read the screen. Here's the text:\n\n{result.get('text', 'No text found')[:500]}",
            "ocr_read_image": lambda: f"I read the image. Here's the text:\n\n{result.get('text', 'No text found')[:500]}",
        }
        
        generator = responses.get(func_name)
        if generator:
            try:
                return generator()
            except Exception:
                pass
        
        # Default response
        if result.get("success"):
            return "Done! Anything else?"
        return "I completed that for you."
    
    def _format_search_results(self, result: Dict) -> str:
        """Format search results nicely."""
        results = result.get("results", [])
        if not results:
            return "I searched but didn't find any relevant results."
        
        formatted = "Here's what I found:\n\n"
        for i, r in enumerate(results[:5], 1):
            title = r.get("title", "Untitled")
            snippet = r.get("snippet", r.get("description", ""))[:100]
            formatted += f"{i}. **{title}**\n   {snippet}\n\n"
        
        return formatted
    
    def _format_local_search_results(self, result: Dict) -> str:
        """Format local file search results nicely."""
        results = result.get("results", [])
        if not results:
            return "I searched your files but didn't find any matches."
        
        formatted = f"Found {len(results)} file(s):\n\n"
        for i, r in enumerate(results[:10], 1):
            if isinstance(r, dict):
                path = r.get("path", str(r))
            else:
                path = str(r)
            # Get just the filename
            filename = path.split("\\")[-1].split("/")[-1]
            formatted += f"{i}. {filename}\n"
        
        if len(results) > 10:
            formatted += f"\n...and {len(results) - 10} more files."
        
        return formatted
    
    def _handle_error(self, error: str, request: str, func_name: str = None, args: Dict = None) -> ExecutionResult:
        """
        Handle errors with LLM-suggested recovery.
        
        Priority 4: Better Error Recovery
        """
        # Ask LLM for recovery suggestion
        recovery_prompt = f"""The user requested: "{request}"
I tried to execute this but got an error: {error}

What should I tell the user? Suggest an alternative or ask for more information.
Be helpful and conversational, not technical."""
        
        try:
            recovery_response = self.llm.generate(
                recovery_prompt,
                system="You are a helpful assistant. Suggest a friendly recovery from an error.",
                temperature=0.7
            )
            
            return ExecutionResult(
                success=False,
                response=recovery_response,
                error=error
            )
        except Exception:
            # Fallback if LLM also fails
            return ExecutionResult(
                success=False,
                response=f"I had trouble with that. Could you try asking in a different way? (Error: {error[:100]})",
                error=error
            )
