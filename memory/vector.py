#!/usr/bin/env python3
"""Optional vector memory backed by turbovec and sentence-transformers."""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

import config

SentenceTransformer: Any = None
IdMapIndex: Any = None

try:
    from sentence_transformers import SentenceTransformer as _SentenceTransformer
    SentenceTransformer = _SentenceTransformer
except ImportError:
    pass

try:
    from turbovec import IdMapIndex as _IdMapIndex
    IdMapIndex = _IdMapIndex
except ImportError:
    pass


def _mem_id_to_uint64(mem_id: str) -> int:
    try:
        return int(uuid.UUID(mem_id).hex[:16], 16)
    except Exception:
        return hash(mem_id) % (2**64)


class Embedder:
    """Local embedder with optional sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model: Any = None
        if SentenceTransformer is not None:
            self.model = SentenceTransformer(model_name)
        self.dim = 384

    def embed(self, texts: Sequence[str]) -> np.ndarray[Any, np.dtype[Any]]:
        if self.model is not None:
            return np.asarray(self.model.encode(list(texts)), dtype=np.float32)
        raise RuntimeError("SentenceTransformer model is not available.")

    def is_available(self) -> bool:
        return self.model is not None


class VectorMemory:
    """Vector memory index stored as `brain/vector_memory.tvim`."""

    def __init__(self, root: Path | None = None, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.root = root or config.discover_root()
        self.db_dir = self.root / "brain"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.db_dir / "vector_memory.tvim"
        self.map_path = self.db_dir / "vector_id_map.json"
        self.embedder = Embedder(model_name)
        self.dim = self.embedder.dim
        self.index: Any = None
        self.id_map: dict[str, str] = {}
        if IdMapIndex is not None:
            self._load_or_create()

    def _load_or_create(self) -> None:
        if self.index_path.exists():
            self.index = IdMapIndex.load(str(self.index_path))
        else:
            self.index = IdMapIndex(dim=self.dim, bit_width=4)
        if self.map_path.exists():
            with self.map_path.open("r", encoding="utf-8") as f:
                self.id_map = json.load(f)

    def _save_map(self) -> None:
        with self.map_path.open("w", encoding="utf-8") as f:
            json.dump(self.id_map, f)

    def is_available(self) -> bool:
        return IdMapIndex is not None and self.index is not None

    def add(self, mem_id: str, text: str) -> None:
        if not self.is_available():
            return
        try:
            vector = self.embedder.embed([text])
        except RuntimeError:
            return
        u64 = _mem_id_to_uint64(mem_id)
        self.id_map[str(u64)] = mem_id
        ids = np.array([u64], dtype=np.uint64)
        self.index.add_with_ids(vector, ids)
        self.index.write(str(self.index_path))
        self._save_map()

    def search(self, text: str, k: int = 5) -> list[dict[str, Any]]:
        if not self.is_available():
            return []
        try:
            vector = self.embedder.embed([text])
        except RuntimeError:
            return []
        scores, ids = self.index.search(vector, k=k)
        results = []
        for i in range(k):
            u64 = str(int(ids[0, i]))
            real_id = self.id_map.get(u64, u64)
            results.append({"id": real_id, "score": float(scores[0, i])})
        return results

    def remove(self, mem_id: str) -> None:
        if not self.is_available():
            return
        u64 = _mem_id_to_uint64(mem_id)
        self.id_map.pop(str(u64), None)
        self.index.remove(np.array([u64], dtype=np.uint64))
        self.index.write(str(self.index_path))
        self._save_map()
