from __future__ import annotations

"""
UI Automation Proxy that runs pywinauto in a dedicated subprocess to avoid COM
threading conflicts in the main process.

Parent process API mirrors methods used in Router:
 - find_window(title?, class_name?, process_id?, best_match?)
 - list_windows()
 - click_button(window_title, button_text?, button_id?, button_class?)
 - type_text(window_title, text, control_id?, control_type?)
 - read_text(window_title, control_id?)
 - get_menu_items(window_title)
 - click_menu_item(window_title, menu_path)
 - focus_window(window_title)
 - close_window(window_title)
 - get_control_tree(window_title)
"""

from dataclasses import dataclass
from multiprocessing import get_context
from multiprocessing.connection import Connection
from typing import Any, Dict, Optional
import os


def _uia_worker_loop(conn: Connection, cfg: dict) -> None:
    """Child process: initialize COM for pywinauto and execute requests."""
    try:
        # Ensure pywinauto uses MTA (COINIT_MULTITHREADED) before any COM init
        os.environ.setdefault('PYWINAUTO_COINIT_FLAGS', '0')
        # Import inside the process to isolate COM initialization
        from .uiautomation_exec import UIAutomationExecutor, UIAutomationConfig
        exec_cfg = UIAutomationConfig(
            timeout=cfg.get("timeout", 10),
            retry_interval=cfg.get("retry_interval", 0.5),
            backend=cfg.get("backend", "uia"),
        )
        uia = UIAutomationExecutor(exec_cfg)
        conn.send({"ready": True, "backend": exec_cfg.backend})
    except Exception as e:
        try:
            conn.send({"ready": False, "error": str(e)})
        except Exception:
            pass
        return

    while True:
        try:
            msg = conn.recv()
        except EOFError:
            break
        if not isinstance(msg, dict):
            continue
        if msg.get("cmd") == "shutdown":
            break
        method = msg.get("method")
        kwargs = msg.get("kwargs", {})
        try:
            fn = getattr(uia, method)
        except AttributeError:
            conn.send({"success": False, "error": f"Unknown method: {method}"})
            continue
        try:
            res = fn(**kwargs)
            # Ensure result is JSON-serializable (pywinauto objects removed)
            if isinstance(res, dict) and "window" in res:
                res = {k: v for k, v in res.items() if k != "window"}
            conn.send(res)
        except Exception as e:
            conn.send({"success": False, "error": str(e)})


@dataclass
class UIAProxyConfig:
    timeout: int = 10
    retry_interval: float = 0.5
    backend: str = "uia"


class UIAutomationProxy:
    """Proxy around a UI Automation worker subprocess."""

    def __init__(self, cfg: UIAProxyConfig | None = None):
        self.cfg = cfg or UIAProxyConfig()
        ctx = get_context("spawn")
        parent_conn, child_conn = ctx.Pipe()
        self._conn: Connection = parent_conn
        self._proc = ctx.Process(target=_uia_worker_loop, args=(child_conn, self.cfg.__dict__), daemon=True)
        self._proc.start()
        # Wait for readiness message
        ready = self._conn.recv()
        if not ready.get("ready"):
            raise RuntimeError(f"UIA worker failed to start: {ready.get('error')}")
        # Note: ready may include which backend is active
        self.backend = ready.get("backend", self.cfg.backend)

    # Generic call helper
    def _call(self, method: str, **kwargs: Any) -> Dict[str, Any]:
        self._conn.send({"method": method, "kwargs": kwargs})
        return self._conn.recv()

    # Mirror executor methods used by Router
    def find_window(self, **kwargs: Any) -> Dict[str, Any]:
        return self._call("find_window", **kwargs)

    def list_windows(self) -> Dict[str, Any]:
        return self._call("list_windows")

    def click_button(self, **kwargs: Any) -> Dict[str, Any]:
        return self._call("click_button", **kwargs)

    def type_text(self, **kwargs: Any) -> Dict[str, Any]:
        return self._call("type_text", **kwargs)

    def read_text(self, **kwargs: Any) -> Dict[str, Any]:
        return self._call("read_text", **kwargs)

    def get_menu_items(self, **kwargs: Any) -> Dict[str, Any]:
        return self._call("get_menu_items", **kwargs)

    def click_menu_item(self, **kwargs: Any) -> Dict[str, Any]:
        return self._call("click_menu_item", **kwargs)

    def focus_window(self, **kwargs: Any) -> Dict[str, Any]:
        return self._call("focus_window", **kwargs)

    def close_window(self, **kwargs: Any) -> Dict[str, Any]:
        return self._call("close_window", **kwargs)

    def get_control_tree(self, **kwargs: Any) -> Dict[str, Any]:
        return self._call("get_control_tree", **kwargs)

    def shutdown(self) -> None:
        try:
            self._conn.send({"cmd": "shutdown"})
        except Exception:
            pass
        try:
            if self._proc.is_alive():
                self._proc.join(timeout=1.0)
        except Exception:
            pass
