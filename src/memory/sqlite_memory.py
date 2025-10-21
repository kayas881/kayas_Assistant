from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class MemoryConfig:
    db_path: Path


class SQLiteMemory:
    def __init__(self, cfg: MemoryConfig):
        self.cfg = cfg
        self.cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.cfg.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    role TEXT,
                    content TEXT,
                    ts TEXT
                );
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    name TEXT,
                    params_json TEXT,
                    result_json TEXT,
                    ts TEXT
                );
                """
            )
            # Store planning prompts/outputs for training datasets
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    model TEXT,
                    kind TEXT, -- 'structured' | 'legacy' | 'heuristic'
                    prompt TEXT,
                    output TEXT,
                    ts TEXT
                );
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    feedback TEXT,
                    tags TEXT,
                    ts TEXT
                );
                """
            )
            conn.commit()

    def log_message(self, run_id: str, role: str, content: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages (run_id, role, content, ts) VALUES (?, ?, ?, ?)",
                (run_id, role, content, datetime.utcnow().isoformat()),
            )
            conn.commit()

    def log_plan(self, run_id: str, model: str, kind: str, prompt: str, output: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO plans (run_id, model, kind, prompt, output, ts) VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, model, kind, prompt, output, datetime.utcnow().isoformat()),
            )
            conn.commit()

    def log_feedback(self, run_id: str, feedback: str, tags: Optional[str] = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO feedback (run_id, feedback, tags, ts) VALUES (?, ?, ?, ?)",
                (run_id, feedback, tags or "", datetime.utcnow().isoformat()),
            )
            conn.commit()

    def log_action(
        self,
        run_id: str,
        name: str,
        params: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO actions (run_id, name, params_json, result_json, ts) VALUES (?, ?, ?, ?, ?)",
                (
                    run_id,
                    name,
                    json.dumps(params, ensure_ascii=False),
                    json.dumps(result or {}, ensure_ascii=False),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
