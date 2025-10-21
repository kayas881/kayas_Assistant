from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Iterable, Dict, Any


@dataclass
class ExportConfig:
    db_path: Path
    out_path: Path


class DatasetExporter:
    """
    Build a JSONL training dataset for plan fine-tuning.
    Each row contains: {prompt, completion, label}
    - prompt: the planning prompt used (structured or legacy)
    - completion: the planner output (JSON or steps text)
    - label: +1 (good) | -1 (bad) from feedback tags or sentiment keywords
    We heuristically map feedback rows onto most recent plan for that run.
    """

    def __init__(self, cfg: ExportConfig):
        self.cfg = cfg

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.cfg.db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    model TEXT,
                    kind TEXT,
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

    def _fetch_rows(self) -> Iterable[Dict[str, Any]]:
        with self._connect() as conn:
            c = conn.cursor()
            # Join latest plan per run with aggregated feedback sentiment
            c.execute(
                """
                WITH latest_plans AS (
                    SELECT p.* FROM plans p
                    JOIN (
                        SELECT run_id, MAX(id) AS max_id FROM plans GROUP BY run_id
                    ) t ON p.id = t.max_id
                ),
                fb AS (
                    SELECT run_id,
                           GROUP_CONCAT(tags, ';') AS tags,
                           GROUP_CONCAT(feedback, '\n') AS feedback
                    FROM feedback GROUP BY run_id
                )
                SELECT lp.run_id, lp.kind, lp.prompt, lp.output, IFNULL(fb.tags, ''), IFNULL(fb.feedback, '')
                FROM latest_plans lp
                LEFT JOIN fb ON fb.run_id = lp.run_id
                ORDER BY lp.id DESC;
                """
            )
            cols = [d[0] for d in c.description]
            for row in c.fetchall():
                yield {k: v for k, v in zip(cols, row)}

    @staticmethod
    def _score(tags: str, feedback: str) -> int:
        t = (tags or '').lower()
        f = (feedback or '').lower()
        neg = any(w in t or w in f for w in ["neg", "bad", "wrong", "worse", "-1", "reject", "not good"])
        pos = any(w in t or w in f for w in ["pos", "good", "great", "+1", "accept", "helpful", "correct"])
        if neg and not pos:
            return -1
        if pos and not neg:
            return +1
        # neutral/unknown
        return 0

    def export(self) -> Path:
        # Ensure tables exist
        self._ensure_schema()
        self.cfg.out_path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with self.cfg.out_path.open("w", encoding="utf-8") as f:
            for row in self._fetch_rows():
                label = self._score(row.get('tags', ''), row.get('feedback', ''))
                data = {
                    "prompt": row.get("prompt", ""),
                    "completion": row.get("output", ""),
                    "label": label,
                    "run_id": row.get("run_id"),
                    "kind": row.get("kind"),
                }
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
                count += 1
        return self.cfg.out_path
