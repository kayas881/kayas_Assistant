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
    spotify_config, desktop_enabled, github_config, notion_config,
    trello_config, jira_config
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
from ..executors.process_exec import ProcessExecutor, ProcessConfig
from ..executors.clipboard_exec import ClipboardExecutor, ClipboardConfig
from ..executors.network_exec import NetworkExecutor, NetworkConfig
from ..executors.filewatcher_exec import FileWatcherExecutor, WatcherConfig
from ..executors.github_exec import GithubExecutor, GithubConfig
from ..executors.notion_exec import NotionExecutor, NotionConfig
from ..executors.trello_exec import TrelloExecutor, TrelloConfig
from ..executors.jira_exec import JiraExecutor, JiraConfig
from ..executors.image_exec import ImageProcessingExecutor, ImageConfig
from ..executors.audio_exec import AudioExecutor, AudioConfig
from ..executors.video_exec import VideoExecutor, VideoConfig
from ..executors.vision_exec import VisionExecutor, VisionConfig
from ..executors.llm_exec import LLMExecutor, LLMConfig
from ..executors.uiautomation_exec import UIAutomationExecutor, UIAutomationConfig
from ..executors.ocr_exec import OCRExecutor, OCRConfig
from ..executors.cv_exec import CVExecutor, CVConfig
from ..executors.perception_engine import PerceptionEngine, PerceptionConfig
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
        
        # System executors (always available)
        self.process_exec = ProcessExecutor(ProcessConfig())
        self.clipboard_exec = ClipboardExecutor(ClipboardConfig())
        self.network_exec = NetworkExecutor(NetworkConfig())
        self.filewatcher_exec = FileWatcherExecutor(WatcherConfig())
        
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
        
        # Productivity integrations (optional - require API keys)
        try:
            cfg = github_config()
            if cfg.get("token"):
                self.github_exec = GithubExecutor(GithubConfig(**cfg))
            else:
                self.github_exec = None
        except Exception:
            self.github_exec = None
            
        try:
            cfg = notion_config()
            if cfg.get("token"):
                self.notion_exec = NotionExecutor(NotionConfig(**cfg))
            else:
                self.notion_exec = None
        except Exception:
            self.notion_exec = None
            
        try:
            cfg = trello_config()
            if cfg.get("api_key") and cfg.get("token"):
                self.trello_exec = TrelloExecutor(TrelloConfig(**cfg))
            else:
                self.trello_exec = None
        except Exception:
            self.trello_exec = None
            
        try:
            cfg = jira_config()
            if cfg.get("url") and cfg.get("email") and cfg.get("api_token"):
                self.jira_exec = JiraExecutor(JiraConfig(**cfg))
            else:
                self.jira_exec = None
        except Exception:
            self.jira_exec = None
        
        # Media processing executors (always available)
        self.image_exec = ImageProcessingExecutor(ImageConfig())
        self.audio_exec = AudioExecutor(AudioConfig())
        self.video_exec = VideoExecutor(VideoConfig())
        
        # AI/ML executors (always available if Ollama is running)
        self.vision_exec = VisionExecutor(VisionConfig())
        self.llm_exec = LLMExecutor(LLMConfig())
        
        # Phase 1: Multi-layer perception executors
        try:
            self.uia_exec = UIAutomationExecutor(UIAutomationConfig())
        except Exception:
            self.uia_exec = None
            
        try:
            self.ocr_exec = OCRExecutor(OCRConfig())
        except Exception:
            self.ocr_exec = None
        
        try:
            self.cv_exec = CVExecutor(CVConfig())
        except Exception:
            self.cv_exec = None
            
        try:
            self.perception = PerceptionEngine(PerceptionConfig())
        except Exception:
            self.perception = None
        
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
            "process": self.process_exec,
            "clipboard": self.clipboard_exec,
            "network": self.network_exec,
            "filewatcher": self.filewatcher_exec,
            "github": self.github_exec,
            "notion": self.notion_exec,
            "trello": self.trello_exec,
            "jira": self.jira_exec,
            "image": self.image_exec,
            "audio": self.audio_exec,
            "video": self.video_exec,
            "vision": self.vision_exec,
            "llm": self.llm_exec,
            "uia": self.uia_exec,
            "ocr": self.ocr_exec,
            "cv": self.cv_exec,
            "perception": self.perception,
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
            
            # Add heuristic handling for common requests before calling LLM
            goal_lower = goal.lower()
            heuristic_plan = None
            
            if "cpu" in goal_lower or "memory" in goal_lower or "system" in goal_lower:
                heuristic_plan = [{"tool": "process.get_system_info", "args": {}}]
            elif "copy" in goal_lower:
                # Extract text to copy
                import re
                match = re.search(r"'([^']+)'|\"([^\"]+)\"", goal)
                if match:
                    text = match.group(1) or match.group(2)
                    heuristic_plan = [{"tool": "clipboard.copy_text", "args": {"text": text}}]
            elif "paste" in goal_lower:
                heuristic_plan = [{"tool": "clipboard.paste_text", "args": {}}]
            elif "online" in goal_lower or "internet" in goal_lower or "connected" in goal_lower or "connectivity" in goal_lower:
                heuristic_plan = [{"tool": "network.check_connectivity", "args": {}}]
            elif "list" in goal_lower and "process" in goal_lower:
                # Extract filter if mentioned (like "python")
                filter_name = None
                if "python" in goal_lower:
                    filter_name = "python"
                heuristic_plan = [{"tool": "process.list_processes", "args": {"filter_name": filter_name}}]
            elif "summarize" in goal_lower and ":" in goal:
                # Extract text after the colon
                text = goal.split(":", 1)[1].strip()
                heuristic_plan = [{"tool": "llm.summarize", "args": {"text": text}}]
            elif "click" in goal_lower and "button" in goal_lower:
                # Extract button name
                import re
                match = re.search(r"click (?:the )?['\"]?([^'\"]+)['\"]? button", goal_lower)
                if match:
                    button_name = match.group(1)
                    heuristic_plan = [{
                        "tool": "perception.smart_click",
                        "args": {
                            "target": button_name,
                            "context": {"control_type": "button"}
                        }
                    }]
            elif ("type" in goal_lower or "enter" in goal_lower) and not ("text" in goal_lower and "read" in goal_lower):
                # Extract text to type
                import re
                match = re.search(r"type ['\"]([^'\"]+)['\"]", goal)
                if match:
                    text = match.group(1)
                    heuristic_plan = [{
                        "tool": "perception.smart_type",
                        "args": {"text": text}
                    }]
            elif "read" in goal_lower and ("screen" in goal_lower or "window" in goal_lower):
                heuristic_plan = [{
                    "tool": "perception.smart_read",
                    "args": {"context": {}}
                }]
            
            if heuristic_plan:
                print(f"DEBUG: Using heuristic plan: {heuristic_plan}")
                plan = {"actions": heuristic_plan}
            else:
                plan_result = plan_structured(self.llm, goal)
                print(f"DEBUG: Planner returned: {plan_result[0]}")
                print(f"DEBUG: Raw LLM response: {plan_result[1]}")
                plan = {"actions": plan_result[0]} if plan_result[0] else None
            
            if not plan or not plan.get("actions"):
                # More helpful, conversational response when planning fails
                response = (
                    f"Hmm, I'm having trouble figuring out how to help with '{goal}'. "
                    f"Here's what's happening: my planner (which uses the {self.llm.model} model) "
                    f"tried to generate a plan but couldn't come up with valid actions. "
                    f"\n\nThis could mean:\n"
                    f"1. I don't have a tool that matches what you're asking for\n"
                    f"2. The request might need to be phrased differently\n"
                    f"3. My language model might need a clearer instruction\n\n"
                    f"Could you try rephrasing it, or let me know if you'd like to see what tools I have available?"
                )
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
                    # More detailed error reporting
                    tool_name = action_data.get('tool') or action_data.get('action', 'unknown')
                    error_msg = (
                        f"Oops, I hit a snag trying to execute the '{tool_name}' action. "
                        f"Technical details: {str(e)}. "
                        f"This might mean the tool isn't wired up correctly or there's a missing dependency."
                    )
                    results.append({"error": error_msg, "tool": tool_name, "exception": str(e)})
            
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
            # More conversational error handling
            error_response = (
                f"Oh no, something went wrong on my end! Here's what happened: {str(e)}\n\n"
                f"This is an unexpected error in my core processing. It might be a bug in how I'm wired up. "
                f"The technical trace should be in the console if you want to debug it."
            )
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
        
        # System monitoring and clipboard operations are actions
        if any(word in goal_lower for word in ["cpu", "memory", "process", "clipboard", "copy", "paste", "download", "upload"]):
            return False
        
        # Internet connectivity checks are actions
        if any(word in goal_lower for word in ["internet", "connected", "online", "offline", "connectivity"]):
            return False
        
        # File operations are actions
        if any(word in goal_lower for word in ["watch", "monitor", "file", "folder", "directory"]):
            return False
        
        # Image/video/audio operations are actions
        if any(word in goal_lower for word in ["image", "photo", "video", "audio", "resize", "convert", "record"]):
            return False
        
        # If it contains action words, it's probably not a simple question
        action_words = ["list", "show", "get", "find", "search", "take", "click", "open", "create", "send", "play", "stop", "start", "go to", "navigate", "run", "execute", "summarize"]
        for word in action_words:
            if word in goal_lower:
                return False
        
        # Greetings and help requests are simple questions
        if any(word in goal_lower for word in ["hello", "hi", "hey", "help", "what can you do"]):
            return True
        
        # Pure "summarize" requests with text are actions (use LLM executor)
        if "summarize" in goal_lower and ":" in goal:
            return False
                
        return False

    def _handle_simple_question(self, goal: str) -> str:
        """Handle simple questions with direct responses."""
        goal_lower = goal.lower()
        
        if any(word in goal_lower for word in ["hello", "hi", "hey"]):
            return (
                "Hey there! 👋 I'm Kayas, your friendly AI assistant. "
                "Think of me as your tech-savvy buddy who can help with all sorts of tasks - "
                "from checking your system stats to automating your desktop, browsing the web, "
                "managing your calendar, and way more! What can I help you with today?"
            )
        
        if any(word in goal_lower for word in ["what can you do", "help", "capabilities"]):
            return """Great question! I've got a whole toolkit of abilities. Here's what I can do:

🖥️ **System & Desktop Control:**
- Check your CPU, memory usage, and running processes
- Take screenshots and control your desktop
- Copy/paste to clipboard
- Run programs and system commands

🌐 **Web & Network:**
- Browse websites and interact with web pages
- Check internet connectivity
- Download and upload files

📅 **Productivity:**
- Manage Google Calendar events
- Send Slack messages
- Control Spotify playback
- Send emails

📁 **Files & Data:**
- Create, edit, and search files
- Watch directories for changes
- Process images, audio, and video

🤖 **AI-Powered:**
- Summarize text
- Generate content using LLMs
- Analyze images (with vision models)

Just ask me naturally, like you would a friend! For example:
- "What's my CPU usage?"
- "Copy 'hello' to clipboard"
- "Am I online?"
- "Take a screenshot"
- "Summarize: [your text here]"
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
            return "I went ahead and did what you asked, but there's no specific data to show you. Everything should be set!"
        
        # Count successful vs failed actions
        successful = [r for r in results if r.get("success", True) and "error" not in r]
        failed = [r for r in results if not r.get("success", True) or "error" in r]
        
        if failed and not successful:
            # All failed - be more helpful and conversational
            error_msg = failed[0].get("error", "Unknown error")
            tool = failed[0].get("tool", "unknown tool")
            
            response = (
                f"Ugh, I ran into an issue trying to do that. Here's what went wrong:\n\n"
                f"**Problem:** {error_msg}\n\n"
                f"**What I tried:** I attempted to use the '{tool}' executor, but it didn't work out.\n\n"
            )
            
            # Add helpful suggestions based on the tool
            if "process" in tool:
                response += "This is usually a permissions issue or the psutil library might not be working correctly."
            elif "clipboard" in tool:
                response += "Clipboard operations can be tricky on Windows. Make sure pywin32 is installed correctly."
            elif "network" in tool:
                response += "Network operations might be blocked by a firewall or you might be offline."
            elif "llm" in tool:
                response += "The LLM executor might need an Ollama model running. Try 'ollama pull llama3.1' if you haven't already."
            else:
                response += "Check the console for more technical details, or we might need to debug this together!"
            
            return response
        
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
                    # For other actions, try to extract meaningful info from the result
                    # Check if there's data to display
                    if "cpu_percent" in result:
                        cpu = result.get("cpu_percent", 0)
                        memory = result.get("memory_percent", 0)
                        response_parts.append(f"Alright, I checked your system stats! Your CPU is running at {cpu}% and you're using {memory}% of your memory")
                    elif "connected" in result:
                        if result.get("connected"):
                            response_parts.append("Yep, you're online! Internet connection is looking good 👍")
                        else:
                            response_parts.append("Hmm, looks like you're offline right now. No internet connection detected")
                    elif "processes" in result:
                        processes = result.get("processes", [])
                        if processes:
                            count = len(processes)
                            process_names = [p.get("name", "") for p in processes[:3]]
                            if count <= 3:
                                response_parts.append(f"I found {count} Python process(es) running: {', '.join(process_names)}")
                            else:
                                response_parts.append(f"You've got {count} Python processes running! Here are the first few: {', '.join(process_names)}")
                        else:
                            response_parts.append("I didn't find any matching processes. They might have stopped or weren't running")
                    elif "text" in result and "copy" in str(result.get("action", "")):
                        text = result.get("text", "")
                        response_parts.append(f"Done! I copied '{text}' to your clipboard 📋")
                    elif "text" in result and "paste" in str(result.get("action", "")):
                        text = result.get("text", "")
                        response_parts.append(f"Here's what I pasted: {text}")
                    elif "summary" in result:
                        summary = result.get("summary", "")
                        response_parts.append(f"Here's a quick summary for you: {summary}")
                    else:
                        response_parts.append("Got it! I took care of that for you")
            
            if response_parts:
                return " ".join(response_parts) + "."
            else:
                return "All done! Everything went smoothly ✨"
        
        # Mixed results - be empathetic but informative
        return (
            f"Okay, so I managed to complete {len(successful)} action(s) successfully, "
            f"but ran into {len(failed)} issue(s) along the way. The task is partially done. "
            f"Want me to try again or help debug what went wrong?"
        )