"""Tests for the hybrid memory search layer."""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from memory.hybrid import (
    HybridSearcher,
    _normalize_bm25_score,
    _normalize_semantic_score,
    extract_entities,
)
from memory.store import Memory, MemoryStore


def _tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="aios_hybrid_"))


def _store(tmp: Path) -> MemoryStore:
    return MemoryStore(tmp, tmp / "memory.db", enable_vector=False)


def _mem(kind: str = "factual", content: str = "test", source: str = "") -> Memory:
    now = datetime.now(timezone.utc).isoformat()
    return Memory(
        id=str(uuid.uuid4()),
        kind=kind,
        content=content,
        source=source,
        meta=json.dumps({}),
        created_at=now,
        valid_from=now,
        valid_to=None,
    )


class TestExtractEntities:
    def test_extract_quoted(self):
        assert "hello" in extract_entities('the "hello world" phrase')
        assert "world" in extract_entities('the "hello world" phrase')

    def test_extract_capitalized_phrase(self):
        entities = extract_entities("query about aiZee")
        assert "aizee" in entities

    def test_extract_mixed_identifier(self):
        assert "get_repo_map" in extract_entities("call get_repo_map")
        assert "camelcasevalue" in extract_entities("CamelCaseValue")

    def test_extract_no_duplicates(self):
        assert extract_entities("get_repo_map get_repo_map") == ["get_repo_map"]


class TestNormalizeSemanticScore:
    def test_similarity_in_range_used_as_is(self):
        assert _normalize_semantic_score(0.95) == pytest.approx(0.95)

    def test_negative_similarity_shifted(self):
        assert _normalize_semantic_score(-0.5) == pytest.approx(0.25, abs=0.01)

    def test_distance_converted(self):
        assert _normalize_semantic_score(2.0) == pytest.approx(1 / 3, abs=0.01)

    def test_none_returns_zero(self):
        assert _normalize_semantic_score(None) == 0.0


class TestNormalizeBm25Score:
    def test_best_one(self):
        assert _normalize_bm25_score(-0.5, -0.5, 0.0) == pytest.approx(1.0)

    def test_worst_one(self):
        assert _normalize_bm25_score(0.0, -0.5, 0.0) == pytest.approx(0.0)

    def test_midpoint(self):
        assert _normalize_bm25_score(-0.25, -0.5, 0.0) == pytest.approx(0.5)

    def test_none_zero(self):
        assert _normalize_bm25_score(None, 0.0, 0.0) == 0.0

    def test_single_value(self):
        assert _normalize_bm25_score(-1.0, -1.0, -1.0) == 1.0


class TestHybridSearch:
    def test_hybrid_search_returns_results(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            store.add("factual", "hello world", source="s1")
            mock_vector = MagicMock()
            mock_vector.is_available.return_value = True
            mock_vector.search.return_value = []
            store.vector = mock_vector
            results = store.search_hybrid("hello", k=5)
            assert len(results) == 1
            assert results[0]["content"] == "hello world"
            assert "score" in results[0]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_hybrid_entity_boost_orders_matching_higher(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            m1 = store.add("factual", "Use get_repo_map to fetch repository", source="s1")
            m2 = store.add("factual", "General discussion about tools", source="s2")
            mock_vector = MagicMock()
            mock_vector.is_available.return_value = True
            mock_vector.search.return_value = [
                {"id": m1.id, "score": 0.9},
                {"id": m2.id, "score": 0.9},
            ]
            store.vector = mock_vector
            results = store.search_hybrid("get_repo_map function", k=2)
            assert results[0]["id"] == m1.id
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_hybrid_explain_includes_score_details(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            store.add("factual", "hello world", source="s1")
            mock_vector = MagicMock()
            mock_vector.is_available.return_value = True
            mock_vector.search.return_value = []
            store.vector = mock_vector
            results = store.search_hybrid("hello", k=5, explain=True)
            assert results[0]["score_details"]
            assert set(results[0]["score_details"].keys()) == {"semantic", "bm25", "entity", "final"}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_hybrid_fallback_when_vector_unavailable(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            m = store.add("factual", "fallback memory", source="s1")
            assert store.vector is None
            results = store.search_hybrid("fallback", k=5)
            assert len(results) == 1
            assert results[0]["id"] == m.id
            assert results[0]["score"] is None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_hybrid_search_with_source_filter(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            store.add("factual", "only in source one", source="src1")
            store.add("factual", "only in source two", source="src2")
            mock_vector = MagicMock()
            mock_vector.is_available.return_value = True
            mock_vector.search.return_value = []
            store.vector = mock_vector
            results = store.search_hybrid("source", k=5, source="src1")
            assert all(r["source"] == "src1" for r in results)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_hybrid_search_with_kind_filter(self):
        """Lines 178-179: _run_fts_score_query appends kind condition."""
        tmp = _tmp()
        try:
            store = _store(tmp)
            store.add("factual", "hello world", source="s1")
            store.add("semantic", "hello earth", source="s2")
            mock_vector = MagicMock()
            mock_vector.is_available.return_value = True
            mock_vector.search.return_value = []
            store.vector = mock_vector
            results = store.search_hybrid("hello", k=5, kind="factual")
            assert all(r["kind"] == "factual" for r in results)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_collect_candidates_updates_existing_with_semantic(self):
        """Lines 115-116: vector result for an existing FTS candidate updates semantic score."""
        tmp = _tmp()
        try:
            store = _store(tmp)
            m = store.add("factual", "hello world", source="s1")
            mock_vector = MagicMock()
            mock_vector.is_available.return_value = True
            mock_vector.search.return_value = [{"id": m.id, "score": 0.95}]
            store.vector = mock_vector
            searcher = HybridSearcher(store)
            candidates = searcher._collect_candidates("hello", 5, None, None)
            assert m.id in candidates
            assert candidates[m.id]["semantic"] == 0.95
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# _mem helper (covers test file lines 32-33)
# ---------------------------------------------------------------------------

class TestMemHelper:
    def test_mem_creates_valid_memory(self):
        """Exercise the _mem helper to cover its body (lines 32-33)."""
        m = _mem(kind="factual", content="test content", source="test_source")
        assert m.kind == "factual"
        assert m.content == "test content"
        assert m.source == "test_source"
        assert m.id
        assert m.valid_to is None
        assert m.created_at  # timestamp was set


# ---------------------------------------------------------------------------
# HybridSearcher â€” edge cases
# ---------------------------------------------------------------------------

class TestHybridSearcherEdgeCases:
    def test_search_k_zero_returns_empty(self):
        """Line 91: search with k<=0 returns empty list."""
        store = MagicMock()
        searcher = HybridSearcher(store)
        assert searcher.search("query", k=0) == []

    def test_search_negative_k_returns_empty(self):
        """Line 91: search with negative k returns empty list."""
        store = MagicMock()
        searcher = HybridSearcher(store)
        assert searcher.search("query", k=-1) == []

    def test_collect_candidates_skips_missing_mid(self):
        """Line 119: vector result whose get() returns None is skipped."""
        store = MagicMock()
        store.search.return_value = []
        store.search_vector.return_value = [{"id": "missing-id", "score": 0.9}]
        store.get.return_value = None
        searcher = HybridSearcher(store)
        candidates = searcher._collect_candidates("query", 5, None, None)
        assert candidates == {}

    def test_apply_bm25_empty_query_skips(self):
        """Line 133: _apply_bm25 returns early when FTS query is empty ('""')."""
        store = MagicMock()
        store._fts_query.return_value = '""'
        searcher = HybridSearcher(store)
        mem = _mem(content="hello")
        candidates = {"id1": {"memory": mem, "bm25": None, "semantic": None}}
        searcher._apply_bm25(candidates, "", 5, None, None)
        # bm25 should remain None since we returned early
        assert candidates["id1"]["bm25"] is None

    def test_bm25_rows_fallback_on_operational_error(self):
        """Lines 153-154: _bm25_rows falls back to 'rank' when bm25() raises OperationalError."""
        tmp = _tmp()
        try:
            store = _store(tmp)
            store.add("factual", "hello world", source="s1")
            searcher = HybridSearcher(store)
            original_method = searcher._run_fts_score_query
            call_count = [0]

            def patched(conn, q_fts, now, kind, source, limit, score_col, order_col):
                call_count[0] += 1
                if score_col == "bm25(memories_fts)":
                    raise sqlite3.OperationalError("bm25 not available")
                return original_method(conn, q_fts, now, kind, source, limit, score_col, order_col)

            searcher._run_fts_score_query = patched
            rows = searcher._bm25_rows('"hello"', 5, None, None)
            assert call_count[0] == 2
            assert len(rows) >= 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_run_fts_score_query_rejects_bad_score_col(self):
        """Line 172: disallowed score_col raises ValueError."""
        store = MagicMock()
        searcher = HybridSearcher(store)
        with pytest.raises(ValueError, match="Disallowed score column"):
            searcher._run_fts_score_query(
                MagicMock(), '"query"', "now", None, None, 5, "bad_col", "rank"
            )

    def test_run_fts_score_query_rejects_bad_order_col(self):
        """Line 174: disallowed order_col raises ValueError."""
        store = MagicMock()
        searcher = HybridSearcher(store)
        with pytest.raises(ValueError, match="Disallowed order column"):
            searcher._run_fts_score_query(
                MagicMock(), '"query"', "now", None, None, 5, "rank", "bad_col"
            )
