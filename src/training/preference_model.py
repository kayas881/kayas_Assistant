from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import sqlite3

from ..agent.config import db_path, preference_model_path


@dataclass
class PrefConfig:
    db_file: Path
    model_file: Path
    max_vocab: int = 5000
    epochs: int = 5
    lr: float = 0.1


def _tokenize(text: str) -> List[str]:
    text = (text or "").lower()
    # lightweight tokenization
    return re.findall(r"[a-z0-9_./:+-]+", text)


def _extract_features(prompt: str, completion: str) -> Dict[str, float]:
    toks = _tokenize(prompt) + _tokenize(completion)
    feats: Dict[str, float] = {}
    for t in toks:
        feats[f"tok:{t}"] = feats.get(f"tok:{t}", 0.0) + 1.0
    # structural features
    feats["len_prompt"] = len(prompt)
    feats["len_completion"] = len(completion)
    feats["num_braces"] = completion.count("{") + completion.count("}")
    feats["num_brackets"] = completion.count("[") + completion.count("]")
    feats["is_json_like"] = 1.0 if completion.strip().startswith("[") or completion.strip().startswith("{") else 0.0
    feats["num_steps"] = completion.count("\n")
    return feats


def _sigmoid(x: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


class PreferenceModel:
    def __init__(self, weights: Dict[str, float] | None = None, vocab: List[str] | None = None):
        self.weights = weights or {}
        self.vocab = vocab or []

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"weights": self.weights, "vocab": self.vocab}, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def load(path: Path) -> "PreferenceModel":
        if not path.exists():
            return PreferenceModel()
        data = json.loads(path.read_text(encoding="utf-8"))
        return PreferenceModel(weights=data.get("weights", {}), vocab=data.get("vocab", []))

    def score(self, prompt: str, completion: str) -> float:
        feats = _extract_features(prompt, completion)
        z = 0.0
        for k, v in feats.items():
            if self.vocab and k not in self.vocab:
                continue
            z += self.weights.get(k, 0.0) * v
        return _sigmoid(z)

    def _fit_sgd(self, items: List[Tuple[str, str, int]], epochs: int, lr: float, max_vocab: int) -> None:
        # Build vocab by frequency across features
        counts: Dict[str, int] = {}
        feat_cache: List[Tuple[Dict[str, float], int]] = []
        for p, c, y in items:
            feats = _extract_features(p, c)
            for k in feats.keys():
                counts[k] = counts.get(k, 0) + 1
            feat_cache.append((feats, y))
        # prune vocab
        self.vocab = [k for k, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:max_vocab]]
        # SGD
        for _ in range(epochs):
            for feats, y in feat_cache:
                # compute prediction
                z = 0.0
                for k, v in feats.items():
                    if k not in self.vocab:
                        continue
                    z += self.weights.get(k, 0.0) * v
                p_hat = _sigmoid(z)
                # gradient for logistic loss
                grad = (p_hat - (1 if y > 0 else 0))
                for k, v in feats.items():
                    if k not in self.vocab:
                        continue
                    self.weights[k] = self.weights.get(k, 0.0) - lr * grad * v


def _load_training_rows(db: Path) -> List[Tuple[str, str, int]]:
    rows: List[Tuple[str, str, int]] = []
    with sqlite3.connect(db) as conn:
        c = conn.cursor()
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
            SELECT lp.prompt, lp.output, IFNULL(fb.tags, '') AS tags, IFNULL(fb.feedback, '') AS feedback
            FROM latest_plans lp
            LEFT JOIN fb ON fb.run_id = lp.run_id
            ORDER BY lp.id DESC;
            """
        )
        for (prompt, output, tags, feedback) in c.fetchall():
            t = (tags or '').lower()
            f = (feedback or '').lower()
            neg = any(w in t or w in f for w in ["neg", "bad", "wrong", "worse", "-1", "reject", "not good"])
            pos = any(w in t or w in f for w in ["pos", "good", "great", "+1", "accept", "helpful", "correct"])
            label = 0
            if neg and not pos:
                label = -1
            elif pos and not neg:
                label = +1
            rows.append((prompt or "", output or "", label))
    return rows


def train_preference_model(cfg: PrefConfig | None = None) -> PreferenceModel:
    cfg = cfg or PrefConfig(db_file=db_path(), model_file=preference_model_path())
    data = _load_training_rows(cfg.db_file)
    # Keep examples with labels; neutral are useful but we focus on polarized feedback
    labeled = [row for row in data if row[2] != 0]
    if not labeled:
        # Fallback to all rows as neutral (won't update much)
        labeled = data
    model = PreferenceModel()
    model._fit_sgd(labeled, epochs=cfg.epochs, lr=cfg.lr, max_vocab=cfg.max_vocab)
    model.save(cfg.model_file)
    return model


def score_plan(prompt: str, completion: str, model_path: Path | None = None) -> float:
    mp = model_path or preference_model_path()
    model = PreferenceModel.load(mp)
    return model.score(prompt, completion)
