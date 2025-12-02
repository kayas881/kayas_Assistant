from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from .actions import Router, Action
from .plan_candidate import PlanCandidate


@dataclass
class ExecutionResult:
    """Result of executing a single action with verification."""
    success: bool
    action: Dict[str, Any]
    result: Dict[str, Any]
    verification_passed: bool = True
    error: str = ""
    retry_count: int = 0


@dataclass
class PlanExecutionResult:
    """Result of executing an entire plan."""
    success: bool
    plan_strategy: str
    completed_actions: List[ExecutionResult]
    failed_action: Optional[ExecutionResult] = None
    artifact_path: str = ""


class ExecutionManager:
    """
    Manages plan execution with verification and retry logic.
    """
    
    def __init__(self, router: Router, max_retries: int = 2, retry_delay_sec: float = 1.0):
        self.router = router
        self.max_retries = max_retries
        self.retry_delay_sec = retry_delay_sec
    
    def verify_action_result(self, action: Dict[str, Any], result: Dict[str, Any]) -> tuple[bool, str]:
        """
        Verify that an action result meets expected criteria.
        
        Returns (success: bool, error_message: str)
        """
        tool = action.get("tool", "")
        
        # Check for explicit errors in result
        if isinstance(result, dict):
            if result.get("error"):
                return False, f"Action returned error: {result.get('error')}"
            
            if result.get("needs_confirmation"):
                return False, "Action blocked by safety policy"
        
        # Tool-specific verification
        if tool.startswith("filesystem."):
            return self._verify_filesystem(action, result)
        elif tool == "web.fetch":
            return self._verify_web_fetch(action, result)
        elif tool.startswith("browser."):
            return self._verify_browser(action, result)
        elif tool.startswith("uia."):
            return self._verify_ui_automation(action, result)
        elif tool.startswith("process."):
            return self._verify_process(action, result)
        else:
            # Generic verification: check for success flag or non-empty result
            if isinstance(result, dict) and result.get("success") is False:
                return False, "Action reported failure"
            return True, ""
    
    def _verify_filesystem(self, action: Dict[str, Any], result: Dict[str, Any]) -> tuple[bool, str]:
        """Verify filesystem operations."""
        tool = action.get("tool", "")
        
        if tool == "filesystem.create_file":
            path = result.get("path")
            if not path:
                return False, "No path returned"
            if not Path(path).exists():
                return False, f"File not created: {path}"
            return True, ""
        
        elif tool == "filesystem.append_file":
            if not result.get("success"):
                return False, "Append failed"
            return True, ""
        
        elif tool == "filesystem.delete_file":
            # Deletion success if either deleted or file didn't exist
            return True, ""
        
        return True, ""
    
    def _verify_web_fetch(self, action: Dict[str, Any], result: Dict[str, Any]) -> tuple[bool, str]:
        """Verify web fetch operations."""
        if not isinstance(result, dict):
            return False, "Invalid result type"
        
        # Check for content
        content = result.get("content") or result.get("excerpt") or result.get("text")
        if not content or len(str(content).strip()) < 10:
            return False, "No meaningful content fetched"
        
        # Check for error indicators
        if "error" in str(content).lower()[:100] and "404" in str(content):
            return False, "Page not found"
        
        return True, ""
    
    def _verify_browser(self, action: Dict[str, Any], result: Dict[str, Any]) -> tuple[bool, str]:
        """Verify browser automation."""
        if not isinstance(result, dict):
            return False, "Invalid result type"
        
        # Check for browser errors
        if result.get("error") or result.get("failed"):
            return False, result.get("error", "Browser action failed")
        
        # If steps were provided, check if any failed
        steps_results = result.get("steps_results", [])
        if steps_results:
            failed_steps = [s for s in steps_results if not s.get("success", True)]
            if failed_steps:
                return False, f"{len(failed_steps)} browser steps failed"
        
        return True, ""
    
    def _verify_ui_automation(self, action: Dict[str, Any], result: Dict[str, Any]) -> tuple[bool, str]:
        """Verify UI automation actions."""
        if not isinstance(result, dict):
            return False, "Invalid result type"
        
        if not result.get("success"):
            return False, result.get("error", "UI action failed")
        
        tool = action.get("tool", "")
        
        # For read_text, verify we got text
        if tool == "uia.read_text":
            text = result.get("text", "")
            if not text or not isinstance(text, str):
                return False, "No text read from UI"
        
        return True, ""
    
    def _verify_process(self, action: Dict[str, Any], result: Dict[str, Any]) -> tuple[bool, str]:
        """Verify process operations."""
        tool = action.get("tool", "")
        
        if tool == "process.run_command":
            # Check exit code
            exit_code = result.get("exit_code")
            if exit_code is not None and exit_code != 0:
                return False, f"Command exited with code {exit_code}"
        
        return True, ""
    
    def execute_action_with_retry(self, action: Dict[str, Any]) -> ExecutionResult:
        """
        Execute a single action with retry on failure.
        """
        action_obj = Action(tool=action.get("tool", ""), args=action.get("args", {}))
        
        for attempt in range(self.max_retries + 1):
            # Execute action
            result = self.router.dispatch(action_obj)
            
            # Verify result
            verified, error_msg = self.verify_action_result(action, result)
            
            if verified:
                return ExecutionResult(
                    success=True,
                    action=action,
                    result=result,
                    verification_passed=True,
                    retry_count=attempt
                )
            
            # If verification failed and we have retries left, wait and retry
            if attempt < self.max_retries:
                print(f"[ExecutionManager] Action {action_obj.tool} failed verification (attempt {attempt + 1}/{self.max_retries + 1}): {error_msg}")
                print(f"[ExecutionManager] Retrying in {self.retry_delay_sec}s...")
                time.sleep(self.retry_delay_sec * (attempt + 1))  # Exponential backoff
            else:
                # Final attempt failed
                return ExecutionResult(
                    success=False,
                    action=action,
                    result=result,
                    verification_passed=False,
                    error=error_msg,
                    retry_count=attempt
                )
        
        # Should never reach here
        return ExecutionResult(
            success=False,
            action=action,
            result={},
            verification_passed=False,
            error="Max retries exceeded",
            retry_count=self.max_retries
        )
    
    def execute_plan(self, plan: PlanCandidate) -> PlanExecutionResult:
        """
        Execute a complete plan with verification at each step.
        
        Stops on first failed action and returns result.
        """
        completed: List[ExecutionResult] = []
        
        print(f"[ExecutionManager] Executing plan: {plan.strategy_name} ({plan.step_count} steps)")
        
        for i, action in enumerate(plan.actions):
            print(f"[ExecutionManager] Step {i+1}/{plan.step_count}: {action.get('tool')}")
            
            exec_result = self.execute_action_with_retry(action)
            completed.append(exec_result)
            
            if not exec_result.success:
                print(f"[ExecutionManager] Plan failed at step {i+1}: {exec_result.error}")
                return PlanExecutionResult(
                    success=False,
                    plan_strategy=plan.strategy_name,
                    completed_actions=completed,
                    failed_action=exec_result
                )
            
            # Extract artifact path if present
            if isinstance(exec_result.result, dict) and exec_result.result.get("path"):
                artifact_path = exec_result.result.get("path", "")
            else:
                artifact_path = ""
        
        # All actions succeeded
        last_artifact = ""
        for exec_result in reversed(completed):
            if isinstance(exec_result.result, dict) and exec_result.result.get("path"):
                last_artifact = exec_result.result["path"]
                break
        
        print(f"[ExecutionManager] Plan completed successfully: {plan.strategy_name}")
        return PlanExecutionResult(
            success=True,
            plan_strategy=plan.strategy_name,
            completed_actions=completed,
            artifact_path=last_artifact
        )
    
    def execute_with_fallback(self, candidates: List[PlanCandidate]) -> PlanExecutionResult:
        """
        Execute plans in order until one succeeds.
        
        Returns result of the first successful plan, or the last failed plan.
        """
        if not candidates:
            return PlanExecutionResult(
                success=False,
                plan_strategy="none",
                completed_actions=[],
                failed_action=ExecutionResult(
                    success=False,
                    action={},
                    result={},
                    error="No candidate plans provided"
                )
            )
        
        print(f"[ExecutionManager] Executing {len(candidates)} candidate plans with fallback")
        
        last_result = None
        for i, candidate in enumerate(candidates):
            print(f"[ExecutionManager] Attempting plan {i+1}/{len(candidates)}: {candidate.strategy_name}")
            
            result = self.execute_plan(candidate)
            
            if result.success:
                print(f"[ExecutionManager] Plan succeeded: {candidate.strategy_name}")
                return result
            else:
                print(f"[ExecutionManager] Plan failed: {candidate.strategy_name}")
                last_result = result
                
                # If not the last plan, wait before trying next
                if i < len(candidates) - 1:
                    print(f"[ExecutionManager] Falling back to next plan...")
                    time.sleep(0.5)
        
        # All plans failed
        print(f"[ExecutionManager] All {len(candidates)} plans failed")
        return last_result or PlanExecutionResult(
            success=False,
            plan_strategy="all_failed",
            completed_actions=[]
        )
