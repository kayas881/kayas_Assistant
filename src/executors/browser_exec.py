from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path
import time
import json

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from ..agent.config import artifacts_dir


@dataclass
class BrowserConfig:
    headless: bool = True
    default_timeout_ms: int = 10000
    user_agent: Optional[str] = None
    viewport_width: int = 1280
    viewport_height: int = 800


class BrowserExecutor:
    def __init__(self, cfg: BrowserConfig | None = None):
        self.cfg = cfg or BrowserConfig()

    def run_steps(
        self,
        steps: List[Dict[str, Any]],
        headless: Optional[bool] = None,
        base_url: Optional[str] = None,
        session_name: Optional[str] = None,
        persist_session: Optional[bool] = None,
        stop_on_error: bool = True,
    ) -> Dict[str, Any]:
        if not PLAYWRIGHT_AVAILABLE:
            return {"error": "Playwright not available. Install with 'pip install playwright' and run 'python -m playwright install'"}

        trace: List[Dict[str, Any]] = []
        screenshots: List[str] = []
        extracted: List[Any] = []
        success = True

        h = self.cfg.headless if headless is None else bool(headless)
        art_dir = artifacts_dir()
        art_dir.mkdir(parents=True, exist_ok=True)

        # Session persistence setup
        sessions_dir = (Path('.agent') / 'browser_sessions').resolve()
        storage_state_dict: Optional[dict] = None
        state_file: Optional[Path] = None
        if session_name:
            sessions_dir.mkdir(parents=True, exist_ok=True)
            state_file = (sessions_dir / f"{session_name}.json").resolve()
            if state_file.exists():
                try:
                    storage_state_dict = json.loads(state_file.read_text(encoding='utf-8'))
                except Exception:
                    storage_state_dict = None

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=h)
            context_kwargs: Dict[str, Any] = {
                "user_agent": self.cfg.user_agent or None,
                "viewport": {"width": self.cfg.viewport_width, "height": self.cfg.viewport_height},
                "base_url": base_url or None,
            }
            if storage_state_dict:
                context_kwargs["storage_state"] = storage_state_dict
            elif state_file and state_file.exists():
                # Fallback: try passing path if dict failed to load
                context_kwargs["storage_state"] = str(state_file)

            context = browser.new_context(**context_kwargs)
            context.set_default_timeout(self.cfg.default_timeout_ms)
            page = context.new_page()

            for i, step in enumerate(steps or []):
                if not isinstance(step, dict):
                    trace.append({"step": i, "error": "Invalid step format"})
                    if stop_on_error:
                        success = False
                        break
                    else:
                        continue
                action = str(step.get("action", "")).lower()
                args = step.get("args", {}) or {}
                try:
                    if action == "goto":
                        url = args.get("url")
                        if not url:
                            raise ValueError("goto requires 'url'")
                        page.goto(url)
                        trace.append({"step": i, "action": action, "url": url})
                    elif action == "click":
                        sel = args.get("selector")
                        if not sel:
                            raise ValueError("click requires 'selector'")
                        page.click(sel)
                        trace.append({"step": i, "action": action, "selector": sel})
                    elif action == "fill":
                        sel = args.get("selector")
                        val = args.get("value", "")
                        if not sel:
                            raise ValueError("fill requires 'selector'")
                        page.fill(sel, str(val))
                        trace.append({"step": i, "action": action, "selector": sel, "value": val})
                    elif action == "type":
                        sel = args.get("selector")
                        text = args.get("text", "")
                        delay = args.get("delay_ms", 0)
                        if not sel:
                            raise ValueError("type requires 'selector'")
                        page.click(sel)
                        page.type(sel, str(text), delay=int(delay))
                        trace.append({"step": i, "action": action, "selector": sel, "text": text})
                    elif action == "press":
                        sel = args.get("selector")
                        key = args.get("key")
                        if not sel or not key:
                            raise ValueError("press requires 'selector' and 'key'")
                        page.press(sel, str(key))
                        trace.append({"step": i, "action": action, "selector": sel, "key": key})
                    elif action == "login_flow":
                        # Heuristic login with retries
                        url = args.get("url")
                        if url:
                            page.goto(url)
                        user_sel = args.get("username_selector")
                        pass_sel = args.get("password_selector")
                        username = args.get("username")
                        password = args.get("password")
                        submit_sel = args.get("submit_selector")
                        success_sel = args.get("success_selector")
                        error_sel = args.get("error_selector")
                        wait_success_ms = int(args.get("wait_success_ms", 8000))
                        retry_count = int(args.get("retry_count", 2))
                        retry_delay_ms = int(args.get("retry_delay_ms", 1500))
                        clear_before_retry = bool(args.get("clear_before_retry", True))
                        if not user_sel or not pass_sel:
                            raise ValueError("login_flow requires 'username_selector' and 'password_selector'")
                        attempts = 0
                        logged_in = False
                        last_error: Optional[str] = None
                        while attempts <= retry_count and not logged_in:
                            attempts += 1
                            try:
                                page.wait_for_selector(user_sel)
                                page.fill(user_sel, str(username) if username is not None else "")
                                page.fill(pass_sel, str(password) if password is not None else "")
                                if submit_sel:
                                    page.click(submit_sel)
                                else:
                                    page.press(pass_sel, "Enter")
                                # Wait for success or error
                                success = False
                                start = time.time()
                                while (time.time() - start) * 1000 < wait_success_ms:
                                    if success_sel:
                                        if page.query_selector(success_sel):
                                            success = True
                                            break
                                    # Navigation heuristic: URL change or content loaded
                                    # Give a small sleep
                                    time.sleep(0.2)
                                if not success and success_sel:
                                    # As a fallback, try a brief wait_for_selector
                                    try:
                                        page.wait_for_selector(success_sel, state='visible', timeout=1000)
                                        success = True
                                    except Exception:
                                        success = False
                                if not success and error_sel:
                                    if page.query_selector(error_sel):
                                        last_error = "login error detected"
                                if success:
                                    logged_in = True
                                    trace.append({"step": i, "action": action, "attempt": attempts, "status": "success"})
                                    break
                                if attempts <= retry_count:
                                    if clear_before_retry:
                                        try:
                                            page.fill(user_sel, "")
                                            page.fill(pass_sel, "")
                                        except Exception:
                                            pass
                                    time.sleep(retry_delay_ms / 1000.0)
                            except Exception as le:
                                last_error = str(le)
                                if attempts <= retry_count:
                                    time.sleep(retry_delay_ms / 1000.0)
                        if not logged_in:
                            raise RuntimeError(last_error or "login failed after retries")
                        # If logged in and a success selector exists, ensure it's visible for trace
                        if success_sel:
                            try:
                                page.wait_for_selector(success_sel, state='visible', timeout=1000)
                            except Exception:
                                pass
                        trace.append({"step": i, "action": action, "attempts": attempts, "result": "logged_in"})
                    elif action == "wait_for_selector":
                        sel = args.get("selector")
                        state = args.get("state", "visible")
                        if not sel:
                            raise ValueError("wait_for_selector requires 'selector'")
                        page.wait_for_selector(sel, state=state)
                        trace.append({"step": i, "action": action, "selector": sel, "state": state})
                    elif action == "wait":
                        ms = int(args.get("ms", 1000))
                        time.sleep(ms / 1000.0)
                        trace.append({"step": i, "action": action, "ms": ms})
                    elif action == "extract_text":
                        sel = args.get("selector")
                        all_ = bool(args.get("all", False))
                        if not sel:
                            raise ValueError("extract_text requires 'selector'")
                        if all_:
                            els = page.query_selector_all(sel)
                            vals = [e.inner_text().strip() for e in els]
                        else:
                            el = page.query_selector(sel)
                            vals = el.inner_text().strip() if el else ""
                        extracted.append(vals)
                        trace.append({"step": i, "action": action, "selector": sel, "result_len": (len(vals) if isinstance(vals, list) else (1 if vals else 0))})
                    elif action == "screenshot":
                        sel = args.get("selector")
                        full_page = bool(args.get("full_page", not bool(sel)))
                        fname = args.get("filename") or f"screenshot_{int(time.time()*1000)}.png"
                        out_path = (art_dir / fname).resolve()
                        if sel:
                            el = page.query_selector(sel)
                            if not el:
                                raise ValueError("screenshot selector not found")
                            el.screenshot(path=str(out_path))
                        else:
                            page.screenshot(path=str(out_path), full_page=full_page)
                        screenshots.append(str(out_path))
                        trace.append({"step": i, "action": action, "path": str(out_path)})
                    elif action == "set_viewport":
                        w = int(args.get("width", self.cfg.viewport_width))
                        h = int(args.get("height", self.cfg.viewport_height))
                        page.set_viewport_size({"width": w, "height": h})
                        trace.append({"step": i, "action": action, "width": w, "height": h})
                    elif action == "check":
                        sel = args.get("selector")
                        if not sel:
                            raise ValueError("check requires 'selector'")
                        page.check(sel)
                        trace.append({"step": i, "action": action, "selector": sel})
                    elif action == "uncheck":
                        sel = args.get("selector")
                        if not sel:
                            raise ValueError("uncheck requires 'selector'")
                        page.uncheck(sel)
                        trace.append({"step": i, "action": action, "selector": sel})
                    else:
                        trace.append({"step": i, "error": f"Unknown action: {action}"})
                        if stop_on_error:
                            success = False
                            break
                except PWTimeoutError as e:
                    trace.append({"step": i, "error": f"Timeout: {str(e)}", "action": action})
                    if stop_on_error:
                        success = False
                        break
                except Exception as e:
                    trace.append({"step": i, "error": str(e), "action": action})
                    if stop_on_error:
                        success = False
                        break

            # Save session state if requested
            do_persist = bool(persist_session) if persist_session is not None else bool(session_name)
            if do_persist and session_name and sessions_dir:
                try:
                    sessions_dir.mkdir(parents=True, exist_ok=True)
                    target_file = (sessions_dir / f"{session_name}.json").resolve()
                    context.storage_state(path=str(target_file))
                    trace.append({"action": "persist_session", "path": str(target_file)})
                except Exception as e:
                    trace.append({"action": "persist_session", "error": str(e)})

            context.close()
            browser.close()

        return {
            "action": "browser.run_steps",
            "success": success,
            "trace": trace,
            "extracted": extracted,
            "screenshots": screenshots,
        }
