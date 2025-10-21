"""
Direct agent wrapper that integrates all tools without HTTP calls.
"""
from __future__ import annotations

from typing import Dict, Any, List
from pathlib import Path
import uuid

from ..agent.config import (
    artifacts_dir, db_path, ollama_model, chroma_dir, embed_model, 
    search_root, smtp_config, google_calendar_config, slack_config, 
    spotify_config, desktop_enabled
)
from ..agent.llm import LLM
from ..agent.planner import Planner
from ..agent.actions import Router
from ..executors.filesystem import FSConfig, FileSystemExecutor
from ..executors.local_search import LocalSearchConfig, LocalSearchExecutor
from ..executors.email_exec import EmailConfig, EmailExecutor
from ..executors.web_exec import WebConfig, WebExecutor
from ..executors.browser_exec import BrowserExecutor, BrowserConfig
from ..executors.desktop_exec import DesktopExecutor, DesktopConfig
from ..executors.calendar_exec import GoogleCalendarExecutor, CalendarConfig
from ..executors.slack_exec import SlackExecutor, SlackConfig
from ..executors.spotify_exec import SpotifyExecutor, SpotifyConfig
from ..memory.sqlite_memory import MemoryConfig, SQLiteMemory
from ..memory.vector_memory import VectorMemory, VectorMemoryConfig


class DirectAgent:
    """Agent that can execute tools directly without HTTP API calls."""
    
    def __init__(self):
        # Initialize LLM and planner
        self.llm = LLM(model=ollama_model())
        self.planner = Planner(self.llm)
        
        # Initialize executors
        self.fs = FileSystemExecutor(FSConfig(root=artifacts_dir()))
        self.local_search = LocalSearchExecutor(LocalSearchConfig(root=search_root()))
        self.email_exec = EmailExecutor(EmailConfig(**smtp_config()))
        self.web_exec = WebExecutor(WebConfig())
        self.browser_exec = BrowserExecutor(BrowserConfig())
        
        # Desktop executor (if enabled)
        self.desktop_exec = DesktopExecutor(DesktopConfig()) if desktop_enabled() else None
        
        # API integrations - only create if credentials are available
        try:
            self.calendar_exec = GoogleCalendarExecutor(CalendarConfig(**google_calendar_config()))
        except Exception:
            self.calendar_exec = None
            
        try:
            self.slack_exec = SlackExecutor(SlackConfig(**slack_config()))
        except Exception:
            self.slack_exec = None
            
        try:
            self.spotify_exec = SpotifyExecutor(SpotifyConfig(**spotify_config()))
        except Exception:
            self.spotify_exec = None
        
        # Initialize router
        self.router = Router({
            "filesystem": self.fs,
            "local_search": self.local_search, 
            "email": self.email_exec,
            "web": self.web_exec,
            "browser": self.browser_exec,
            "desktop": self.desktop_exec,
            "calendar": self.calendar_exec,
            "slack": self.slack_exec,
            "spotify": self.spotify_exec,
        })
        
        # Initialize memory
        self.memory = SQLiteMemory(MemoryConfig(db_path=db_path()))
        self.vmem = VectorMemory(VectorMemoryConfig(
            persist_dir=chroma_dir(),
            embed_model=embed_model()
        ))

    def run(self, goal: str) -> Dict[str, Any]:
        """Run the agent with a goal and return a conversational response."""
        run_id = str(uuid.uuid4())
        self.memory.log_message(run_id, "user", goal)
        
        try:
            # Check if this is a simple question or requires action
            is_simple = self._is_simple_question(goal)
            print(f"DEBUG: Goal '{goal}' classified as simple question: {is_simple}")
            
            if is_simple:
                response = self._handle_simple_question(goal)
                self.memory.log_message(run_id, "assistant", response)
                return {
                    "response": response,
                    "run_id": run_id,
                    "type": "conversation"
                }
            
            # Special handling for screen requests
            goal_lower = goal.lower()
            if any(word in goal_lower for word in ["screen", "screenshot"]) and self.desktop_exec:
                print("DEBUG: Handling screen request directly")
                try:
                    result = self.desktop_exec.run_steps([
                        {"action": "screenshot", "args": {"filename": "current_screen.png"}}
                    ])
                    
                    if result.get("success"):
                        screenshots = result.get("screenshots", [])
                        if screenshots:
                            response = f"I took a screenshot of your screen and saved it at {screenshots[0]}. I can see what's currently displayed. What would you like me to do next?"
                        else:
                            response = "I took a screenshot of your screen. I can see what's currently displayed. What would you like me to do next?"
                    else:
                        response = "I tried to take a screenshot but encountered an issue. Please make sure desktop automation is enabled."
                    
                    self.memory.log_message(run_id, "assistant", response)
                    return {
                        "response": response,
                        "run_id": run_id,
                        "type": "action",
                        "results": [result]
                    }
                except Exception as e:
                    response = f"I had trouble taking a screenshot: {str(e)}"
                    self.memory.log_message(run_id, "assistant", response)
                    return {
                        "response": response,
                        "run_id": run_id,
                        "type": "error",
                        "error": str(e)
                    }
            
            # For action requests, use the planner
            from ..agent.planner import plan_structured
            plan_result = plan_structured(self.llm, goal)
            plan = {"actions": plan_result[0]} if plan_result[0] else None
            
            if not plan or not plan.get("actions"):
                response = "I'm not sure how to help with that. Could you be more specific?"
                self.memory.log_message(run_id, "assistant", response)
                return {
                    "response": response,
                    "run_id": run_id,
                    "type": "conversation"
                }
            
            # Execute the plan
            results = []
            for action_data in plan["actions"]:
                try:
                    result = self.router.route(action_data)
                    results.append(result)
                except Exception as e:
                    error_msg = f"Error executing {action_data.get('action', 'unknown')}: {str(e)}"
                    results.append({"error": error_msg})
            
            # Generate a conversational response based on results
            response = self._generate_response(goal, results)
            
            self.memory.log_message(run_id, "assistant", response)
            
            return {
                "response": response,
                "run_id": run_id,
                "type": "action",
                "results": results
            }
            
        except Exception as e:
            error_response = f"I encountered an error: {str(e)}"
            self.memory.log_message(run_id, "assistant", error_response)
            return {
                "response": error_response,
                "run_id": run_id,
                "type": "error",
                "error": str(e)
            }

    def _is_simple_question(self, goal: str) -> bool:
        """Check if this is a simple question that doesn't require actions."""
        goal_lower = goal.lower()
        
        # Screen-related requests are always actions, not simple questions
        if any(word in goal_lower for word in ["screen", "screenshot", "desktop", "display"]):
            return False
        
        # If it contains action words, it's probably not a simple question
        action_words = ["take", "click", "open", "create", "send", "play", "stop", "start", "go to", "navigate", "show me"]
        for word in action_words:
            if word in goal_lower:
                return False
        
        # Greetings and help requests are simple questions
        if any(word in goal_lower for word in ["hello", "hi", "hey", "help", "what can you do"]):
            return True
        
        # Questions starting with question words might be simple questions
        question_words = ["what", "how", "why", "when", "where", "who", "can you", "do you"]
        for word in question_words:
            if goal_lower.startswith(word):
                # But only if they don't contain action words
                return not any(action in goal_lower for action in action_words)
                
        return False

    def _handle_simple_question(self, goal: str) -> str:
        """Handle simple questions with direct responses."""
        goal_lower = goal.lower()
        
        if any(word in goal_lower for word in ["hello", "hi", "hey"]):
            return "Hello! I'm Kayas, your AI assistant. I can help you with desktop automation, web browsing, managing your calendar, playing music, and much more. What would you like me to do?"
        
        if any(word in goal_lower for word in ["what can you do", "help", "capabilities"]):
            return """I can help you with many tasks:

🖥️ Desktop Control:
- Take screenshots and analyze your screen
- Click on buttons, text, or images
- Type text and use keyboard shortcuts
- Control windows and applications

🌐 Web Browsing:
- Visit websites and interact with forms
- Fill out forms and submit data
- Take screenshots of web pages

📅 Productivity:
- Manage Google Calendar events
- Send Slack messages
- Control Spotify playback
- Send emails

📁 File Management:
- Create and edit files
- Search your local files

Just tell me what you'd like to do! For example:
- "Take a screenshot"
- "Go to Google and search for Python"
- "Create a calendar event for tomorrow"
- "Play some music"
"""
        
        if "screen" in goal_lower and any(word in goal_lower for word in ["what", "show", "see"]):
            if self.desktop_exec:
                # This should be handled as an action, not a simple question
                # But provide a fallback response
                return "I can take a screenshot to see your screen. Let me do that for you."
            else:
                return "Desktop automation is not enabled. To see your screen, please enable it by setting DESKTOP_AUTOMATION_ENABLED=1"
        
        # Use the LLM for other questions
        try:
            response = self.llm.generate(f"Answer this question briefly and helpfully: {goal}")
            return response
        except Exception:
            return "I'm not sure how to answer that. Could you try asking something else or give me a specific task to perform?"

    def _generate_response(self, goal: str, results: List[Dict[str, Any]]) -> str:
        """Generate a conversational response based on action results."""
        if not results:
            return "I completed the task, but didn't get any specific results to report."
        
        # Count successful vs failed actions
        successful = [r for r in results if r.get("success", True) and "error" not in r]
        failed = [r for r in results if not r.get("success", True) or "error" in r]
        
        if failed and not successful:
            # All failed
            error_msg = failed[0].get("error", "Unknown error")
            return f"I had trouble completing that task: {error_msg}"
        
        if successful and not failed:
            # All successful
            response_parts = []
            
            for result in successful:
                action = result.get("action", "")
                
                if "screenshot" in action:
                    screenshots = result.get("screenshots", [])
                    if screenshots:
                        response_parts.append(f"I took a screenshot and saved it at {screenshots[0]}")
                    else:
                        response_parts.append("I took a screenshot")
                
                elif "click" in action:
                    response_parts.append("I clicked as requested")
                
                elif "web.fetch" in action:
                    title = result.get("title", "")
                    if title:
                        response_parts.append(f"I fetched the webpage: {title}")
                    else:
                        response_parts.append("I fetched the webpage")
                
                elif "filesystem" in action:
                    path = result.get("path", "")
                    if path:
                        response_parts.append(f"I created a file at {path}")
                    else:
                        response_parts.append("I completed the file operation")
                
                elif "browser" in action:
                    response_parts.append("I completed the browser automation")
                
                else:
                    response_parts.append("I completed the requested action")
            
            if response_parts:
                return " and ".join(response_parts) + "."
            else:
                return "Task completed successfully!"
        
        # Mixed results
        return f"I completed {len(successful)} actions successfully, but had {len(failed)} issues. The task was partially completed."