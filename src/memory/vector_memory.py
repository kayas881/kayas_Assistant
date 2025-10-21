from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from ..agent.config import ollama_url
import os


@dataclass
class VectorMemoryConfig:
    persist_dir: Path
    embed_model: str


class VectorMemory:
    def __init__(self, cfg: VectorMemoryConfig) -> None:
        # Best-effort: suppress chroma telemetry noisy errors in local runs
        os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
        os.environ.setdefault("POSTHOG_DISABLED", "1")
        os.environ.setdefault("DO_NOT_TRACK", "1")
        cfg.persist_dir.mkdir(parents=True, exist_ok=True)
        # Using Ollama embedding function wrapper
        self.embed = embedding_functions.OllamaEmbeddingFunction(
            model_name=cfg.embed_model, url=ollama_url()
        )
        self.client = chromadb.PersistentClient(
            path=str(cfg.persist_dir), settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="agent_memory",
            metadata={"hnsw:space": "cosine"},
            embedding_function=self.embed,
        )

    def add(
        self, texts: List[str], metadatas: Optional[List[Dict]] = None, ids: Optional[List[str]] = None
    ) -> None:
        try:
            metadatas = metadatas or [{} for _ in texts]
            ids = ids or [str(i) for i in range(len(texts))]
            self.collection.add(documents=texts, metadatas=metadatas, ids=ids)
        except Exception:
            # Swallow embedding/store errors to avoid breaking the agent loop
            pass

    def query(self, text: str, k: int = 5) -> List[Dict]:
        try:
            res = self.collection.query(query_texts=[text], n_results=k)
        except Exception:
            return []
        out: List[Dict] = []
        ids_list = res.get("ids", [[]])[0]
        for i in range(len(ids_list)):
            out.append(
                {
                    "id": res["ids"][0][i],
                    "document": res["documents"][0][i],
                    "distance": res.get("distances", [[None]])[0][i] if res.get("distances") else None,
                    "metadata": res["metadatas"][0][i],
                }
            )
        return out
