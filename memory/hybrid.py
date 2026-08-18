"""Hybrid memory scoring layer combining FTS5, vector, and entity boosting."""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .store import MemoryStore

_ENTITY_WEIGHT = 0.5
_MAX_POSSIBLE = 2.0 + _ENTITY_WEIGHT
_FTS_LIMIT = 50


def extract_entities(text: str) -> list[str]:
    """Extract quoted strings, capitalized phrases, and mixed identifiers."""
    results: set[str] = set()
    for quoted in re.findall(r'"([^"]*)"|\'([^\']*)\'', text):
        fragment = quoted[0] or quoted[1]
        for token in fragment.split():
            if token:
                results.add(token.lower())
    for phrase in re.findall(r'\b[A-Z][a-zA-Z0-9_]*(?:\s+[A-Z][a-zA-Z0-9_]*)+\b', text):
        for token in phrase.split():
            if token:
                results.add(token.lower())
    for token in re.findall(r'\b[A-Z]{2,}\d*\b', text):
        results.add(token.lower())
    patterns = (
        r'\b[a-z]+(?:_[a-z0-9]+)+\b',
        r'\b[a-z]+(?:[A-Z][a-z0-9]*)+\b',
        r'\b[A-Z][a-z]+(?:[A-Z][a-z0-9]*)+\b',
        r'\b[a-zA-Z_]+\d+[a-zA-Z0-9_]*\b',
    )
    for pattern in patterns:
        for token in re.findall(pattern, text):
            results.add(token.lower())
    return sorted(results)


def _normalize_semantic_score(score: float | None) -> float:
    """Convert a vector score to [0, 1]."""
    if score is None:
        return 0.0
    if score < 0:
        return max(0.0, (score + 1.0) / 2.0)
    if score <= 1.0:
        return score
    return 1.0 / (1.0 + score)


def _normalize_bm25_score(score: float | None, min_s: float, max_s: float) -> float:
    """Normalize an FTS5 bm25/rank score to [0, 1] (lower raw is better)."""
    if score is None:
        return 0.0
    if max_s == min_s:
        return 1.0
    return (max_s - score) / (max_s - min_s)


class HybridSearcher:
    """Combine FTS5 keyword search, vector semantic search, and entity boosting."""

    # Whitelist of allowed FTS5 score/order expressions to prevent SQL injection
    # via dynamic column interpolation. Only these exact strings are permitted.
    _ALLOWED_SCORE_COLS: frozenset[str] = frozenset({
        "bm25(memories_fts)",
        "rank",
    })
    _ALLOWED_ORDER_COLS: frozenset[str] = frozenset({
        "bm25(memories_fts)",
        "rank",
    })

    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory_store = memory_store

    def search(
        self,
        query: str,
        k: int = 5,
        kind: str | None = None,
        source: str | None = None,
        explain: bool = False,
    ) -> list[dict[str, Any]]:
        """Return top-k memories with a hybrid [0, 1] score."""
        if k <= 0:
            return []
        entities = set(extract_entities(query))
        candidates = self._collect_candidates(query, k, kind, source)
        self._apply_bm25(candidates, query, k, kind, source)
        results = self._score_candidates(candidates, entities, explain)
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:k]

    def _collect_candidates(
        self,
        query: str,
        k: int,
        kind: str | None,
        source: str | None,
    ) -> dict[str, dict[str, Any]]:
        candidates: dict[str, dict[str, Any]] = {}
        limit = max(k, _FTS_LIMIT)
        for mem in self.memory_store.search(query, kind=kind, limit=limit):
            if source and mem.source != source:
                continue
            candidates[mem.id] = {"memory": mem, "bm25": None, "semantic": None}
        for vr in self.memory_store.search_vector(query, k=limit, kind=kind, source=source):
            mid = vr["id"]
            if mid in candidates:
                candidates[mid]["semantic"] = vr["score"]
                continue
            found = self.memory_store.get(mid)
            if found is None:
                continue
            candidates[mid] = {"memory": found, "bm25": None, "semantic": vr["score"]}
        return candidates

    def _apply_bm25(
        self,
        candidates: dict[str, dict[str, Any]],
        query: str,
        k: int,
        kind: str | None,
        source: str | None,
    ) -> None:
        q_fts = self.memory_store._fts_query(query)
        if q_fts == '""':
            return
        for row in self._bm25_rows(q_fts, max(k, _FTS_LIMIT), kind, source):
            mid = row["id"]
            if mid in candidates:
                candidates[mid]["bm25"] = row["score"]

    def _bm25_rows(
        self,
        q_fts: str,
        limit: int,
        kind: str | None,
        source: str | None,
    ) -> list[sqlite3.Row]:
        now = datetime.now(UTC).isoformat()
        with self.memory_store._conn() as conn:
            try:
                return self._run_fts_score_query(
                    conn, q_fts, now, kind, source, limit, "bm25(memories_fts)",
                    "bm25(memories_fts)"
                )
            except sqlite3.OperationalError:
                return self._run_fts_score_query(
                    conn, q_fts, now, kind, source, limit, "rank", "rank"
                )

    def _run_fts_score_query(
        self,
        conn: sqlite3.Connection,
        q_fts: str,
        now: str,
        kind: str | None,
        source: str | None,
        limit: int,
        score_col: str,
        order_col: str,
    ) -> list[sqlite3.Row]:
        # Defense-in-depth: validate score_col/order_col against whitelist
        # to prevent SQL injection via dynamic column interpolation.
        if score_col not in self._ALLOWED_SCORE_COLS:
            raise ValueError(f"Disallowed score column: {score_col!r}")
        if order_col not in self._ALLOWED_ORDER_COLS:
            raise ValueError(f"Disallowed order column: {order_col!r}")
        conditions = ["memories_fts MATCH ?", "(m.valid_to IS NULL OR m.valid_to > ?)"]
        params: list[Any] = [q_fts, now]
        if kind:
            conditions.append("m.kind = ?")
            params.append(kind)
        if source:
            conditions.append("m.source = ?")
            params.append(source)
        where = " AND ".join(conditions)
        sql = (
            f"SELECT m.id, m.rowid, {score_col} as score FROM memories m "
            f"JOIN memories_fts fts ON m.rowid = fts.rowid "
            f"WHERE {where} ORDER BY {order_col} LIMIT ?"
        )
        params.append(limit)
        return conn.execute(sql, params).fetchall()

    def _score_candidates(
        self,
        candidates: dict[str, dict[str, Any]],
        entities: set[str],
        explain: bool,
    ) -> list[dict[str, Any]]:
        counts = self._entity_counts(candidates, entities)
        max_entity = max(counts.values()) if counts else 0
        bm25_values = [c["bm25"] for c in candidates.values() if c["bm25"] is not None]
        min_bm25 = min(bm25_values) if bm25_values else 0.0
        max_bm25 = max(bm25_values) if bm25_values else 0.0
        results: list[dict[str, Any]] = []
        for mid, cand in candidates.items():
            semantic = _normalize_semantic_score(cand["semantic"])
            bm25 = _normalize_bm25_score(cand["bm25"], min_bm25, max_bm25)
            entity = (counts[mid] * _ENTITY_WEIGHT / max_entity) if max_entity else 0.0
            final = (semantic + bm25 + entity) / _MAX_POSSIBLE
            mem = cand["memory"]
            r: dict[str, Any] = {
                "id": mem.id,
                "kind": mem.kind,
                "source": mem.source,
                "content": mem.content,
                "score": final,
            }
            if explain:
                r["score_details"] = {
                    "semantic": semantic,
                    "bm25": bm25,
                    "entity": entity,
                    "final": final,
                }
            results.append(r)
        return results

    def _entity_counts(
        self,
        candidates: dict[str, dict[str, Any]],
        entities: set[str],
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for mid, cand in candidates.items():
            content = cand["memory"].content.lower()
            counts[mid] = sum(1 for e in entities if e in content)
        return counts
