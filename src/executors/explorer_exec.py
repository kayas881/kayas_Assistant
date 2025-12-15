"""src.executors.explorer_exec

Windows File Explorer automation.

Design goals:
- Always be importable (no hard dependency on UI automation libraries).
- Make navigation to common folders reliable by using `explorer.exe` with `shell:` monikers.
- Provide safe direct filesystem operations for copy/move/list/info/delete.
- For UI-only features (pane toggles, view changes, back/forward), return a clear
  error instead of raising AttributeError.

This executor is intentionally conservative: it prefers robustness over deep UI control.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


# Optional UI automation dependencies (not required)
try:
    from pywinauto.keyboard import send_keys  # type: ignore

    PYWINAUTO_AVAILABLE = True
except Exception:
    send_keys = None  # type: ignore
    PYWINAUTO_AVAILABLE = False


@dataclass
class ExplorerConfig:
    timeout: int = 7


class ExplorerExecutor:
    def __init__(self, config: Optional[ExplorerConfig] = None):
        self.config = config or ExplorerConfig()

    # --------------------------
    # Helpers
    # --------------------------
    def _normalize_path(self, path: str) -> str:
        # Resolve common known-folder names to actual filesystem locations.
        # (We can't use shell: monikers for direct filesystem operations like mkdir.)
        p = str(path).strip().strip('"').strip("'")

        lower = p.lower()
        user_profile = os.environ.get("USERPROFILE") or str(Path.home())
        onedrive = os.environ.get("OneDrive")

        def pick_existing(primary: Path, secondary: Optional[Path] = None) -> Path:
            if primary.exists():
                return primary
            if secondary and secondary.exists():
                return secondary
            return primary

        if lower in {"desktop", "desktop folder"}:
            return str(pick_existing(Path(user_profile) / "Desktop", Path(onedrive) / "Desktop" if onedrive else None))
        if lower in {"downloads", "download", "downloads folder", "download folder"}:
            return str(Path(user_profile) / "Downloads")
        if lower in {"documents", "document", "documents folder", "document folder"}:
            return str(pick_existing(Path(user_profile) / "Documents", Path(onedrive) / "Documents" if onedrive else None))
        if lower in {"pictures", "photos", "pictures folder"}:
            return str(pick_existing(Path(user_profile) / "Pictures", Path(onedrive) / "Pictures" if onedrive else None))
        if lower in {"music", "music folder"}:
            return str(Path(user_profile) / "Music")
        if lower in {"videos", "video", "videos folder", "video folder"}:
            return str(Path(user_profile) / "Videos")

        # Keep shell: monikers intact (critical for Downloads/Documents)
        if p.lower().startswith("shell:"):
            return p
        return os.path.abspath(str(Path(p).expanduser()))

    def _open_explorer_process(self, target: Optional[str] = None) -> None:
        if target:
            subprocess.Popen(["explorer.exe", target])
        else:
            subprocess.Popen(["explorer.exe"])

    def _ui_not_available(self, feature: str) -> Dict[str, Any]:
        detail = "pywinauto not installed" if not PYWINAUTO_AVAILABLE else "UI automation not wired"
        return {"success": False, "error": f"{feature} requires UI automation ({detail})"}

    # --------------------------
    # Core operations
    # --------------------------
    def open_explorer(self, path: str | None = None) -> Dict[str, Any]:
        try:
            target = self._normalize_path(path) if path else None
            self._open_explorer_process(target)
            time.sleep(0.25)
            return {"success": True, "path": target or "This PC", "action": "explorer.open"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def navigate_to(self, path: str) -> Dict[str, Any]:
        # Use explorer.exe navigation for reliability
        return self.open_explorer(path)

    def close_explorer(self) -> Dict[str, Any]:
        # Without UI automation, we can't reliably close the right window.
        return self._ui_not_available("close_explorer")

    # --------------------------
    # Creation / selection / clipboard (UI)
    # --------------------------
    def create_folder(self, name: str, path: str | None = None) -> Dict[str, Any]:
        # Prefer direct filesystem when path is provided.
        if path:
            try:
                base = self._normalize_path(path)
                target = Path(base) / name
                try:
                    target.mkdir(parents=True, exist_ok=True)
                    return {"success": True, "folder": str(target), "action": "explorer.create_folder"}
                except PermissionError as e:
                    # Common case: trying to create directly under C:\Users can be blocked.
                    base_norm = os.path.normcase(os.path.abspath(base))
                    if base_norm.rstrip("\\/") == os.path.normcase(os.path.abspath(r"C:\Users")):
                        user_profile = os.environ.get("USERPROFILE") or str(Path.home())
                        fallback = Path(user_profile) / name
                        fallback.mkdir(parents=True, exist_ok=True)
                        return {
                            "success": True,
                            "folder": str(fallback),
                            "action": "explorer.create_folder",
                            "note": "Access denied creating directly under C:\\Users; created under your user profile instead.",
                            "requested": str(target),
                        }
                    raise e
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "create_folder requires 'path' (UI creation not enabled)"}

    def create_file(self, name: str, file_type: str = "txt", path: str | None = None) -> Dict[str, Any]:
        if not path:
            return {"success": False, "error": "create_file requires 'path'"}
        try:
            folder = Path(self._normalize_path(path))
            folder.mkdir(parents=True, exist_ok=True)
            suffix = file_type if file_type.startswith(".") else f".{file_type}"
            target = folder / f"{name}{suffix}"
            target.write_text("", encoding="utf-8")
            return {"success": True, "file": str(target), "action": "explorer.create_file"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def select_file(self, name: str) -> Dict[str, Any]:
        return self._ui_not_available("select_file")

    def select_files(self, names: List[str]) -> Dict[str, Any]:
        return self._ui_not_available("select_files")

    def select_all(self) -> Dict[str, Any]:
        return self._ui_not_available("select_all")

    def copy_selected(self) -> Dict[str, Any]:
        return self._ui_not_available("copy_selected")

    def cut_selected(self) -> Dict[str, Any]:
        return self._ui_not_available("cut_selected")

    def paste(self) -> Dict[str, Any]:
        return self._ui_not_available("paste")

    # --------------------------
    # File operations (direct)
    # --------------------------
    def rename(self, old_name: str, new_name: str) -> Dict[str, Any]:
        try:
            src = Path(self._normalize_path(old_name))
            dst = src.with_name(new_name)
            src.rename(dst)
            return {"success": True, "old_name": str(src), "new_name": str(dst), "action": "explorer.rename"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete(self, name: str | None = None, permanent: bool = False) -> Dict[str, Any]:
        if not name:
            return {"success": False, "error": "delete requires 'name' path"}
        return self.delete_file_direct(path=name, permanent=permanent)

    def open_file(self, name: str) -> Dict[str, Any]:
        try:
            os.startfile(self._normalize_path(name))  # type: ignore[attr-defined]
            return {"success": True, "file": name, "action": "explorer.open_file"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def show_properties(self, name: str | None = None) -> Dict[str, Any]:
        return self._ui_not_available("show_properties")

    # --------------------------
    # Navigation/history/view (UI)
    # --------------------------
    def go_back(self) -> Dict[str, Any]:
        return self._ui_not_available("go_back")

    def go_forward(self) -> Dict[str, Any]:
        return self._ui_not_available("go_forward")

    def go_up(self) -> Dict[str, Any]:
        return self._ui_not_available("go_up")

    def refresh(self) -> Dict[str, Any]:
        return self._ui_not_available("refresh")

    def set_view(self, mode: str) -> Dict[str, Any]:
        return self._ui_not_available("set_view")

    def toggle_preview_pane(self) -> Dict[str, Any]:
        return self._ui_not_available("toggle_preview_pane")

    def toggle_details_pane(self) -> Dict[str, Any]:
        return self._ui_not_available("toggle_details_pane")

    def search(self, query: str, path: str | None = None) -> Dict[str, Any]:
        # Best-effort: open the folder and let user see search box manually.
        try:
            if path:
                self.open_explorer(path)
            if PYWINAUTO_AVAILABLE and send_keys:
                # Ctrl+F focuses search box in Explorer
                send_keys("^f")
                time.sleep(0.1)
                send_keys(query)
                time.sleep(0.05)
                send_keys("{ENTER}")
            return {"success": True, "query": query, "path": path, "action": "explorer.search"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --------------------------
    # Common locations
    # --------------------------
    def go_to_quick_access(self) -> Dict[str, Any]:
        return self.navigate_to("shell:Quick Access")

    def go_to_this_pc(self) -> Dict[str, Any]:
        return self.navigate_to("shell:MyComputerFolder")

    def go_to_desktop(self) -> Dict[str, Any]:
        return self.navigate_to("shell:Desktop")

    def go_to_documents(self) -> Dict[str, Any]:
        return self.navigate_to("shell:Personal")

    def go_to_downloads(self) -> Dict[str, Any]:
        return self.navigate_to("shell:Downloads")

    def go_to_pictures(self) -> Dict[str, Any]:
        return self.navigate_to("shell:My Pictures")

    def go_to_music(self) -> Dict[str, Any]:
        return self.navigate_to("shell:My Music")

    def go_to_videos(self) -> Dict[str, Any]:
        return self.navigate_to("shell:My Video")

    def go_to_recycle_bin(self) -> Dict[str, Any]:
        return self.navigate_to("shell:RecycleBinFolder")

    # --------------------------
    # Utility actions
    # --------------------------
    def copy_path(self, name: str | None = None) -> Dict[str, Any]:
        # Without UI selection, require explicit path.
        if not name:
            return {"success": False, "error": "copy_path requires 'name' path"}
        try:
            from ..executors.clipboard_exec import ClipboardExecutor, ClipboardConfig  # local import

            clip = ClipboardExecutor(ClipboardConfig())
            clip.copy_text(self._normalize_path(name))
            return {"success": True, "path": name, "action": "explorer.copy_path"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_in_terminal(self, path: str | None = None) -> Dict[str, Any]:
        try:
            target = self._normalize_path(path) if path else os.path.expanduser("~")
            # Prefer Windows Terminal if available
            subprocess.Popen(["wt", "-d", target])
            return {"success": True, "path": target, "action": "explorer.open_terminal"}
        except Exception as e:
            # Fallback to cmd
            try:
                target = self._normalize_path(path) if path else os.path.expanduser("~")
                subprocess.Popen(["cmd.exe", "/c", "start", "cmd.exe", "/k", f"cd /d \"{target}\""])
                return {"success": True, "path": target, "action": "explorer.open_terminal"}
            except Exception as e2:
                return {"success": False, "error": f"{e}; fallback failed: {e2}"}

    def undo(self) -> Dict[str, Any]:
        return self._ui_not_available("undo")

    def redo(self) -> Dict[str, Any]:
        return self._ui_not_available("redo")

    # --------------------------
    # Direct filesystem operations (used by actions.py)
    # --------------------------
    def list_contents(self, path: str) -> Dict[str, Any]:
        try:
            p = Path(self._normalize_path(path))
            if not p.exists():
                return {"success": False, "error": f"Path does not exist: {path}"}
            if not p.is_dir():
                return {"success": False, "error": f"Path is not a directory: {path}"}
            items: List[Dict[str, Any]] = []
            for item in p.iterdir():
                entry: Dict[str, Any] = {"name": item.name, "type": "folder" if item.is_dir() else "file"}
                try:
                    stat = item.stat()
                    entry["modified"] = stat.st_mtime
                    if item.is_file():
                        entry["size"] = stat.st_size
                        entry["extension"] = item.suffix
                except Exception:
                    pass
                items.append(entry)
            return {"success": True, "path": str(p), "items": items, "count": len(items), "action": "explorer.list"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_file_info(self, path: str) -> Dict[str, Any]:
        try:
            p = Path(self._normalize_path(path))
            if not p.exists():
                return {"success": False, "error": f"Path does not exist: {path}"}
            stat = p.stat()
            info: Dict[str, Any] = {
                "name": p.name,
                "path": str(p.resolve()),
                "type": "folder" if p.is_dir() else "file",
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime,
            }
            if p.is_file():
                info["extension"] = p.suffix
            return {"success": True, "info": info, "action": "explorer.file_info"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_folder_direct(self, path: str) -> Dict[str, Any]:
        try:
            p = Path(self._normalize_path(path))
            p.mkdir(parents=True, exist_ok=True)
            return {"success": True, "path": str(p), "action": "explorer.create_folder_direct"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def move_file(self, source: str, destination: str) -> Dict[str, Any]:
        try:
            import shutil

            src = Path(self._normalize_path(source))
            dst = Path(self._normalize_path(destination))
            if not src.exists():
                return {"success": False, "error": f"Source does not exist: {source}"}
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return {"success": True, "source": str(src), "destination": str(dst), "action": "explorer.move"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def copy_file(self, source: str, destination: str) -> Dict[str, Any]:
        try:
            import shutil

            src = Path(self._normalize_path(source))
            dst = Path(self._normalize_path(destination))
            if not src.exists():
                return {"success": False, "error": f"Source does not exist: {source}"}
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
            else:
                shutil.copy2(str(src), str(dst))
            return {"success": True, "source": str(src), "destination": str(dst), "action": "explorer.copy_file"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_file_direct(self, path: str, permanent: bool = False) -> Dict[str, Any]:
        try:
            import shutil

            tgt = Path(self._normalize_path(path))
            if not tgt.exists():
                return {"success": False, "error": f"Path does not exist: {path}"}

            if permanent:
                if tgt.is_dir():
                    shutil.rmtree(str(tgt))
                else:
                    tgt.unlink()
                return {"success": True, "path": str(tgt), "permanent": True, "action": "explorer.delete_direct"}

            # Try recycle bin if available
            try:
                from send2trash import send2trash  # type: ignore

                send2trash(str(tgt))
                return {"success": True, "path": str(tgt), "permanent": False, "action": "explorer.delete_direct"}
            except Exception:
                # Fallback to permanent
                if tgt.is_dir():
                    shutil.rmtree(str(tgt))
                else:
                    tgt.unlink()
                return {
                    "success": True,
                    "path": str(tgt),
                    "permanent": True,
                    "note": "send2trash not available, permanently deleted",
                    "action": "explorer.delete_direct",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
