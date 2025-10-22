"""
File watcher executor for monitoring file system changes.
"""
from __future__ import annotations

import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from typing import Dict, Any, Callable, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
import threading


@dataclass
class WatcherConfig:
    recursive: bool = True
    ignore_patterns: List[str] = field(default_factory=lambda: ["*.tmp", "*.swp", "__pycache__"])
    debounce_ms: int = 100


class FileWatcherExecutor:
    def __init__(self, cfg: WatcherConfig | None = None):
        self.cfg = cfg or WatcherConfig()
        self.observers: Dict[str, Observer] = {}
        self.handlers: Dict[str, 'CustomEventHandler'] = {}
        self.event_log: List[Dict[str, Any]] = []

    def watch_directory(self, path: str, watch_id: str | None = None,
                       on_created: Callable | None = None,
                       on_modified: Callable | None = None,
                       on_deleted: Callable | None = None,
                       on_moved: Callable | None = None) -> Dict[str, Any]:
        """Start watching a directory for changes."""
        try:
            path = Path(path).resolve()
            
            if not path.exists():
                return {
                    "action": "filewatcher.watch",
                    "success": False,
                    "error": f"Path does not exist: {path}"
                }
            
            watch_id = watch_id or f"watch_{len(self.observers)}"
            
            # Create handler
            handler = CustomEventHandler(
                executor=self,
                on_created=on_created,
                on_modified=on_modified,
                on_deleted=on_deleted,
                on_moved=on_moved,
                ignore_patterns=self.cfg.ignore_patterns
            )
            
            # Create observer
            observer = Observer()
            observer.schedule(handler, str(path), recursive=self.cfg.recursive)
            observer.start()
            
            self.observers[watch_id] = observer
            self.handlers[watch_id] = handler
            
            return {
                "action": "filewatcher.watch",
                "success": True,
                "watch_id": watch_id,
                "path": str(path),
                "recursive": self.cfg.recursive
            }
        except Exception as e:
            return {
                "action": "filewatcher.watch",
                "success": False,
                "error": str(e)
            }

    def stop_watching(self, watch_id: str) -> Dict[str, Any]:
        """Stop watching a directory."""
        try:
            if watch_id not in self.observers:
                return {
                    "action": "filewatcher.stop",
                    "success": False,
                    "error": f"Watch ID not found: {watch_id}"
                }
            
            observer = self.observers[watch_id]
            observer.stop()
            observer.join(timeout=5)
            
            del self.observers[watch_id]
            del self.handlers[watch_id]
            
            return {
                "action": "filewatcher.stop",
                "success": True,
                "watch_id": watch_id
            }
        except Exception as e:
            return {
                "action": "filewatcher.stop",
                "success": False,
                "error": str(e)
            }

    def get_active_watches(self) -> Dict[str, Any]:
        """Get list of active watches."""
        try:
            watches = []
            for watch_id, observer in self.observers.items():
                watches.append({
                    "watch_id": watch_id,
                    "is_alive": observer.is_alive()
                })
            
            return {
                "action": "filewatcher.active",
                "success": True,
                "count": len(watches),
                "watches": watches
            }
        except Exception as e:
            return {
                "action": "filewatcher.active",
                "success": False,
                "error": str(e)
            }

    def get_event_log(self, watch_id: str | None = None, limit: int = 50) -> Dict[str, Any]:
        """Get recent file system events."""
        try:
            if watch_id:
                events = [e for e in self.event_log if e.get("watch_id") == watch_id]
            else:
                events = self.event_log
            
            return {
                "action": "filewatcher.events",
                "success": True,
                "count": len(events),
                "events": events[-limit:]
            }
        except Exception as e:
            return {
                "action": "filewatcher.events",
                "success": False,
                "error": str(e)
            }

    def clear_event_log(self) -> Dict[str, Any]:
        """Clear the event log."""
        try:
            self.event_log.clear()
            
            return {
                "action": "filewatcher.clear_log",
                "success": True
            }
        except Exception as e:
            return {
                "action": "filewatcher.clear_log",
                "success": False,
                "error": str(e)
            }

    def _log_event(self, event_type: str, src_path: str, dest_path: str | None = None,
                   watch_id: str | None = None) -> None:
        """Log a file system event."""
        import time
        
        entry = {
            "type": event_type,
            "src_path": src_path,
            "timestamp": time.time(),
            "watch_id": watch_id
        }
        
        if dest_path:
            entry["dest_path"] = dest_path
        
        self.event_log.append(entry)
        
        # Keep log size reasonable
        if len(self.event_log) > 1000:
            self.event_log = self.event_log[-500:]


class CustomEventHandler(FileSystemEventHandler):
    """Custom event handler for file system events."""
    
    def __init__(self, executor: FileWatcherExecutor,
                 on_created: Callable | None = None,
                 on_modified: Callable | None = None,
                 on_deleted: Callable | None = None,
                 on_moved: Callable | None = None,
                 ignore_patterns: List[str] | None = None):
        super().__init__()
        self.executor = executor
        self.on_created = on_created
        self.on_modified = on_modified
        self.on_deleted = on_deleted
        self.on_moved = on_moved
        self.ignore_patterns = ignore_patterns or []
        self.last_event_time: Dict[str, float] = {}

    def _should_ignore(self, path: str) -> bool:
        """Check if path matches ignore patterns."""
        from fnmatch import fnmatch
        
        for pattern in self.ignore_patterns:
            if fnmatch(path, pattern):
                return True
        return False

    def _debounce(self, event_key: str) -> bool:
        """Check if event should be debounced."""
        now = time.time()
        last_time = self.last_event_time.get(event_key, 0)
        
        if now - last_time < self.executor.cfg.debounce_ms / 1000:
            return True
        
        self.last_event_time[event_key] = now
        return False

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory or self._should_ignore(event.src_path):
            return
        
        event_key = f"created:{event.src_path}"
        if self._debounce(event_key):
            return
        
        self.executor._log_event("created", event.src_path)
        
        if self.on_created:
            threading.Thread(target=self.on_created, args=(event.src_path,)).start()

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory or self._should_ignore(event.src_path):
            return
        
        event_key = f"modified:{event.src_path}"
        if self._debounce(event_key):
            return
        
        self.executor._log_event("modified", event.src_path)
        
        if self.on_modified:
            threading.Thread(target=self.on_modified, args=(event.src_path,)).start()

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory or self._should_ignore(event.src_path):
            return
        
        self.executor._log_event("deleted", event.src_path)
        
        if self.on_deleted:
            threading.Thread(target=self.on_deleted, args=(event.src_path,)).start()

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory or self._should_ignore(event.src_path):
            return
        
        dest_path = getattr(event, 'dest_path', None)
        self.executor._log_event("moved", event.src_path, dest_path)
        
        if self.on_moved:
            threading.Thread(target=self.on_moved, args=(event.src_path, dest_path)).start()
