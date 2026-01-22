"""
Cognitive DirectAgent - JARVIS-like agent integration.

This wraps the CognitiveAgent to work with the existing tool infrastructure
while providing the thinking/personality layer.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
import uuid

from ..agent.config import (
    db_path, chroma_dir, embed_model, llm_backend,
    groq_api_key, groq_model, vllm_api_url, vllm_model, vllm_mode
)
from ..agent.cognitive import CognitiveAgent
from ..agent.screen_perceiver import ScreenPerceiver
from ..memory.sqlite_memory import MemoryConfig, SQLiteMemory
from ..memory.vector_memory import VectorMemory, VectorMemoryConfig
from ..memory.user_profile import get_profile_manager


class ActionExecutorBridge:
    """
    Bridges the cognitive agent's decisions to the existing executor infrastructure.
    
    Uses SmartExecutor for actual execution (it knows all the tools and handles
    function calling properly), while the cognitive loop handles reasoning.
    """
    
    def __init__(self, router=None, smart_executor=None):
        self.router = router
        self.smart_executor = smart_executor
    
    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action using SmartExecutor or router."""
        try:
            func_name = action.get("function", "")
            args = action.get("args", {})
            
            if not func_name:
                return {"success": False, "error": "No function specified"}
            
            # Try router first for direct tool calls
            if self.router:
                try:
                    result = self.router.route({
                        "tool": func_name,
                        "args": args
                    })
                    return {
                        "success": not result.get("error"),
                        "result": result,
                        "message": result.get("message", str(result))
                    }
                except Exception as e:
                    # If router fails, that's okay - we tried
                    pass
            
            return {"success": False, "error": f"Could not execute {func_name}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_natural(self, request: str) -> Dict[str, Any]:
        """
        Execute a natural language request using SmartExecutor.
        
        This is the preferred method - let SmartExecutor figure out
        which tool to use based on the request.
        """
        if self.smart_executor:
            try:
                result = self.smart_executor.execute(request, "")
                return {
                    "success": result.success,
                    "response": result.response,
                    "action_taken": result.action_taken,
                    "message": result.response
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "No SmartExecutor available"}


class CognitiveDirectAgent:
    """
    JARVIS-like agent that thinks before acting.
    
    Uses the cognitive loop (Perceive → Think → Decide → Act → Reflect)
    while leveraging existing executors for actions.
    
    Usage:
        agent = CognitiveDirectAgent()
        response = agent.run("open youtube")
        print(response["response"])  # Natural, personality-rich response
        print(response["thinking"])  # The agent's inner monologue (for debugging)
    """
    
    def __init__(self, router=None, smart_executor=None, enable_background=True):
        """
        Initialize the cognitive agent.
        
        Args:
            router: Optional existing router from DirectAgent.
            smart_executor: Optional SmartExecutor for action execution.
            enable_background: Enable background monitoring for proactive suggestions.
        """
        self.router = router
        self.smart_executor_ref = smart_executor
        
        # Initialize LLM
        backend = llm_backend()
        
        if backend == "groq":
            from ..agent.groq_llm import GroqLLM
            self.llm = GroqLLM(api_key=groq_api_key(), model=groq_model())
            print("[CognitiveAgent] Using Groq backend")
        elif backend == "vllm":
            from ..agent.vllm_llm import VLLMLlm
            self.llm = VLLMLlm(
                base_url=vllm_api_url(),
                model=vllm_model(),
                mode=vllm_mode()
            )
            print("[CognitiveAgent] Using vLLM backend")
        else:
            from ..agent.llm import LLM
            from ..agent.config import ollama_model
            self.llm = LLM(model=ollama_model())
            print("[CognitiveAgent] Using Ollama backend")
        
        # Initialize memory
        self.memory = SQLiteMemory(MemoryConfig(db_path=db_path()))
        self.vector_memory = VectorMemory(VectorMemoryConfig(
            persist_dir=chroma_dir(),
            embed_model=embed_model()
        ))
        
        # Initialize profile manager
        self.profile_manager = get_profile_manager()
        
        # Initialize screen perceiver
        self.screen_perceiver = ScreenPerceiver()
        
        # Action executor (bridges to existing tools)
        self.action_executor = ActionExecutorBridge(
            router=router, 
            smart_executor=smart_executor
        )
        
        # Vision capabilities for deep screen understanding
        self.vision_llm = None
        try:
            from ..agent.vision_llm import VisionLLM
            self.vision_llm = VisionLLM()
            print("[CognitiveAgent] Vision enabled (Qwen3-VL for screen analysis)")
        except Exception as e:
            print(f"[CognitiveAgent] Vision unavailable: {e}")
        
        # Continuous Observer with vision (self-learning data collection)
        self.observer = None
        try:
            from ..agent.observer import Observer
            self.observer = Observer(vision_llm=self.vision_llm)
            self.observer.start()
            if self.vision_llm:
                print("[CognitiveAgent] Observer started (with vision every 5 min)")
            else:
                print("[CognitiveAgent] Observer started (learning your patterns)")
        except Exception as e:
            print(f"[CognitiveAgent] Observer unavailable: {e}")
        
        # Analyst - LLM-driven autonomous decisions (replaces hardcoded triggers)
        self.analyst = None
        if enable_background and self.observer:
            try:
                from ..agent.analyst import Analyst
                self.analyst = Analyst(
                    llm=self.llm,
                    observation_store=self.observer.store,
                )
                # Pass observer reference so analyst can get screen context
                self.analyst.observer = self.observer
                self.analyst.start()
                print("[CognitiveAgent] Analyst started (autonomous decision making)")
            except Exception as e:
                print(f"[CognitiveAgent] Analyst unavailable: {e}")
        
        # Legacy background monitor (fallback if analyst fails)
        self.background_monitor = None
        self.proactive_engine = None
        
        # The cognitive core
        self.cognitive_agent = CognitiveAgent(
            llm=self.llm,
            memory=self.memory,
            vector_memory=self.vector_memory,
            profile_manager=self.profile_manager,
            screen_perceiver=self.screen_perceiver,
            action_executor=self.action_executor,
        )
        
        print("[CognitiveAgent] Initialized with thinking layer")
    
    def run(self, goal: str, conversation_context: str = "") -> Dict[str, Any]:
        """
        Execute a goal through the cognitive loop.
        
        Args:
            goal: What the user wants
            conversation_context: Recent conversation for context
            
        Returns:
            Dict with:
                - response: Natural language response
                - thinking: The agent's inner monologue (for debugging)
                - run_id: Unique identifier for this interaction
        """
        run_id = str(uuid.uuid4())
        self.memory.log_message(run_id, "user", goal)
        
        try:
            # Record this interaction for break tracking
            if self.background_monitor:
                self.background_monitor.record_interaction()
            
            # FAST PATH: Simple questions get single LLM call (10x faster)
            # Only use full cognitive loop for complex requests
            if self._is_simple_question(goal):
                response = self._fast_respond(goal, conversation_context)
            else:
                # Run the full cognitive loop for complex requests
                response = self.cognitive_agent.run(goal, conversation_context)
            
            # Get thinking trace for debugging
            thinking = ""
            if hasattr(self.cognitive_agent, 'last_thought') and self.cognitive_agent.last_thought:
                thought = self.cognitive_agent.last_thought
                thinking = f"""
**Interpretation:** {thought.interpretation}

**Context Analysis:** {thought.context_analysis}

**Concerns:** {', '.join(thought.concerns) if thought.concerns else 'None'}

**Options Considered:** {', '.join(thought.options) if thought.options else 'Direct execution'}

**My Opinion:** {thought.opinion}

**Emotional Read:** {thought.emotional_read}
""".strip()
            
            self.memory.log_message(run_id, "assistant", response)
            
            # Increment interaction count
            if self.profile_manager:
                self.profile_manager.increment_interactions()
            
            return {
                "response": response,
                "thinking": thinking,
                "run_id": run_id,
                "success": True
            }
            
        except Exception as e:
            error_response = f"Something went wrong in my thinking process: {e}"
            self.memory.log_message(run_id, "assistant", error_response)
            
            return {
                "response": error_response,
                "thinking": "",
                "run_id": run_id,
                "success": False,
                "error": str(e)
            }
    
    def _is_simple_question(self, goal: str) -> bool:
        """Detect if this is a simple Q&A that doesn't need full cognitive loop."""
        goal_lower = goal.lower().strip()
        
        # Question patterns that just need a direct answer
        question_starters = [
            'what is', 'what are', 'what\'s',
            'who is', 'who are',
            'how do', 'how does', 'how to',
            'why is', 'why do', 'why does',
            'explain', 'tell me about', 'describe',
            'can you explain', 'can you tell me',
            'what does', 'what do',
            'difference between', 'compare',
        ]
        
        # Action patterns that need full cognitive loop
        action_patterns = [
            'open', 'launch', 'start', 'run',
            'search for', 'find', 'look up',
            'send', 'message', 'email',
            'play', 'stop', 'pause',
            'create', 'make', 'write',
            'set', 'change', 'update',
        ]
        
        # If it starts with a question pattern and doesn't have action words
        is_question = any(goal_lower.startswith(q) for q in question_starters)
        is_action = any(a in goal_lower for a in action_patterns)
        
        return is_question and not is_action
    
    def _fast_respond(self, goal: str, conversation_context: str = "") -> str:
        """Fast single-call response for simple questions."""
        import re
        
        # Get some context
        screen_context = ""
        try:
            screen_context = self.screen_perceiver.get_quick_context()
        except:
            pass
        
        prompt = f"""/nothink
You are Kayas, a friendly and knowledgeable AI assistant.

User's question: {goal}

{f"Current context: {screen_context}" if screen_context else ""}
{f"Recent conversation: {conversation_context[-500:]}" if conversation_context else ""}

Answer the question directly and helpfully. Be conversational and warm.
Keep your response concise but complete."""

        response = self.llm.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=500,
        )
        
        # Strip thinking tags if present
        if '</think>' in response:
            response = response.split('</think>')[-1].strip()
        else:
            response = re.sub(r'<think>.*', '', response, flags=re.DOTALL).strip()
        
        return response if response else "I'm not sure how to answer that. Could you rephrase?"
    
    def get_screen_context(self) -> str:
        """Get a quick description of what's on screen."""
        return self.screen_perceiver.get_quick_context()
    
    def check_proactive(self) -> Optional[str]:
        """
        Check if there's a proactive suggestion to make.
        
        Uses the Analyst (LLM-driven) to decide if we should speak.
        No hardcoded rules - the LLM decides based on observations.
        
        Returns:
            A message to show the user, or None if nothing to say.
        """
        # Use Analyst (LLM-driven autonomous decisions)
        if self.analyst:
            return self.analyst.should_intervene()
        
        # Fallback to old proactive engine if analyst unavailable
        if self.proactive_engine:
            return self.proactive_engine.should_intervene()
        
        return None
    
    def add_goal(self, description: str, deadline: str = None, priority: int = 5) -> str:
        """
        Add a goal for the agent to track.
        
        Args:
            description: What the goal is
            deadline: Optional deadline (format: "2024-01-20 14:00")
            priority: 1-10, higher = more important
            
        Returns:
            Goal ID for reference
        """
        if not self.background_monitor:
            return ""
        
        from datetime import datetime
        deadline_dt = None
        if deadline:
            try:
                deadline_dt = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
            except ValueError:
                pass
        
        return self.background_monitor.add_goal(description, deadline_dt, priority)
    
    def complete_goal(self, goal_id: str):
        """Mark a goal as completed."""
        if self.background_monitor:
            self.background_monitor.complete_goal(goal_id)
    
    def get_goals(self) -> list:
        """Get all active goals."""
        if not self.background_monitor:
            return []
        return [
            {"id": g.id, "description": g.description, "deadline": str(g.deadline) if g.deadline else None}
            for g in self.background_monitor.goals.values()
            if g.status == "active"
        ]
    
    def get_activity_summary(self, minutes: int = 60) -> dict:
        """Get a summary of recent user activity."""
        if not self.observer:
            return {}
        return self.observer.store.get_summary(minutes)
    
    def get_recent_observations(self, minutes: int = 30) -> list:
        """Get recent observation data."""
        if not self.observer:
            return []
        return self.observer.store.get_recent(minutes)
    
    def shutdown(self):
        """Clean shutdown of background processes."""
        if self.analyst:
            self.analyst.stop()
        if self.observer:
            self.observer.stop()
        if self.background_monitor:
            self.background_monitor.stop()
