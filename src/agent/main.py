from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Dict, List

from rich import print

from .config import artifacts_dir, db_path, ollama_model, chroma_dir, embed_model, search_root, smtp_config, strong_model, planning_mode, react_max_steps, react_beam_width, google_calendar_config, slack_config, spotify_config, desktop_enabled, llm_backend, hf_base_model, hf_adapter_dir, hf_merged_model_dir, hf_use_4bit, remote_base_url, remote_api_key, use_multi_candidate_planning, num_plan_candidates, max_action_retries
from .llm import LLM
from .hf_llm import HFLLM
from .http_llm import HTTPLLM
from .planner import Planner, plan_structured, plan_candidates, estimate_confidence
from .actions import Router, Action, parse_actions
from .safety import SafetyPolicy
from .execution_manager import ExecutionManager
from .plan_candidate import PlanCandidate
from ..executors.filesystem import FSConfig, FileSystemExecutor
from ..executors.local_search import LocalSearchConfig, LocalSearchExecutor
from ..executors.email_exec import EmailConfig, EmailExecutor
from ..executors.web_exec import WebConfig, WebExecutor
from ..executors.browser_exec import BrowserExecutor, BrowserConfig
from ..executors.desktop_exec import DesktopExecutor, DesktopConfig
from ..executors.process_exec import ProcessExecutor, ProcessConfig
from ..executors.uiautomation_exec import UIAutomationExecutor, UIAutomationConfig
from ..executors.perception_executor import PerceptionExecutor, PerceptionExecutorConfig
from ..executors.calendar_exec import GoogleCalendarExecutor, CalendarConfig
from ..executors.slack_exec import SlackExecutor, SlackConfig  
from ..executors.spotify_exec import SpotifyExecutor, SpotifyConfig
from ..executors.explorer_exec import ExplorerExecutor, ExplorerConfig
from ..memory.sqlite_memory import MemoryConfig, SQLiteMemory
from ..memory.vector_memory import VectorMemory, VectorMemoryConfig
from ..training.preference_model import score_plan
from .react import ReactAgent


def run_agent(goal: str) -> Dict[str, str]:
    run_id = str(uuid.uuid4())
    memory = SQLiteMemory(MemoryConfig(db_path=db_path()))
    memory.log_message(run_id, "user", goal)

    # Select backend
    backend = llm_backend()
    if backend == "hf":
        merged = hf_merged_model_dir()
        base_or_merged = merged if merged else hf_base_model()
        adapter = "" if merged else hf_adapter_dir()
        llm = HFLLM(base_or_merged, adapter_dir=adapter or None, use_4bit=hf_use_4bit())
    elif backend == "http":
        base_url = remote_base_url()
        if not base_url:
            raise RuntimeError("models.backend is 'http' but no models.remote.base_url configured in profile or REMOTE_LLM_BASE_URL env")
        llm = HTTPLLM(base_url=base_url, api_key=remote_api_key())
    else:
        llm = LLM(model=ollama_model())
    planner = Planner(llm)
    steps: List[str] = []

    fs = FileSystemExecutor(FSConfig(root=artifacts_dir()))
    local_search = LocalSearchExecutor(LocalSearchConfig(root=search_root()))
    email_exec = EmailExecutor(EmailConfig(**smtp_config()))
    web_exec = WebExecutor(WebConfig())
    browser_exec = BrowserExecutor(BrowserConfig())
    process_exec = ProcessExecutor(ProcessConfig())
    desktop_exec = DesktopExecutor(DesktopConfig()) if desktop_enabled() else None
    
    # UI Automation - only create if on Windows
    try:
        uia_exec = UIAutomationExecutor(UIAutomationConfig())
    except ImportError:
        uia_exec = None
    
    # Perception Engine - multi-layer UI interaction
    try:
        perception_exec = PerceptionExecutor(PerceptionExecutorConfig())
    except Exception:
        perception_exec = None
    
    # File Explorer automation
    try:
        explorer_exec = ExplorerExecutor(ExplorerConfig())
    except Exception:
        explorer_exec = None
    
    # API integrations - only create if credentials are available
    try:
        calendar_exec = GoogleCalendarExecutor(CalendarConfig(**google_calendar_config()))
    except Exception:
        calendar_exec = None
    
    try:
        slack_exec = SlackExecutor(SlackConfig(**slack_config()))
    except Exception:
        slack_exec = None
        
    try:
        spotify_exec = SpotifyExecutor(SpotifyConfig(**spotify_config()))
    except Exception:
        spotify_exec = None

    # Vector memory
    vmem = VectorMemory(VectorMemoryConfig(persist_dir=chroma_dir(), embed_model=embed_model()))

    # Retrieve related past tasks to prime context
    similar = vmem.query(goal, k=3)
    reuse_artifact: str = ""
    if similar:
        memory.log_message(run_id, "system", "Similar past tasks:\n" + "\n".join([f"- {s['document'][:200]}" for s in similar]))
        # Try to reuse an existing artifact from the most similar item
        for s in similar:
            meta = s.get("metadata") or {}
            path = meta.get("artifact")
            if path and Path(path).exists():
                reuse_artifact = path
                break
    default_filename = "freelancing-notes.txt" if "freelanc" in goal.lower() else "notes.txt"
    if reuse_artifact:
        default_filename = Path(reuse_artifact).name
        memory.log_message(run_id, "system", f"Reusing existing artifact: {reuse_artifact}")

    last_path: str = ""
    last_web_result: Dict[str, str] | None = None
    last_ui_text: str | None = None
    did_ui_read: bool = False
    # Planning entry point: structured or ReAct
    if planning_mode() == "react":
        # Build router with available executors
        router_executors = {
            "fs": fs,
            "web": web_exec,
            "email": email_exec,
            "search": local_search,
            "process": process_exec,
        }
        if calendar_exec:
            router_executors["calendar"] = calendar_exec
        if slack_exec:
            router_executors["slack"] = slack_exec
        if spotify_exec:
            router_executors["spotify"] = spotify_exec
            
        if desktop_exec:
            router_executors["desktop"] = desktop_exec
        if uia_exec:
            router_executors["uia"] = uia_exec
        if perception_exec:
            router_executors["perception"] = perception_exec
        if explorer_exec:
            router_executors["explorer"] = explorer_exec
        router = Router(router_executors, safety=SafetyPolicy())
        ra = ReactAgent(llm, router)
        rr = ra.run(goal, max_steps=react_max_steps(), beam_width=react_beam_width())
        for act in rr.actions_taken:
            memory.log_action(run_id, name=act.get("tool", "unknown"), params=act.get("args", {}), result=act.get("result", {}))
        # Persist final output if no artifact was produced
        last_path = ""
        if rr.final_text:
            # write to default notes
            target_name = "notes.txt"
            create_res = fs.create_file(target_name, rr.final_text)
            memory.log_action(run_id, name="filesystem.create_file", params={"filename": target_name}, result=create_res)
            last_path = create_res.get("path", str(artifacts_dir() / target_name))
        memory.log_message(run_id, "assistant", f"Completed. Artifact: {last_path}")
        # Save summary to vector memory
        doc = f"Goal: {goal}\nArtifact: {last_path}"
        vmem.add([doc], metadatas=[{"run_id": run_id, "artifact": last_path}], ids=[run_id])
        return {"run_id": run_id, "artifact": last_path}

    # Attempt a structured planning pass for better tool routing
    # Gather feedback hints from vector memory
    fb_results = [s for s in vmem.query(goal, k=5) if (s.get("metadata") or {}).get("type") == "feedback"]
    feedback_hints = "\n".join([r.get("document", "") for r in fb_results])
    structured_calls_json, raw_structured, used_prompt = plan_structured(planner.llm, goal, default_filename if reuse_artifact else None, feedback_hints=feedback_hints)
    if structured_calls_json:
        memory.log_message(run_id, "system", f"Structured plan: {raw_structured}")
        # Log plan for training
        memory.log_plan(run_id, ollama_model(), "structured", used_prompt, raw_structured)
        # Preference score the plan
        try:
            base_score = score_plan(used_prompt, raw_structured)
            memory.log_message(run_id, "system", f"Plan preference score: {base_score:.3f}")
        except Exception:
            base_score = None
    else:
        # Try stronger model if configured
        sm = strong_model()
        if sm:
            strong_llm = LLM(model=sm)
            structured_calls_json, raw_structured, used_prompt = plan_structured(strong_llm, goal, default_filename if reuse_artifact else None, feedback_hints=feedback_hints)
            if structured_calls_json:
                memory.log_message(run_id, "system", f"Structured plan (strong model): {raw_structured}")
                memory.log_plan(run_id, sm, "structured", used_prompt, raw_structured)
    # Build router with available executors
    router_executors = {
        "fs": fs,
        "web": web_exec,
        "browser": browser_exec,
        "email": email_exec,
        "search": local_search,
        "process": process_exec,
    }
    if calendar_exec:
        router_executors["calendar"] = calendar_exec
    if slack_exec:
        router_executors["slack"] = slack_exec
    if spotify_exec:
        router_executors["spotify"] = spotify_exec
    if desktop_exec:
        router_executors["desktop"] = desktop_exec
    if uia_exec:
        router_executors["uia"] = uia_exec
    if perception_exec:
        router_executors["perception"] = perception_exec
    if explorer_exec:
        router_executors["explorer"] = explorer_exec
        
    router = Router(router_executors, safety=SafetyPolicy())

    # ========== MULTI-CANDIDATE PLANNING WITH VERIFICATION ==========
    # If enabled, generate k candidate plans, rank them, and execute with fallback
    if use_multi_candidate_planning() and planning_mode() == "structured":
        print(f"[Agent] Using multi-candidate planning (k={num_plan_candidates()})")
        memory.log_message(run_id, "system", f"Multi-candidate planning enabled (k={num_plan_candidates()})")
        
        try:
            candidates = plan_candidates(
                planner.llm,
                goal,
                k=num_plan_candidates(),
                reuse_filename=default_filename if reuse_artifact else None,
                feedback_hints=feedback_hints
            )
            
            if candidates:
                # Log all candidates
                for i, cand in enumerate(candidates):
                    memory.log_message(
                        run_id,
                        "system",
                        f"Candidate {i+1}: {cand.strategy_name} - "
                        f"steps={cand.step_count}, risk={cand.risk_score:.2f}, "
                        f"conf={cand.confidence:.2f}, score={cand.overall_score():.2f}"
                    )
                
                # Execute with fallback
                exec_manager = ExecutionManager(router, max_retries=max_action_retries())
                plan_result = exec_manager.execute_with_fallback(candidates)
                
                if plan_result.success:
                    memory.log_message(
                        run_id,
                        "system",
                        f"Plan succeeded: {plan_result.plan_strategy} "
                        f"({len(plan_result.completed_actions)} actions)"
                    )
                    last_path = plan_result.artifact_path
                    
                    # Log each action for training
                    for exec_result in plan_result.completed_actions:
                        memory.log_action(
                            run_id,
                            name=exec_result.action.get("tool", "unknown"),
                            params=exec_result.action.get("args", {}),
                            result=exec_result.result
                        )
                else:
                    memory.log_message(
                        run_id,
                        "system",
                        f"All {len(candidates)} candidate plans failed"
                    )
                    if plan_result.failed_action:
                        memory.log_message(
                            run_id,
                            "system",
                            f"Last failure: {plan_result.failed_action.error}"
                        )
                
                # Skip the old single-plan execution
                memory.log_message(run_id, "assistant", f"Completed. Artifact: {last_path}")
                doc = f"Goal: {goal}\nArtifact: {last_path}"
                vmem.add([doc], metadatas=[{"run_id": run_id, "artifact": last_path}], ids=[run_id])
                return {"run_id": run_id, "artifact": last_path}
        except Exception as e:
            print(f"[Agent] Multi-candidate planning failed: {e}")
            memory.log_message(run_id, "system", f"Multi-candidate planning error: {e}, falling back to single plan")
            # Fall through to original single-plan execution

    # ========== ORIGINAL SINGLE-PLAN EXECUTION ==========
    # If we have a structured plan and a strong model is available, optionally compare if score is low
    if structured_calls_json:
        sm = strong_model()
        if sm and (base_score is not None) and base_score < 0.5:
            try:
                alt_llm = LLM(model=sm)
                alt_calls, alt_raw, alt_prompt = plan_structured(alt_llm, goal, default_filename if reuse_artifact else None, feedback_hints=feedback_hints)
                if alt_calls:
                    alt_score = score_plan(alt_prompt, alt_raw)
                    memory.log_message(run_id, "system", f"Alt plan score ({sm}): {alt_score:.3f}")
                    if alt_score > base_score:
                        structured_calls_json, raw_structured, used_prompt = alt_calls, alt_raw, alt_prompt
                        memory.log_message(run_id, "system", "Using alternative higher-scoring plan.")
            except Exception:
                pass
        def _sanitize_filename(name: str) -> str:
            # Remove characters invalid on Windows and trim length
            import re as _re
            name = name.strip().replace("\0", "")
            name = _re.sub(r'[<>:"/\\|?*]', "_", name)
            if len(name) > 120:
                base, ext = (name, "") if "." not in name else (".".join(name.split(".")[:-1]), "." + name.split(".")[-1])
                name = base[:100] + ext
            return name or "notes.txt"

        for item in structured_calls_json:
            action = Action(tool=item.get("tool", ""), args=item.get("args", {}))
            # Skip redundant file ops if reusing
            if reuse_artifact and action.tool.startswith("filesystem."):
                if action.tool == "filesystem.create_file":
                    memory.log_action(run_id, name="reuse_artifact", params=action.__dict__, result={"path": reuse_artifact, "skipped": True})
                    last_path = reuse_artifact
                    continue
                if action.tool == "filesystem.append_file":
                    # force filename to reuse target
                    action.args["filename"] = Path(reuse_artifact).name
            result = router.dispatch(action)
            # Self-correction on common errors
            if isinstance(result, dict) and result.get("error"):
                err = result.get("error", "").lower()
                # Invalid filename -> sanitize and retry
                if action.tool.startswith("filesystem.") and ("filename" in action.args) and ("invalid" in err or "illegal" in err or "file name" in err):
                    action.args["filename"] = _sanitize_filename(str(action.args.get("filename", "notes.txt")))
                    result = router.dispatch(action)
                # Missing/invalid URL -> try to extract URL from goal
                elif action.tool == "web.fetch":
                    import re as _re
                    m = _re.search(r"https?://\S+", goal)
                    if m:
                        action.args["url"] = m.group(0).rstrip(').,;')
                        result = router.dispatch(action)
            # Safety confirmation branch
            if result.get("needs_confirmation"):
                # For CLI, we can't do interactive input right now; pick safer alternative if available
                suggestion = result.get("suggestion")
                suggested_args = result.get("suggested_args") or {}
                if suggestion == "filesystem.archive_file":
                    # Prefer archive over delete
                    safer_action = Action(tool=suggestion, args=suggested_args)
                    result = router.dispatch(safer_action)
                    memory.log_action(run_id, name="safety_auto_choice", params={"original": action.__dict__}, result=result)
                else:
                    # Deny by default
                    memory.log_action(run_id, name="safety_denied", params=action.__dict__, result=result)
                    continue
            # capture web fetch results to materialize into a file later
            if action.tool == "web.fetch" and isinstance(result, dict):
                last_web_result = result
            # capture UI text reads for later summarization/materialization
            if action.tool == "uia.read_text" and isinstance(result, dict):
                did_ui_read = True
                t = result.get("text")
                if isinstance(t, str) and t.strip():
                    last_ui_text = t
            if isinstance(result, dict) and result.get("path"):
                last_path = result["path"]
            memory.log_action(run_id, name=action.tool, params=action.args, result=result)

        # If structured run didn't create/update a file but we fetched web content, persist a summary
        if not last_path and last_web_result:
            content_lines = []
            title = last_web_result.get("title") or "Web Result"
            url = last_web_result.get("url") or ""
            excerpt = last_web_result.get("excerpt") or last_web_result.get("content") or ""
            # Summarize the excerpt into concise bullets
            try:
                summary_prompt = (
                    "Summarize the following content into 5-8 concise bullet points focusing on key facts and definitions.\n"
                    "Use plain text bullets starting with '- '. Avoid boilerplate like navigation or menu items.\n\n"
                    f"CONTENT:\n{excerpt[:4000]}"
                )
                summary_text = llm.generate(summary_prompt, system="You are a precise summarizer.", temperature=0.2)
            except Exception:
                summary_text = ""
            # Fallback: basic bulletizer if model output isn't bullet-y
            if not summary_text or "- " not in summary_text[:200]:
                # take first ~10 sentences as bullets
                import re as _re
                sentences = _re.split(r"(?<=[.!?])\s+", excerpt)
                bullets = [f"- {s.strip()}" for s in sentences if len(s.strip()) > 0][:8]
                summary_text = "\n".join(bullets)
            content_lines.append(f"Title: {title}")
            if url:
                content_lines.append(f"URL: {url}")
            if summary_text:
                content_lines.append("")
                content_lines.append(summary_text)
            content = "\n".join(content_lines).strip()
            target_name = Path(reuse_artifact).name if reuse_artifact else default_filename
            # Always overwrite with fresh summary to avoid stale boilerplate
            target_path = (artifacts_dir() / target_name)
            create_res = fs.create_file(target_name, content if content else f"Notes for goal: {goal}")
            memory.log_action(run_id, name="filesystem.create_file", params={"filename": target_name}, result=create_res)
            last_path = create_res.get("path", str(target_path))
        # If we captured UI text (e.g., Notepad content) but no artifact exists, summarize and save it
        if not last_path and (last_ui_text or did_ui_read):
            try:
                summary_prompt = (
                    "You are given raw text captured from a Notepad window on the user's screen.\n"
                    "Succinctly define what's on the screen in 3-6 bullets.\n"
                    "If it's short, include the exact text first, then a brief interpretation.\n\n"
                    f"TEXT:\n{(last_ui_text or '').strip()[:6000]}"
                )
                summary = llm.generate(summary_prompt, system="You are a precise desktop content summarizer.", temperature=0.2)
            except Exception:
                summary = last_ui_text or ""
            target_name = Path(reuse_artifact).name if reuse_artifact else default_filename
            target_path = (artifacts_dir() / target_name)
            if last_ui_text and last_ui_text.strip():
                body = f"Captured Notepad Content:\n\n{last_ui_text}\n\nSummary:\n{summary}" if summary and summary.strip() else last_ui_text
            else:
                body = summary if summary.strip() else "No readable Notepad content was detected."
            create_res = fs.create_file(target_name, body)
            memory.log_action(run_id, name="filesystem.create_file", params={"filename": target_name}, result=create_res)
            last_path = create_res.get("path", str(target_path))
    else:
        # No structured plan available; attempt structured fallback instead of legacy text steps
        fallback_calls, raw_fallback, used_prompt = plan_structured(planner.llm, goal, default_filename if reuse_artifact else None, feedback_hints=feedback_hints)
        if fallback_calls:
            memory.log_message(run_id, "system", f"Fallback structured plan: {raw_fallback}")
            memory.log_plan(run_id, ollama_model(), "structured-fallback", used_prompt, raw_fallback)
        else:
            # Minimal deterministic fallback: create a notes file with the goal
            fallback_calls = [{"tool": "filesystem.create_file", "args": {"filename": default_filename, "content": f"Goal: {goal}\n"}}]

        for item in fallback_calls:
            action = Action(tool=item.get("tool", ""), args=item.get("args", {}))
            if reuse_artifact and action.tool.startswith("filesystem."):
                if action.tool == "filesystem.create_file":
                    memory.log_action(run_id, name="reuse_artifact", params=action.__dict__, result={"path": reuse_artifact, "skipped": True})
                    last_path = reuse_artifact
                    continue
                if action.tool == "filesystem.append_file":
                    action.args["filename"] = Path(reuse_artifact).name

            result = router.dispatch(action)

            if isinstance(result, dict) and result.get("error"):
                err = result.get("error", "").lower()
                if action.tool.startswith("filesystem.") and ("filename" in action.args) and ("invalid" in err or "illegal" in err or "file name" in err):
                    action.args["filename"] = _sanitize_filename(str(action.args.get("filename", "notes.txt")))
                    result = router.dispatch(action)

            if action.tool == "web.fetch" and isinstance(result, dict):
                last_web_result = result
            if action.tool == "uia.read_text" and isinstance(result, dict):
                did_ui_read = True
                t = result.get("text")
                if isinstance(t, str) and t.strip():
                    last_ui_text = t
            if isinstance(result, dict) and result.get("path"):
                last_path = result["path"]
            memory.log_action(run_id, name=action.tool, params=action.args, result=result)

        # If fallback structured run didn't create/update a file but we fetched web content, persist a summary
        if not last_path and last_web_result:
            content_lines = []
            title = last_web_result.get("title") or "Web Result"
            url = last_web_result.get("url") or ""
            excerpt = last_web_result.get("excerpt") or last_web_result.get("content") or ""
            try:
                summary_prompt = (
                    "Summarize the following content into 5-8 concise bullet points focusing on key facts and definitions.\n"
                    "Use plain text bullets starting with '- '. Avoid boilerplate like navigation or menu items.\n\n"
                    f"CONTENT:\n{excerpt[:4000]}"
                )
                summary_text = llm.generate(summary_prompt, system="You are a precise summarizer.", temperature=0.2)
            except Exception:
                summary_text = ""
            if not summary_text or "- " not in summary_text[:200]:
                import re as _re
                sentences = _re.split(r"(?<=[.!?])\s+", excerpt)
                bullets = [f"- {s.strip()}" for s in sentences if len(s.strip()) > 0][:8]
                summary_text = "\n".join(bullets)
            content_lines.append(f"Title: {title}")
            if url:
                content_lines.append(f"URL: {url}")
            if summary_text:
                content_lines.append("")
                content_lines.append(summary_text)
            content = "\n".join(content_lines).strip()
            target_name = Path(reuse_artifact).name if reuse_artifact else default_filename
            target_path = (artifacts_dir() / target_name)
            create_res = fs.create_file(target_name, content if content else f"Notes for goal: {goal}")
            memory.log_action(run_id, name="filesystem.create_file", params={"filename": target_name}, result=create_res)
            last_path = create_res.get("path", str(target_path))
        if not last_path and (last_ui_text or did_ui_read):
            try:
                summary_prompt = (
                    "You are given raw text captured from a Notepad window on the user's screen.\n"
                    "Succinctly define what's on the screen in 3-6 bullets.\n"
                    "If it's short, include the exact text first, then a brief interpretation.\n\n"
                    f"TEXT:\n{(last_ui_text or '').strip()[:6000]}"
                )
                summary = llm.generate(summary_prompt, system="You are a precise desktop content summarizer.", temperature=0.2)
            except Exception:
                summary = last_ui_text or ""
            target_name = Path(reuse_artifact).name if reuse_artifact else default_filename
            target_path = (artifacts_dir() / target_name)
            if last_ui_text and last_ui_text.strip():
                body = f"Captured Notepad Content:\n\n{last_ui_text}\n\nSummary:\n{summary}" if summary and summary.strip() else last_ui_text
            else:
                body = summary if summary.strip() else "No readable Notepad content was detected."
            create_res = fs.create_file(target_name, body)
            memory.log_action(run_id, name="filesystem.create_file", params={"filename": target_name}, result=create_res)
            last_path = create_res.get("path", str(target_path))

    memory.log_message(run_id, "assistant", f"Completed. Artifact: {last_path}")

    # Save summary to vector memory
    doc = f"Goal: {goal}\nArtifact: {last_path}"
    vmem.add([doc], metadatas=[{"run_id": run_id, "artifact": last_path}], ids=[run_id])
    return {"run_id": run_id, "artifact": last_path}


def main(argv: List[str]) -> int:
    if not argv:
        print("[red]Please provide a goal string.[/red]")
        return 2
    goal = " ".join(argv).strip()
    try:
        out = run_agent(goal)
        print(f"[green]Done[/green]. Run: {out['run_id']}\nArtifact: {out['artifact']}")
        return 0
    except Exception as e:
        print(f"[red]Error:[/red] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
