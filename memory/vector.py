#!/usr/bin/env python3
"""Optional vector memory backed by turbovec and sentence-transformers."""

from __future__ import annotations

import json
import logging
import math
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False

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


# ---------------------------------------------------------------------------
# VectorStore — standalone in-memory vector store with hybrid-search support
# (Pattern from Weaviate/Qdrant: brute-force below threshold, indexed above,
#  filter-during-traversal for metadata constraints.)
# ---------------------------------------------------------------------------


class VectorStore:
    """In-memory vector store with brute-force and indexed search.

    Uses brute-force cosine similarity for small datasets (below
    ``full_scan_threshold``) and delegates to an indexed search for
    larger ones. Metadata filtering follows Qdrant's
    filter-during-traversal pattern: conditions are applied *during*
    scoring so filtered-out vectors never enter the top-k.

    Numpy is used when available; a pure-Python fallback is used
    otherwise so the store remains functional without the dependency.
    """

    def __init__(self, dim: int = 384, full_scan_threshold: int = 1000) -> None:
        self._dim = dim
        self._full_scan_threshold = full_scan_threshold
        self._vectors: list[list[float]] = []
        self._ids: list[str] = []
        self._metadata: list[dict[str, Any]] = []
        self._index: Any = None  # placeholder for an HNSW-like index

    def __len__(self) -> int:
        return len(self._vectors)

    @property
    def full_scan_threshold(self) -> int:
        return self._full_scan_threshold

    def add(
        self, id: str, vector: list[float], metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a vector with an associated id and optional metadata."""
        self._vectors.append(list(vector))
        self._ids.append(id)
        self._metadata.append(metadata or {})

    def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        """Search for the top-k most similar vectors.

        Returns a list of ``(id, score)`` tuples sorted by descending
        cosine similarity. When the dataset is smaller than
        ``full_scan_threshold`` a brute-force scan is used; otherwise
        the indexed search path is taken.
        """
        if not self._vectors:
            return []
        if len(self._vectors) < self._full_scan_threshold:
            raw = self._brute_force_search(query_vector, limit, filter_metadata)
        else:
            raw = self._indexed_search(query_vector, limit, filter_metadata)
        return [(self._ids[i], score) for i, score in raw]

    # -- brute-force path -------------------------------------------------

    def _brute_force_search(
        self,
        query_vector: list[float],
        limit: int,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[tuple[int, float]]:
        """Brute-force cosine similarity over all stored vectors."""
        if not self._vectors:
            return []
        if _HAS_NUMPY:
            return self._numpy_brute_force(query_vector, limit, filter_metadata)
        return self._pure_python_brute_force(query_vector, limit, filter_metadata)

    def _numpy_brute_force(
        self,
        query_vector: list[float],
        limit: int,
        filter_metadata: dict[str, Any] | None,
    ) -> list[tuple[int, float]]:
        """Numpy-accelerated brute-force search."""
        assert np is not None
        query = np.array(query_vector, dtype=np.float32)
        vectors = np.array(self._vectors, dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1)
        query_norm = np.linalg.norm(query)
        denom = norms * query_norm + 1e-8
        scores = (vectors @ query) / denom
        if filter_metadata:
            mask = self._apply_metadata_filter(filter_metadata)
            scores = scores * mask
        top_indices = np.argsort(scores)[-limit:][::-1]
        return [(int(i), float(scores[i])) for i in top_indices if scores[i] > 0]

    def _pure_python_brute_force(
        self,
        query_vector: list[float],
        limit: int,
        filter_metadata: dict[str, Any] | None,
    ) -> list[tuple[int, float]]:
        """Pure-Python fallback when numpy is unavailable."""
        scored: list[tuple[int, float]] = []
        for i, vec in enumerate(self._vectors):
            score = self._cosine_python(query_vector, vec)
            if filter_metadata and not self._matches_metadata(
                self._metadata[i], filter_metadata,
            ):
                score = 0.0
            if score > 0:
                scored.append((i, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    @staticmethod
    def _cosine_python(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    # -- indexed path (mock HNSW) ----------------------------------------

    def _indexed_search(
        self,
        query_vector: list[float],
        limit: int,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[tuple[int, float]]:
        """Indexed search path for large datasets.

        The default implementation falls back to brute-force. Subclasses
        or tests can override this to plug in a real HNSW (or mock) index.
        """
        return self._brute_force_search(query_vector, limit, filter_metadata)

    # -- metadata filtering ----------------------------------------------

    def _apply_metadata_filter(
        self, filter_metadata: dict[str, Any],
    ) -> Any:
        """Build a numpy mask array for filter-during-traversal.

        Returns a float32 array where ``1.0`` indicates the vector
        matches all filter conditions and ``0.0`` indicates it should
        be excluded. Multiplying scores by this mask removes
        non-matching vectors during scoring rather than after top-k
        selection (Qdrant's filter-during-traversal pattern).
        """
        assert np is not None
        mask = np.ones(len(self._vectors), dtype=np.float32)
        for i, meta in enumerate(self._metadata):
            if not self._matches_metadata(meta, filter_metadata):
                mask[i] = 0.0
        return mask

    @staticmethod
    def _matches_metadata(
        meta: dict[str, Any], conditions: dict[str, Any],
    ) -> bool:
        """Check whether *meta* satisfies all *conditions*.

        Supports equality (``{"key": value}``) and operator dicts:
        ``$eq``, ``$ne``, ``$gte``, ``$lte``, ``$gt``, ``$lt``, ``$in``.
        """
        for key, value in conditions.items():
            if key not in meta:
                return False
            field_val = meta[key]
            if isinstance(value, dict):
                if not VectorStore._check_operators(field_val, value):
                    return False
            elif field_val != value:
                return False
        return True

    @staticmethod
    def _check_operators(field_val: Any, ops: dict[str, Any]) -> bool:
        """Evaluate operator-style conditions against a field value."""
        for op, operand in ops.items():
            if op == "$eq" and field_val != operand:
                return False
            if op == "$ne" and field_val == operand:
                return False
            if op == "$gte" and not (field_val >= operand):
                return False
            if op == "$lte" and not (field_val <= operand):
                return False
            if op == "$gt" and not (field_val > operand):
                return False
            if op == "$lt" and not (field_val < operand):
                return False
            if op == "$in" and field_val not in operand:
                return False
        return True
