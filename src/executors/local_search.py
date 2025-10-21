from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class LocalSearchConfig:
    root: Path
    max_files: int = 1000
    max_hits: int = 100


class LocalSearchExecutor:
    def __init__(self, cfg: LocalSearchConfig) -> None:
        self.cfg = cfg

    def search(self, query: str) -> Dict:
        query_l = query.lower()
        results: List[Dict] = []
        for dirpath, _, filenames in os.walk(self.cfg.root):
            for name in filenames:
                path = Path(dirpath) / name
                rel = str(path)
                if query_l in name.lower() or fnmatch.fnmatch(name.lower(), f"*{query_l}*"):
                    results.append({"path": rel, "match": "filename"})
                # lightweight content search for text files
                try:
                    if len(results) >= self.cfg.max_hits:
                        break
                    with path.open("r", encoding="utf-8", errors="ignore") as f:
                        text = f.read(50000)  # limit
                        if query_l in text.lower():
                            results.append({"path": rel, "match": "content"})
                except Exception:
                    pass
            if len(results) >= self.cfg.max_hits:
                break
        return {"query": query, "results": results[: self.cfg.max_hits]}
