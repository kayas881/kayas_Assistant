"""
Cognitive Agent - JARVIS-like autonomous reasoning loop.

Implements the 5-phase cognitive cycle:
PERCEIVE → THINK → DECIDE → ACT → REFLECT

This replaces the executor-dispatch pattern with true reasoning.
"""
from __future__ import annotations

import time
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

from .personality import get_personality_prompt, detect_mood_indicators


@dataclass
class PerceptionFrame:
    """Everything the agent knows at a moment in time."""
    
    # User input
    user_input: str = ""
    timestamp: str = ""
    
    # Time context
    time_of_day: str = ""  # morning, afternoon, evening, late_night
    day_type: str = ""  # weekday, weekend
    
    # Screen state (filled by vision system)
    active_window: str = ""
    visible_apps: List[str] = field(default_factory=list)
    screen_description: str = ""
    
    # User state
    recent_mood: str = ""
    interaction_count_today: int = 0
    
    # Memory context
    relevant_memories: List[str] = field(default_factory=list)
    recent_conversation: List[Dict[str, str]] = field(default_factory=list)
    
    # Active goals and signals
    active_goals: List[str] = field(default_factory=list)
    background_signals: List[str] = field(default_factory=list)
    
    def to_prompt(self) -> str:
        """Format perception for LLM consumption."""
        parts = []
        
        parts.append(f"**Current Time:** {self.timestamp} ({self.time_of_day}, {self.day_type})")
        
        if self.user_input:
            parts.append(f"**User Said:** \"{self.user_input}\"")
        
        if self.active_window:
            parts.append(f"**Active Window:** {self.active_window}")
        
        if self.visible_apps:
            parts.append(f"**Open Apps:** {', '.join(self.visible_apps)}")
        
        if self.screen_description:
            parts.append(f"**Screen:** {self.screen_description}")
        
        if self.recent_mood:
            parts.append(f"**User's Mood:** {self.recent_mood}")
        
        if self.relevant_memories:
            parts.append("**Relevant Memories:**")
            for mem in self.relevant_memories[:5]:
                parts.append(f"  - {mem}")
        
        if self.active_goals:
            parts.append("**Active Goals:**")
            for goal in self.active_goals:
                parts.append(f"  - {goal}")
        
        if self.background_signals:
            parts.append("**Signals:**")
            for sig in self.background_signals:
                parts.append(f"  - {sig}")
        
        return "\n".join(parts)


@dataclass
class Thought:
    """Result of the thinking phase - inner monologue."""
    
    interpretation: str = ""  # What does user actually want?
    context_analysis: str = ""  # What matters about the situation?
    concerns: List[str] = field(default_factory=list)  # Worries, red flags
    options: List[str] = field(default_factory=list)  # Possible approaches
    opinion: str = ""  # What do I think they should do?
    emotional_read: str = ""  # How is user feeling?
    
    raw_thinking: str = ""  # Full thinking trace for debugging


@dataclass
class Decision:
    """Committed action plan."""
    
    action_type: str = ""  # "execute_function", "screen_interaction", "synthesize_code", "just_respond"
    actions: List[Dict[str, Any]] = field(default_factory=list)
    
    response_tone: str = "friendly"
    response_includes: List[str] = field(default_factory=list)
    response_avoids: List[str] = field(default_factory=list)
    
    contingencies: Dict[str, str] = field(default_factory=dict)


@dataclass
class Reflection:
    """Post-action assessment."""
    
    action_taken: str = ""
    outcome: str = ""  # success, partial, failed
    observations: List[str] = field(default_factory=list)
    learnings: List[str] = field(default_factory=list)
    follow_up_needed: bool = False
    follow_up_action: str = ""


class CognitiveAgent:
    """
    JARVIS-like agent with genuine reasoning.
    
    The key insight: personality emerges from actual thinking,
    not from prompt templates. By having the agent truly reason
    about situations, responses become naturally human.
    """
    
    def __init__(
        self,
        llm,
        memory=None,
        vector_memory=None,
        profile_manager=None,
        screen_perceiver=None,
        action_executor=None,
    ):
        """
        Initialize the cognitive agent.
        
        Args:
            llm: The language model for reasoning
            memory: SQLite memory for conversation history
            vector_memory: Vector memory for semantic search
            profile_manager: User profile and preferences
            screen_perceiver: Vision system for screen understanding
            action_executor: System for executing decided actions
        """
        self.llm = llm
        self.memory = memory
        self.vector_memory = vector_memory
        self.profile_manager = profile_manager
        self.screen_perceiver = screen_perceiver
        self.action_executor = action_executor
        
        # Cognitive state
        self.last_perception: Optional[PerceptionFrame] = None
        self.last_thought: Optional[Thought] = None
        self.conversation_context: List[Dict[str, str]] = []
    
    # =========================================================================
    # PHASE 1: PERCEIVE
    # =========================================================================
    
    def perceive(self, user_input: str = "") -> PerceptionFrame:
        """
        Gather all relevant context into a perception frame.
        
        This is where we collect everything the agent needs to 
        understand the situation before thinking about it.
        """
        now = datetime.now()
        
        frame = PerceptionFrame(
            user_input=user_input,
            timestamp=now.strftime("%Y-%m-%d %H:%M"),
            time_of_day=self._get_time_of_day(now.hour),
            day_type="weekend" if now.weekday() >= 5 else "weekday",
        )
        
        # Get screen state if available
        if self.screen_perceiver:
            try:
                screen_info = self.screen_perceiver.get_current_state()
                frame.active_window = screen_info.get("active_window", "")
                frame.visible_apps = screen_info.get("visible_apps", [])
                frame.screen_description = screen_info.get("description", "")
            except Exception:
                pass
        
        # Get user context if available
        if self.profile_manager:
            try:
                profile = self.profile_manager.get_profile()
                frame.interaction_count_today = getattr(profile, 'total_interactions', 0)
                
                # Get recent mood
                mood = self.profile_manager.get_dominant_mood(hours=2)
                if mood:
                    frame.recent_mood = mood
            except Exception:
                pass
        
        # Get relevant memories
        if self.vector_memory and user_input:
            try:
                results = self.vector_memory.query(user_input, n_results=5)
                if results and 'documents' in results:
                    frame.relevant_memories = results['documents'][0] if results['documents'] else []
            except Exception:
                pass
        
        # Detect mood from input
        if user_input:
            mood_indicators = detect_mood_indicators(user_input)
            if mood_indicators and not frame.recent_mood:
                frame.recent_mood = mood_indicators
        
        # Add recent conversation
        frame.recent_conversation = self.conversation_context[-5:]
        
        self.last_perception = frame
        return frame
    
    def _get_time_of_day(self, hour: int) -> str:
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "late_night"
    
    # =========================================================================
    # PHASE 2: THINK (Inner Monologue)
    # =========================================================================
    
    def think(self, perception: PerceptionFrame) -> Thought:
        """
        Reason about the situation. This is where personality lives.
        
        The thinking process considers:
        - What does user actually want (not just literal meaning)?
        - What matters about the current context?
        - Are there any concerns or red flags?
        - What are the options?
        - What do I (the agent) actually think?
        """
        
        thinking_prompt = f"""You are Kayas, a personal AI assistant with genuine personality.

## Current Situation
{perception.to_prompt()}

## Your Task: Think Through This

Before deciding what to do, reason through the situation:

### 1. INTERPRET
What does the user actually want? Look beyond the literal words.
- What's the underlying intent or need?
- Is this a request, a question, or just conversation?
- Are they stressed, relaxed, in a hurry?

### 2. CONTEXT
What matters about the current situation?
- Time of day, what they were doing
- Recent patterns or history
- Anything unusual?

### 3. CONCERNS
Is there anything to be worried about?
- Is this a bad idea they might regret?
- Are there better alternatives?
- Should I warn them about something?
- Are they forgetting something important?

### 4. OPTIONS
What are my choices here?
- List 2-4 different approaches
- Include the obvious option AND alternatives
- Consider doing nothing / asking clarifying questions

### 5. MY OPINION
What do I actually think?
- Don't be neutral - have a perspective
- What would a good friend do here?
- If you think they're making a mistake, say so

Respond in this JSON format:
{{
    "interpretation": "What they actually want...",
    "context_analysis": "What matters about the situation...",
    "concerns": ["concern 1", "concern 2"],
    "options": ["option 1", "option 2", "option 3"],
    "opinion": "What I think they should do and why...",
    "emotional_read": "How they seem to be feeling..."
}}

Think like a friend who genuinely cares, not a robotic assistant."""

        try:
            # Use generate() - the actual method in GroqLLM and VLLMLlm
            raw_thinking = self.llm.generate(
                prompt=thinking_prompt,
                temperature=0.7,
                max_tokens=800,
            )
            
            # Parse the JSON response
            thought = self._parse_thinking(raw_thinking)
            thought.raw_thinking = raw_thinking
            
            self.last_thought = thought
            return thought
            
        except Exception as e:
            # Fallback to minimal thinking
            print(f"[Cognitive] THINKING ERROR: {e}")
            return Thought(
                interpretation=perception.user_input,
                opinion="I'll help with this directly.",
                raw_thinking=f"Error in thinking: {e}"
            )
    
    def _parse_thinking(self, raw: str) -> Thought:
        """Parse LLM thinking output into structured Thought."""
        thought = Thought()
        
        # Try to extract JSON
        try:
            # Find JSON block
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
                thought.interpretation = data.get("interpretation", "")
                thought.context_analysis = data.get("context_analysis", "")
                thought.concerns = data.get("concerns", [])
                thought.options = data.get("options", [])
                thought.opinion = data.get("opinion", "")
                thought.emotional_read = data.get("emotional_read", "")
        except json.JSONDecodeError:
            # If JSON fails, just store raw thinking
            thought.interpretation = raw[:500]
        
        return thought
    
    # =========================================================================
    # PHASE 3: DECIDE
    # =========================================================================
    
    def decide(self, perception: PerceptionFrame, thought: Thought) -> Decision:
        """
        Commit to a specific action plan based on thinking.
        
        This phase turns reasoning into action. It chooses:
        - What kind of action to take
        - Specific steps
        - How to frame the response
        """
        
        decision_prompt = f"""Based on your thinking, decide what to do.

## The Situation
User said: "{perception.user_input}"

## Your Thinking
- Interpretation: {thought.interpretation}
- Concerns: {', '.join(thought.concerns) if thought.concerns else 'None'}
- Options: {', '.join(thought.options) if thought.options else 'Direct execution'}
- Your opinion: {thought.opinion}

## Decide

Choose your approach and plan the response:

{{
    "action_type": "execute_function|screen_interaction|just_respond|clarify",
    "actions": [
        {{"function": "function_name", "args": {{...}}}}
    ],
    "response_tone": "casual|warm|playful|serious|concerned",
    "include_in_response": ["what to mention"],
    "avoid_in_response": ["what to avoid"],
    "reasoning": "why this approach"
}}

Notes:
- action_type "just_respond" means no action needed, just conversation
- action_type "clarify" means ask the user for more info
- include_in_response should reflect your OPINION and CONCERNS
- Personality comes through in what you choose to say"""

        try:
            # Use generate() - the actual method in GroqLLM and VLLMLlm
            raw = self.llm.generate(
                prompt=decision_prompt,
                temperature=0.3,
                max_tokens=500,
            )
            return self._parse_decision(raw)
            
        except Exception as e:
            return Decision(
                action_type="just_respond",
                response_tone="friendly",
            )
    
    def _parse_decision(self, raw: str) -> Decision:
        """Parse LLM decision into structured Decision."""
        decision = Decision()
        
        try:
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
                decision.action_type = data.get("action_type", "just_respond")
                decision.actions = data.get("actions", [])
                decision.response_tone = data.get("response_tone", "friendly")
                decision.response_includes = data.get("include_in_response", [])
                decision.response_avoids = data.get("avoid_in_response", [])
        except json.JSONDecodeError:
            decision.action_type = "just_respond"
        
        return decision
    # =========================================================================
    # PHASE 4: ACT
    # =========================================================================
    
    def act(self, decision: Decision, user_input: str = "") -> Dict[str, Any]:
        """
        Execute the decided actions.
        
        This phase handles:
        - Natural language execution via SmartExecutor (only for actual actions)
        - Direct function calls via router
        - Early return for conversation-only responses
        """
        
        # For conversation/clarification, don't try to execute anything
        if decision.action_type in ("just_respond", "clarify", "conversation"):
            return {"success": True, "result": "No action needed", "action_type": decision.action_type}
        
        # Only use SmartExecutor for actual execution requests
        if decision.action_type == "execute_function" and self.action_executor:
            if hasattr(self.action_executor, 'execute_natural') and user_input:
                result = self.action_executor.execute_natural(user_input)
                if result.get("success"):
                    return {
                        "success": True,
                        "results": [result],
                        "message": result.get("message", "Action completed")
                    }
        
        # Fallback: try direct function execution
        results = []
        for action in decision.actions:
            try:
                if self.action_executor:
                    result = self.action_executor.execute(action)
                    results.append(result)
                else:
                    results.append({"success": False, "error": "No executor available"})
            except Exception as e:
                results.append({"success": False, "error": str(e)})
        
        return {
            "success": all(r.get("success", False) for r in results) if results else False,
            "results": results
        }
    
    # =========================================================================
    # PHASE 5: REFLECT
    # =========================================================================
    
    def reflect(self, decision: Decision, action_result: Dict[str, Any]) -> Reflection:
        """
        Assess what happened and learn from it.
        
        This phase:
        - Evaluates whether actions succeeded
        - Captures observations
        - Identifies learnings for future
        """
        
        reflection = Reflection(
            action_taken=decision.action_type,
            outcome="success" if action_result.get("success") else "failed",
            observations=[],
        )
        
        if "results" in action_result:
            for r in action_result["results"]:
                if "error" in r:
                    reflection.observations.append(f"Error: {r['error']}")
                elif "message" in r:
                    reflection.observations.append(r["message"])
        
        return reflection
    
    # =========================================================================
    # RESPONSE GENERATION
    # =========================================================================
    
    def generate_response(
        self,
        perception: PerceptionFrame,
        thought: Thought,
        decision: Decision,
        reflection: Reflection,
    ) -> str:
        """
        Generate the final user-facing response.
        
        This is where the cognitive trace becomes natural speech.
        The response should REFLECT the thinking, not just report actions.
        """
        
        response_prompt = f"""Generate a response as Kayas.

## What happened
User: "{perception.user_input}"
Action taken: {decision.action_type}
Outcome: {reflection.outcome}
Observations: {', '.join(reflection.observations) if reflection.observations else 'None'}

## How to respond
Tone: {decision.response_tone}
Include: {', '.join(decision.response_includes) if decision.response_includes else 'natural response'}
Avoid: {', '.join(decision.response_avoids) if decision.response_avoids else 'being robotic'}

## Your thinking (let this influence your response)
- Interpretation: {thought.interpretation}
- Concerns: {', '.join(thought.concerns) if thought.concerns else 'none'}
- Opinion: {thought.opinion}
- Their mood: {thought.emotional_read}

## Response Guidelines
1. DON'T just report what happened ("I opened YouTube")
2. DO respond like a friend would ("YouTube's up - want me to find something specific?")
3. If you had concerns, mention them naturally
4. If you have suggestions, offer them
5. Match their energy - brief if they're busy, chatty if they're relaxed
6. Be yourself - have opinions, make jokes, show personality

Generate only the response text, nothing else:"""

        try:
            # Use generate() - the actual method in GroqLLM and VLLMLlm
            response = self.llm.generate(
                prompt=response_prompt,
                temperature=0.8,
                max_tokens=500,  # Increased to prevent cutoff
            )
            
            return response if isinstance(response, str) else str(response)
            
        except Exception as e:
            return f"Did that for you. {str(e)}" if reflection.outcome != "success" else "Done!"
    
    # =========================================================================
    # MAIN LOOP
    # =========================================================================
    
    def run(self, user_input: str, conversation_history: str = "") -> str:
        """
        Execute the full cognitive loop.
        
        PERCEIVE → THINK → DECIDE → ACT → REFLECT → RESPOND
        
        Args:
            user_input: What the user said/asked
            conversation_history: Recent conversation for context
            
        Returns:
            Natural language response
        """
        
        # Update conversation context
        if conversation_history:
            # Parse history if needed
            self.conversation_context.append({"role": "user", "content": user_input})
        
        # Phase 1: PERCEIVE
        perception = self.perceive(user_input)
        
        # Phase 2: THINK
        thought = self.think(perception)
        
        # Phase 3: DECIDE
        decision = self.decide(perception, thought)
        
        # Phase 4: ACT (pass user_input for natural language execution)
        action_result = self.act(decision, user_input)
        
        # Phase 5: REFLECT
        reflection = self.reflect(decision, action_result)
        
        # Generate response
        response = self.generate_response(perception, thought, decision, reflection)
        
        # Store in conversation context
        self.conversation_context.append({"role": "assistant", "content": response})
        
        # Keep context manageable
        if len(self.conversation_context) > 20:
            self.conversation_context = self.conversation_context[-20:]
        
        return response
