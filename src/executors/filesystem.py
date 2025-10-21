from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from ..agent.config import archive_dir, sandbox_mode


@dataclass
class FSConfig:
    root: Path


class FileSystemExecutor:
    def __init__(self, cfg: FSConfig):
        self.cfg = cfg
        self.cfg.root.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, name: str) -> Path:
        # Allow relative subpaths but prevent escaping root
        p = Path(name)
        if p.is_absolute():
            # Drop directory components for absolute paths, keep basename only
            p = Path(p.name)
        # If the path redundantly starts with the artifacts root name (e.g., 'artifacts/notes.txt'), strip it
        if p.parts and p.parts[0].lower() == self.cfg.root.name.lower():
            p = Path(*p.parts[1:]) if len(p.parts) > 1 else Path(p.name)
        full = (self.cfg.root / p).resolve()
        root = self.cfg.root.resolve()
        try:
            common = os.path.commonpath([str(full), str(root)])
        except Exception:
            common = str(root)
        if common != str(root):
            # Path traversal detected; fall back to basename under root
            full = (root / p.name).resolve()
        full.parent.mkdir(parents=True, exist_ok=True)
        return full

    def create_file(self, filename: str, content: str = "") -> Dict[str, str]:
        path = self._resolve_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"action": "filesystem.create_file", "path": str(path)}

    def append_file(self, filename: str, content: str) -> Dict[str, str]:
        path = self._resolve_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(content)
        return {"action": "filesystem.append_file", "path": str(path)}

    def delete_file(self, filename: str) -> Dict[str, str]:
        p = self._resolve_path(filename)
        mode = sandbox_mode()
        if mode in ("dry-run", "enforced"):
            # Don't actually delete in sandbox or dry-run
            return {"action": "filesystem.delete_file", "path": str(p), "sandbox": mode, "deleted": False}
        try:
            p.unlink(missing_ok=True)
            return {"action": "filesystem.delete_file", "path": str(p), "deleted": True}
        except Exception as e:
            return {"action": "filesystem.delete_file", "path": str(p), "error": str(e)}

    def archive_file(self, filename: str) -> Dict[str, str]:
        p = self._resolve_path(filename)
        arch_dir = archive_dir()
        arch_dir.mkdir(parents=True, exist_ok=True)
        target = arch_dir / p.name
        mode = sandbox_mode()
        if mode == "dry-run":
            return {"action": "filesystem.archive_file", "source": str(p), "target": str(target), "sandbox": mode, "moved": False}
        try:
            shutil.move(str(p), str(target))
            return {"action": "filesystem.archive_file", "source": str(p), "target": str(target), "moved": True}
        except Exception as e:
            return {"action": "filesystem.archive_file", "source": str(p), "target": str(target), "error": str(e)}

    def execute_step(self, step: str, goal: str, default_filename: Optional[str] = None) -> Dict[str, str]:
        s = step.lower()
        # Basic intent parsing
        if "create" in s and "file" in s:
            # try to extract a quoted filename
            m = re.search(r"'([^']+)'|\"([^\"]+)\"", step)
            if m:
                filename = m.group(1) or m.group(2)
            else:
                filename = default_filename or "notes.txt"
            result = self.create_file(filename, "")
            return result
        if any(k in s for k in ["write", "append", "add"]):
            filename = default_filename or "notes.txt"
            summary = summarize_goal(goal)
            result = self.append_file(filename, "\n" + summary + "\n")
            return result
        # Fallback: ensure file exists then append summary
        filename = default_filename or "notes.txt"
        if not self._resolve_path(filename).exists():
            self.create_file(filename, "")
        summary = summarize_goal(goal)
        result = self.append_file(filename, "\n" + summary + "\n")
        return result


def summarize_goal(goal: str) -> str:
    g = goal.strip().rstrip(".")
    return f"Summary based on goal: {g}. Key points: objectives, steps, and next actions."
