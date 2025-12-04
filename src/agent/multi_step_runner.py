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
import json
import time


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
            
            print(f"\n--- Step {context.current_step} ---")
            
            # Execute current batch of actions
            step_results = self._execute_action_batch(
                context.current_plan,
                context.current_step
            )
            
            # Store results
            for result in step_results:
                context.executed_steps.append(result)
            
            # Check if we should continue
            should_continue, next_plan, reasoning = self._should_continue(
                goal,
                context.executed_steps,
                context.conversation_history
            )
            
            print(f"[MultiStepRunner] Continuation check: {should_continue}")
            print(f"[MultiStepRunner] Reasoning: {reasoning}")
            
            if not should_continue:
                context.completed = True
                context.completion_reason = reasoning
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
        conversation_history: List[Dict[str, str]]
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], str]:
        """
        Determine if we should continue with more steps.
        
        Returns:
            Tuple of (should_continue, next_plan, reasoning)
        """
        
        # Build context for the model
        step_summary = self._summarize_execution(executed_steps)
        
        # Create a continuation prompt
        prompt = f"""
You are Kayas, an intelligent assistant executing a multi-step task.

Original goal: {goal}

Execution so far:
{step_summary}

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
            
            print(f"[MultiStepRunner] Model response: {response[:200]}...")
            
            # Parse the response
            try:
                decision = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group())
                else:
                    # If we can't parse, assume we're done
                    return False, None, "Could not parse model response; assuming task is complete"
            
            completed = decision.get("completed", False)
            reasoning = decision.get("reasoning", "No reasoning provided")
            next_steps = decision.get("next_steps")
            
            # If completed or no next steps, we're done
            if completed or next_steps is None:
                return False, None, reasoning
            
            # Otherwise, return the next plan
            if next_steps and len(next_steps) > 0:
                return True, next_steps, reasoning
            else:
                return False, None, reasoning or "Task appears complete"
        
        except Exception as e:
            # If there's an error getting continuation, assume we're done
            return False, None, f"Error checking continuation: {str(e)}"
    
    def _summarize_execution(self, executed_steps: List[StepResult]) -> str:
        """Create a summary of what has been executed so far."""
        summary_lines = []
        
        for step in executed_steps:
            action_name = step.action.get("tool", step.action.get("action", "unknown"))
            status = "✓" if step.success else "✗"
            
            summary_lines.append(f"{status} Step {step.step_number}: {action_name}")
            
            if step.success and step.output:
                # Add brief output summary
                if isinstance(step.output, dict):
                    if "response" in step.output:
                        summary_lines.append(f"   Response: {step.output['response'][:100]}")
                    elif "message" in step.output:
                        summary_lines.append(f"   Message: {step.output['message'][:100]}")
                    elif "result" in step.output:
                        summary_lines.append(f"   Result: {step.output['result'][:100]}")
            elif step.error:
                summary_lines.append(f"   Error: {step.error[:100]}")
        
        return "\n".join(summary_lines)
    
    def _generate_final_response(self, goal: str, context: ExecutionContext) -> str:
        """Generate a natural language response about what was accomplished."""
        
        if not context.executed_steps:
            return "I wasn't able to start the task. Please check if your request is clear."
        
        success_count = sum(1 for s in context.executed_steps if s.success)
        total_count = len(context.executed_steps)
        
        if context.completed:
            if success_count == total_count:
                return f"Done! I completed your request: {goal}. {context.completion_reason}"
            else:
                return (
                    f"I mostly completed your request ({success_count}/{total_count} steps succeeded). "
                    f"{context.completion_reason}"
                )
        else:
            return (
                f"I worked on your request but hit the step limit ({context.max_steps} steps). "
                f"I completed {success_count} actions so far. Would you like me to continue?"
            )


# Example usage and testing
if __name__ == "__main__":
    print("Multi-step runner module loaded successfully")
    print("\nThis module is designed to be used by DirectAgent for complex workflows.")
    print("It handles continuation logic to ensure multi-step tasks complete fully.")
