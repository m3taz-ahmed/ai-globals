"""Tests for the hybrid memory search layer."""

from __future__ import annotations

import json
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from memory.hybrid import (
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
        entities = extract_entities("query about AI Global OS")
        assert "ai" in entities
        assert "global" in entities
        assert "os" in entities

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
