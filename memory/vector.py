#!/usr/bin/env python3
"""Optional vector memory backed by turbovec and sentence-transformers."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

import config

logger = logging.getLogger(__name__)

SentenceTransformer: Any = None
IdMapIndex: Any = None

try:
    from sentence_transformers import SentenceTransformer as _SentenceTransformer
    SentenceTransformer = _SentenceTransformer
except ImportError:  # pragma: no cover
    pass

try:
    from turbovec import IdMapIndex as _IdMapIndex
    IdMapIndex = _IdMapIndex
except ImportError:  # pragma: no cover
    pass


def _mem_id_to_uint64(mem_id: str) -> int:
    try:
        return int(uuid.UUID(mem_id).hex[:16], 16)
    except Exception:
        return hash(mem_id) % (2**64)


class Embedder:
    """Local embedder with optional sentence-transformers.

    Uses a module-level singleton to avoid re-loading the SentenceTransformer
    model on every instantiation (saves ~3s per test).
    """

    _singleton: Any = None
    _singleton_model_name: str | None = None

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model: Any = None
        if SentenceTransformer is not None:
            # Reuse the singleton if the model name matches
            if Embedder._singleton is not None and Embedder._singleton_model_name == model_name:
                self.model = Embedder._singleton
            else:
                self.model = SentenceTransformer(model_name)
                Embedder._singleton = self.model
                Embedder._singleton_model_name = model_name
        self.dim = 384

    def embed(self, texts: Sequence[str]) -> np.ndarray[Any, np.dtype[Any]]:
        if self.model is not None:
            return np.asarray(self.model.encode(list(texts)), dtype=np.float32)
        raise RuntimeError("SentenceTransformer model is not available.")

    def is_available(self) -> bool:
        return self.model is not None

    @classmethod
    def _reset_singleton(cls) -> None:
        """Reset the model singleton. Useful for tests."""
        cls._singleton = None
        cls._singleton_model_name = None


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
        self.add_batch([mem_id], [text])

    def add_batch(self, mem_ids: list[str], texts: list[str]) -> None:
        """Add a batch of memories and persist the index once."""
        if not self.is_available() or not mem_ids:
            return
        try:
            vector = self.embedder.embed(texts)
        except RuntimeError as exc:
            logger.warning("Vector embed failed for batch: %s", exc)
            return
        u64s = np.array([_mem_id_to_uint64(mid) for mid in mem_ids], dtype=np.uint64)
        for u64, mid in zip(u64s, mem_ids, strict=True):
            self.id_map[str(u64)] = mid
        self.index.add_with_ids(vector, u64s)
        self.index.write(str(self.index_path))
        self._save_map()

    def search(self, text: str, k: int = 5, ids: list[str] | None = None) -> list[dict[str, Any]]:
        """Search the vector index, optionally restricted to the given ids."""
        if not self.is_available():
            return []
        try:
            vector = self.embedder.embed([text])
        except RuntimeError as exc:
            logger.warning("Vector embed failed for query: %s", exc)
            return []
        allowlist = None
        if ids is not None:
            if not ids:
                return []
            u64s = [_mem_id_to_uint64(mid) for mid in ids]
            present = [u for u in u64s if str(int(u)) in self.id_map]
            if not present:
                return []
            allowlist = np.array(present, dtype=np.uint64)
        scores, ids_arr = self.index.search(vector, k=k, allowlist=allowlist)
        results = []
        # Turbovec may return fewer than k results (e.g., empty index → shape (1,0))
        n_results = ids_arr.shape[1] if ids_arr.ndim >= 2 else 0
        for i in range(min(k, n_results)):
            u64 = str(int(ids_arr[0, i]))
            real_id = self.id_map.get(u64)
            if real_id is None:
                continue
            results.append({"id": real_id, "score": float(scores[0, i])})
        return results

    def remove(self, mem_id: str) -> None:
        self.remove_batch([mem_id])

    def remove_batch(self, mem_ids: list[str]) -> None:
        """Remove a batch of memories and persist the index once."""
        if not self.is_available() or not mem_ids:
            return
        u64s = np.array([_mem_id_to_uint64(mid) for mid in mem_ids], dtype=np.uint64)
        for u64 in u64s:
            self.id_map.pop(str(u64), None)
            self.index.remove(int(u64))
        self.index.write(str(self.index_path))
        self._save_map()
