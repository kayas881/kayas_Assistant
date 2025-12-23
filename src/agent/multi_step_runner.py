"""
Multi-step task runner for complex workflows.

This module handles the execution of complex tasks that require multiple steps
and decision points. Instead of executing all planned actions at once, it:

1. Executes the first action(s)
2. Checks if the task is complete
3. If not complete, asks the model for the next step with full context
4. Repeats until the task is marked as complete or max steps reached

This solves the problem where models trained on multi-step examples still
only execute one action batch during inference.

Example workflow (Chrome + Search + Save):
  User: "Open Chrome, search for Python tutorials, and save results to notepad"
  
  Step 1: Execute [open Chrome]
  Check: "Is the Chrome window open?" -> No, wait for startup
  
  Step 2: Execute [search for Python tutorials]
  Check: "Are search results displayed?" -> Yes
  
  Step 3: Model continues: "Results are showing. Now save to notepad?"
  Execute: [open notepad, copy search results]
  
  Step 4: Model determines task is complete
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import json
import time
import re
import ast


@dataclass
class StepResult:
    """Result of executing a single step."""
    step_number: int
    action: Dict[str, Any]
    output: Dict[str, Any]
    success: bool
    error: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class ExecutionContext:
    """Context maintained across multiple steps."""
    original_goal: str
    executed_steps: List[StepResult]
    current_plan: List[Dict[str, Any]]
    conversation_history: List[Dict[str, str]]
    completed: bool = False
    completion_reason: Optional[str] = None
    max_steps: int = 10
    current_step: int = 0
    forced_stop: bool = False
    state_snapshot: str = ""


class MultiStepRunner:
    """Executes multi-step tasks with continuation logic."""
    
    def __init__(self, llm, router, memory=None):
        """
        Initialize the multi-step runner.
        
        Args:
            llm: Language model for planning and continuation
            router: Action router for executing individual actions
            memory: Optional memory system for logging
        """
        self.llm = llm
        self.router = router
        self.memory = memory
    
    def run_task(
        self,
        goal: str,
        initial_plan: List[Dict[str, Any]],
        max_steps: int = 10,
        conversation_context: str = ""
    ) -> Dict[str, Any]:
        """
        Execute a complex task with multiple steps.
        
        Args:
            goal: The original user goal
            initial_plan: The initial action plan from the planner
            max_steps: Maximum number of steps before stopping
            conversation_context: Previous conversation for context
        
        Returns:
            Dictionary with final response, all results, and execution trace
        """
        context = ExecutionContext(
            original_goal=goal,
            executed_steps=[],
            current_plan=initial_plan,
            conversation_history=[],
            max_steps=max_steps
        )
        
        # Add user goal to conversation history
        context.conversation_history.append({
            "role": "user",
            "content": goal
        })
        
        print(f"\n{'='*60}")
        print(f"[MultiStepRunner] Starting task: {goal}")
        print(f"[MultiStepRunner] Initial plan: {len(initial_plan)} action(s)")
        print(f"{'='*60}\n")
        
        # Execute steps in a loop
        while context.current_step < context.max_steps and not context.completed:
            context.current_step += 1

            # Hard stop to avoid runaway loops
            if context.current_step > 15:
                context.completed = False
                context.forced_stop = True
                context.completion_reason = "Max steps exceeded (hard limit 15)."
                break
            
            print(f"\n--- Step {context.current_step} ---")
            
            # Execute current batch of actions
            step_results = self._execute_action_batch(
                context.current_plan,
                context.current_step
            )
            
            # Store results
            for result in step_results:
                context.executed_steps.append(result)
            
            # Refresh runtime state snapshot for the continuation prompt
            self._update_state_snapshot(context)
            
            # Check if we should continue
            should_continue, next_plan, reasoning, forced_stop = self._should_continue(
                goal,
                context.executed_steps,
                context.conversation_history,
                context.state_snapshot
            )
            
            print(f"[MultiStepRunner] Continuation check: {should_continue}")
            print(f"[MultiStepRunner] Reasoning: {reasoning}")
            
            if not should_continue:
                context.completed = True
                context.completion_reason = reasoning
                if forced_stop:
                    context.forced_stop = True
                break
            
            # Update plan for next iteration
            if next_plan:
                context.current_plan = next_plan
                context.conversation_history.append({
                    "role": "assistant",
                    "content": f"Executing step {context.current_step}: {reasoning}"
                })
            else:
                context.completed = True
                context.completion_reason = "No further actions needed"
                break
        
        if not context.completed and context.current_step >= context.max_steps:
            context.completion_reason = f"Stopped after reaching the step limit of {context.max_steps}."
            context.forced_stop = True
        
        # Generate final response
        final_response = self._generate_final_response(goal, context)
        
        return {
            "response": final_response,
            "completed": context.completed,
            "completion_reason": context.completion_reason,
            "total_steps": context.current_step,
            "results": [
                {
                    "step": r.step_number,
                    "action": r.action,
                    "output": r.output,
                    "success": r.success,
                    "error": r.error,
                    "execution_time": r.execution_time
                }
                for r in context.executed_steps
            ]
        }
    
    def _execute_action_batch(
        self,
        actions: List[Dict[str, Any]],
        step_number: int
    ) -> List[StepResult]:
        """Execute a batch of actions and return results."""
        results = []
        
        for i, action_data in enumerate(actions):
            print(f"  Action {i+1}/{len(actions)}: {action_data.get('tool', action_data.get('action', 'unknown'))}")
            
            start_time = time.time()
            try:
                # Execute the action
                result = self.router.route(action_data)
                execution_time = time.time() - start_time
                
                success = result.get("success", True) if isinstance(result, dict) else True
                
                step_result = StepResult(
                    step_number=step_number,
                    action=action_data,
                    output=result,
                    success=success,
                    execution_time=execution_time
                )
                
                print(f"    ✓ Success ({execution_time:.2f}s)")
                results.append(step_result)
                
            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = str(e)
                
                step_result = StepResult(
                    step_number=step_number,
                    action=action_data,
                    output={"error": error_msg},
                    success=False,
                    error=error_msg,
                    execution_time=execution_time
                )
                
                print(f"    ✗ Failed ({execution_time:.2f}s): {error_msg}")
                results.append(step_result)
        
        return results
    
    def _should_continue(
        self,
        goal: str,
        executed_steps: List[StepResult],
        conversation_history: List[Dict[str, str]],
        state_snapshot: str
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], str, bool]:
        """
        Determine if we should continue with more steps.
        
        Returns:
            Tuple of (should_continue, next_plan, reasoning)
        """
        
        # Build context for the model
        step_summary = self._summarize_execution(executed_steps)
        state_info = state_snapshot or "State information unavailable"
        recent_steps = self._format_recent_steps(executed_steps)
        conversation_text = self._format_conversation_history(conversation_history)

        # Additional deterministic context for the LLM
        process_list = self._get_process_list()
        continuation_context = (
            f"Current state: {process_list}\n"
            f"Last N actions: {recent_steps}\n"
            f"Task: {goal}\n\n"
            "Should we continue or mark as complete?"
        )
        
        # Create a continuation prompt
        prompt = f"""
You are Kayas, an intelligent assistant executing a multi-step task.

Original goal: {goal}

Conversation context:
{conversation_text}

Recent actions:
{recent_steps}

Deterministic context:
{continuation_context}

Execution trace (JSON):
{step_summary}

Current system state:
{state_info}

Analyze what has been done and decide:
1. Is the goal complete/satisfied?
2. If not, what is the NEXT logical step?

Respond in this JSON format:
{{
    "completed": true/false,
    "reasoning": "brief explanation of your decision",
    "next_steps": [
        {{"tool": "...", "args": {{...}}}},
        ...
    ] or null if completed
}}

IMPORTANT:
- Only return valid JSON
- If completed, set next_steps to null
- next_steps should be a list of actions or null (never an empty list)
"""
        
        print(f"\n[MultiStepRunner] Asking model if task is complete...")
        
        try:
            # Get model's continuation decision
            response = self.llm.generate(prompt, max_tokens=1000)
            self._log_continuation_output(response)
            
            print(f"[MultiStepRunner] Model response: {response[:200]}...")
            
            decision = self._parse_continuation_response(response)
            if decision is None:
                # Couldn't parse JSON - be lenient and assume task is complete to avoid loops
                # Log the raw response for debugging
                print(f"[MultiStepRunner] WARNING: Could not parse model response, assuming task complete")
                print(f"[MultiStepRunner] Raw response: {response[:500]}")
                return False, None, "Task completed (could not parse model response for next steps)", False
            
            completed = decision.get("completed", False)
            reasoning = decision.get("reasoning", "No reasoning provided")
            next_steps = decision.get("next_steps")
            
            # If the model provided next_steps, honor them regardless of the completed flag
            if next_steps and len(next_steps) > 0:
                # Treat as continuation required; model may optimistically set completed=true
                return True, next_steps, reasoning, False

            # Otherwise rely on completed flag
            if completed or next_steps is None:
                return False, None, reasoning, False
            
            return False, None, reasoning or "Task appears complete", False
        
        except Exception as e:
            # If there's an error getting continuation, assume we're done
            return False, None, f"Error checking continuation: {str(e)}", True
    
    def _summarize_execution(self, executed_steps: List[StepResult]) -> str:
        """Create a structured JSON summary of executed steps."""
        if not executed_steps:
            return json.dumps({"steps": []})
        trace: List[Dict[str, Any]] = []
        for step in executed_steps[-20:]:  # keep prompt compact
            action_name = step.action.get("tool", step.action.get("action", "unknown"))
            entry: Dict[str, Any] = {
                "step": step.step_number,
                "tool": action_name,
                "success": step.success,
            }
            if "args" in step.action:
                entry["args"] = step.action["args"]
            if step.error:
                entry["error"] = self._shorten_output(step.error)
            elif step.output:
                entry["result"] = self._shorten_output(step.output)
            trace.append(entry)
        return json.dumps({"steps": trace}, indent=2, default=str)
    
    def _generate_final_response(self, goal: str, context: ExecutionContext) -> str:
        """Generate a natural language response about what was accomplished."""
        
        if not context.executed_steps:
            return "I wasn't able to start the task. Please check if your request is clear."
        
        success_count = sum(1 for s in context.executed_steps if s.success)
        total_count = len(context.executed_steps)
        failed_steps = [s for s in context.executed_steps if not s.success]
        failure_detail = ""
        if failed_steps:
            last_fail = failed_steps[-1]
            fail_tool = last_fail.action.get("tool", last_fail.action.get("action", "unknown"))
            fail_msg = last_fail.error or self._shorten_output(last_fail.output)
            failure_detail = f" Failed at step {last_fail.step_number} ({fail_tool}): {fail_msg}."
        
        if context.completed:
            if context.forced_stop:
                reason = context.completion_reason or "an internal safety stop was triggered"
                return (
                    f"I had to stop working on '{goal}' after {context.current_step} step(s) because {reason}. "
                    f"{success_count}/{total_count} actions succeeded."
                )
            if success_count == total_count:
                return f"Done! I completed your request: {goal}. {context.completion_reason or ''}".strip()
            return (
                f"I completed {success_count} of {total_count} steps for '{goal}'."
                f"{failure_detail or (' ' + (context.completion_reason or ''))}"
                )
        else:
            return (
                f"I worked on your request but hit the step limit ({context.max_steps} steps). "
                f"I completed {success_count} actions so far. Would you like me to continue?"
            )
        

    def _shorten_output(self, output: Any, max_len: int = 500) -> str:
        """Shorten output for display in prompts. Special handling for search results."""
        # Special handling for local file/folder search results (explorer.find_items)
        if isinstance(output, dict) and "results" in output and "query" in output:
            query = output.get("query", "")
            results = output.get("results", [])
            location = output.get("location", "")
            if results:
                # Show count and first few file names
                count = len(results)
                names = [r.get("name", r.get("path", "").split("\\")[-1]) for r in results[:3]]
                summary = f"Found {count} match(es) for '{query}' in {location}: {', '.join(names)}"
                if count > 3:
                    summary += f" and {count - 3} more"
                return summary
            else:
                return f"No results found for '{query}' in {location}"
        
        # Special handling for web.research results (Comet-style)
        if isinstance(output, dict) and output.get("action") == "web.research":
            question = output.get("question", "")
            sources = output.get("sources", [])
            sources_reviewed = output.get("sources_reviewed", 0)
            queries_used = output.get("queries_used", [])
            
            # Special handling for web.deep_research results (iterative evidence-based research)
            if isinstance(output, dict) and output.get("action") == "web.deep_research":
                success = output.get("success", False)
                if success:
                    answer = (output.get("answer") or "").strip()
                    sources = output.get("sources", [])
                    conf_breakdown = output.get("confidence_breakdown", [])
                    overall_conf = output.get("overall_confidence", 0.0)
                    iterations = output.get("iterations", 0)
                    total_sources = output.get("total_sources", 0)
                    
                    lines = []
                    # Show research metadata
                    lines.append(f"Deep Research Results ({iterations} iterations, {total_sources} sources):")
                    lines.append(f"Overall Confidence: {overall_conf:.0%}\n")
                    
                    # Show answer
                    if answer:
                        lines.append("Answer:")
                        lines.append(answer)
                    
                    # Show sources
                    if sources:
                        lines.append(f"\n{len(sources)} Sources:")
                        for s in sources[:10]:
                            sid = s.get("id", "?")
                            title = s.get("title", "")[:60]
                            domain = s.get("domain", "")
                            quality = s.get("quality", 0.0)
                            lines.append(f"[{sid}] {title} ({domain}) - quality: {quality:.1f}")
                    
                    # Show high-confidence claims
                    if conf_breakdown:
                        high_conf_claims = [c for c in conf_breakdown if c.get("confidence", 0) >= 0.6]
                        if high_conf_claims:
                            lines.append(f"\nHigh-Confidence Claims ({len(high_conf_claims)}):")
                            for c in high_conf_claims[:5]:
                                claim_text = c.get("claim", "")[:80]
                                conf = c.get("confidence", 0)
                                support = c.get("support_count", 0)
                                lines.append(f"- {claim_text} (conf: {conf:.0%}, {support} sources)")
                    
                    return "\n".join(lines)
                else:
                    return f"Deep research failed: {output.get('error', 'unknown error')}"
            
            # Special handling for web.answer results (one-shot synthesis with citations)
            if isinstance(output, dict) and output.get("action") == "web.answer":
                success = output.get("success", False)
                if success:
                    answer = (output.get("answer") or "").strip()
                    sources = output.get("sources", [])
                    lines = []
                    if answer:
                        lines.append("Final Answer:\n" + answer)
                    if sources:
                        lines.append("\nSources:")
                        for s in sources[:8]:
                            title = s.get("title", "")[:60]
                            domain = s.get("domain", "")
                            lines.append(f"- {title} ({domain})")
                    return "\n".join(lines) if lines else "Answer generated."
                else:
                    return f"Answer failed: {output.get('error', 'unknown error')}"

            if output.get("success") and sources:
                lines = [f"Research for '{question}'"]
                lines.append(f"Queries: {', '.join(queries_used)}")
                lines.append(f"Reviewing sources · {sources_reviewed}")
                lines.append("Sources:")
                for s in sources[:10]:
                    title = s.get("title", "")[:50]
                    domain = s.get("domain", "")
                    word_count = s.get("word_count", 0)
                    lines.append(f"  [{title}]({domain}) - {word_count} words")
                lines.append(f"\n--- Content from sources (for citation) ---")
                for i, s in enumerate(sources[:5], 1):
                    content = s.get("content", "")[:1500]
                    lines.append(f"\n[{i}] {s.get('title', '')} ({s.get('url', '')})")
                    lines.append(content)
                return "\n".join(lines)
            else:
                # Show detailed error when no sources were found
                err = output.get('error') or "no sources found"
                return f"Research failed: {err}"
        
        # Special handling for web.search results
        if isinstance(output, dict) and output.get("action") == "web.search":
            query = output.get("query", "")
            results = output.get("results", [])
            success = output.get("success", False)
            if success and results:
                count = len(results)
                # Format search results for LLM to see
                summary_lines = [f"Web search for '{query}' returned {count} results:"]
                for i, r in enumerate(results[:5], 1):
                    title = r.get("title", "")[:60]
                    url = r.get("url", "")
                    snippet = r.get("snippet", "")[:100]
                    summary_lines.append(f"{i}. {title}\n   URL: {url}\n   {snippet}")
                return "\n".join(summary_lines)
            elif not success:
                return f"Web search failed: {output.get('error', 'unknown error')}"
            else:
                return f"No web results found for '{query}'"
        
        # Special handling for web.extract_main_text results
        if isinstance(output, dict) and output.get("action") == "web.extract_main_text":
            url = output.get("url", "")
            title = output.get("title", "")
            word_count = output.get("word_count", 0)
            main_text = output.get("main_text", "")[:1000]  # Show first 1000 chars
            if output.get("success"):
                return f"Extracted from '{title}' ({word_count} words):\n{main_text}..."
            else:
                return f"Failed to extract content from {url}: {output.get('error', 'unknown')}"
        
        # Special handling for web.fetch results
        if isinstance(output, dict) and output.get("action") == "web.fetch":
            title = output.get("title", "")
            excerpt = output.get("excerpt", "")[:500]
            if output.get("success"):
                return f"Fetched '{title}':\n{excerpt}..."
            else:
                return f"Failed to fetch: {output.get('error', 'unknown')}"
        
        # Default shortening
        text = json.dumps(output, default=str) if isinstance(output, (dict, list)) else str(output)
        text = text.replace("\n", " ")
        return text[:max_len] + ("..." if len(text) > max_len else "")

    def _format_recent_steps(self, executed_steps: List[StepResult], limit: int = 5) -> str:
        if not executed_steps:
            return "No steps executed yet."
        lines: List[str] = []
        for step in executed_steps[-limit:]:
            tool = step.action.get("tool", step.action.get("action", "unknown"))
            status = "succeeded" if step.success else "failed"
            detail_source = step.error or step.output
            detail = self._shorten_output(detail_source) if detail_source else "no output"
            lines.append(f"Step {step.step_number}: {tool} {status} -> {detail}")
        return "\n".join(lines)

    def _format_conversation_history(
        self,
        conversation_history: List[Dict[str, str]],
        limit: int = 6,
    ) -> str:
        if not conversation_history:
            return "No prior conversation."
        relevant = conversation_history[-limit:]
        formatted = [
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in relevant
        ]
        return "\n".join(formatted)

    def _update_state_snapshot(self, context: ExecutionContext) -> None:
        process_summary = "Process information unavailable"
        try:
            state = self.router.route({"tool": "process.list_processes", "args": {}})
            if isinstance(state, dict) and state.get("success") and state.get("processes"):
                names = [proc.get("name", "unknown") for proc in state.get("processes", [])[:8]]
                process_summary = f"Running processes: {', '.join(names)}"
            else:
                process_summary = "Process information unavailable"
        except Exception as exc:
            process_summary = f"Process information unavailable ({exc})"

        last_action_summary = "No actions have been executed yet."
        if context.executed_steps:
            last_step = context.executed_steps[-1]
            tool = last_step.action.get("tool", last_step.action.get("action", "unknown"))
            status = "succeeded" if last_step.success else "failed"
            detail_source = last_step.error or last_step.output
            detail = self._shorten_output(detail_source) if detail_source else "no output"
            last_action_summary = (
                f"Last action step {last_step.step_number} via {tool} {status}: {detail}"
            )

        context.state_snapshot = f"{process_summary}\n{last_action_summary}"

    def _get_process_list(self) -> str:
        try:
            state = self.router.route({"tool": "process.list_processes", "args": {}})
            if isinstance(state, dict) and state.get("processes"):
                names = [proc.get("name", "unknown") for proc in state.get("processes", [])[:8]]
                return ", ".join(names) or "none"
        except Exception:
            return "unavailable"
        return "unavailable"

    def _log_continuation_output(self, response: str) -> None:
        try:
            log_path = Path("logs") / "continuations.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.utcnow().isoformat()
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(f"[{timestamp}] {response}\n\n")
        except Exception:
            pass

    def _parse_continuation_response(self, response: str) -> Optional[Dict[str, Any]]:
        cleaned = response.replace("```json", "").replace("```", "").strip()
        # Strip JavaScript-style comments that models sometimes emit
        cleaned = re.sub(r"//.*", "", cleaned)
        candidate = self._extract_json_block(cleaned)
        candidates = [c for c in (candidate, cleaned) if c]
        for cand in candidates:
            cand = cand.strip()
            # Remove trailing commas before object/array endings
            cand = re.sub(r",\s*([}\]])", r"\1", cand)
            try:
                return json.loads(cand)
            except json.JSONDecodeError:
                pass
            py_ready = re.sub(r"\btrue\b", "True", cand, flags=re.IGNORECASE)
            py_ready = re.sub(r"\bfalse\b", "False", py_ready, flags=re.IGNORECASE)
            py_ready = re.sub(r"\bnull\b", "None", py_ready, flags=re.IGNORECASE)
            try:
                parsed = ast.literal_eval(py_ready)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue
        return None

    def _extract_json_block(self, text: str) -> Optional[str]:
        start = None
        depth = 0
        for idx, char in enumerate(text):
            if char == '{':
                if depth == 0:
                    start = idx
                depth += 1
            elif char == '}':
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start is not None:
                        return text[start:idx + 1]
        return None


# Example usage and testing
if __name__ == "__main__":
    print("Multi-step runner module loaded successfully")
    print("\nThis module is designed to be used by DirectAgent for complex workflows.")
    print("It handles continuation logic to ensure multi-step tasks complete fully.")
