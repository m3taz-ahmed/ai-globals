"""Tests for hybrid search with alpha-blended fusion (Pattern 3).

Covers ``hybrid_search``, ``fuse_rrf``, ``fuse_relative_score``, and
related helpers in ``runtime/semantic_search.py``.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from runtime.codegraph import FunctionNode
from runtime.semantic_search import (
    SearchResult,
    SemanticCodeSearch,
    _classify_source,
    _normalize_keyword_scores,
    _normalize_vector_scores,
    fuse_relative_score,
    fuse_rrf,
    hybrid_search,
    set_hybrid_backends,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_func(name: str = "test_func") -> FunctionNode:
    return FunctionNode(
        name=name,
        file_path="test.py",
        line=1,
        end_line=5,
        args=[],
    )


def _make_result(name: str, score: float) -> SearchResult:
    return SearchResult(function=_make_func(name), score=score, snippet="")


# ---------------------------------------------------------------------------
# _normalize_keyword_scores
# ---------------------------------------------------------------------------


class TestNormalizeKeywordScores:
    def test_empty(self) -> None:
        assert _normalize_keyword_scores([]) == {}

    def test_single_result(self) -> None:
        results = [_make_result("foo", 5.0)]
        norm = _normalize_keyword_scores(results)
        assert norm == {"foo": 1.0}

    def test_multiple_results(self) -> None:
        results = [_make_result("a", 1.0), _make_result("b", 3.0), _make_result("c", 5.0)]
        norm = _normalize_keyword_scores(results)
        assert norm["a"] == 0.0
        assert norm["b"] == 0.5
        assert norm["c"] == 1.0

    def test_all_same_scores(self) -> None:
        results = [_make_result("a", 2.0), _make_result("b", 2.0)]
        norm = _normalize_keyword_scores(results)
        assert norm["a"] == 1.0
        assert norm["b"] == 1.0


# ---------------------------------------------------------------------------
# _normalize_vector_scores
# ---------------------------------------------------------------------------


class TestNormalizeVectorScores:
    def test_empty(self) -> None:
        assert _normalize_vector_scores([]) == {}

    def test_single_result(self) -> None:
        norm = _normalize_vector_scores([("foo", 0.8)])
        assert norm == {"foo": 1.0}

    def test_multiple_results(self) -> None:
        norm = _normalize_vector_scores([("a", 0.2), ("b", 0.6), ("c", 1.0)])
        assert norm["a"] == pytest.approx(0.0)
        assert norm["b"] == pytest.approx(0.5)
        assert norm["c"] == pytest.approx(1.0)

    def test_negative_scores_clamped(self) -> None:
        norm = _normalize_vector_scores([("a", -0.5), ("b", 0.5)])
        assert norm["a"] == 0.0
        assert norm["b"] == 1.0


# ---------------------------------------------------------------------------
# _classify_source
# ---------------------------------------------------------------------------


class TestClassifySource:
    def test_keyword_only(self) -> None:
        result = _classify_source("foo", {"foo": 0.5}, {"bar": 0.8})
        assert result == "keyword"

    def test_vector_only(self) -> None:
        result = _classify_source("foo", {"bar": 0.5}, {"foo": 0.8})
        assert result == "vector"

    def test_hybrid(self) -> None:
        result = _classify_source("foo", {"foo": 0.5}, {"foo": 0.8})
        assert result == "hybrid"

    def test_neither(self) -> None:
        result = _classify_source("foo", {"bar": 0.5}, {"baz": 0.8})
        assert result == "keyword"


# ---------------------------------------------------------------------------
# fuse_rrf
# ---------------------------------------------------------------------------


class TestFuseRRF:
    def test_empty_inputs(self) -> None:
        results = fuse_rrf([], [], 0.5, 10)
        assert results == []

    def test_keyword_only(self) -> None:
        kw = [_make_result("a", 1.0), _make_result("b", 0.5)]
        results = fuse_rrf(kw, [], 0.0, 10)
        names = [r.function.name for r in results]
        assert "a" in names
        assert "b" in names

    def test_vector_only(self) -> None:
        kw = [_make_result("a", 1.0)]
        vec = [("a", 0.9), ("b", 0.8)]
        results = fuse_rrf(kw, vec, 1.0, 10)
        names = [r.function.name for r in results]
        assert "a" in names

    def test_both_sources(self) -> None:
        kw = [_make_result("a", 1.0), _make_result("b", 0.5)]
        vec = [("a", 0.9), ("c", 0.8)]
        results = fuse_rrf(kw, vec, 0.5, 10)
        names = [r.function.name for r in results]
        assert "a" in names  # appears in both → higher RRF score

    def test_limit_applied(self) -> None:
        kw = [_make_result(f"f{i}", 1.0) for i in range(10)]
        vec = [(f"f{i}", 0.9) for i in range(10)]
        results = fuse_rrf(kw, vec, 0.5, 3)
        assert len(results) <= 3

    def test_hybrid_score_positive(self) -> None:
        kw = [_make_result("a", 1.0)]
        vec = [("a", 0.9)]
        results = fuse_rrf(kw, vec, 0.5, 10)
        assert all(r.hybrid_score > 0 for r in results)


# ---------------------------------------------------------------------------
# fuse_relative_score
# ---------------------------------------------------------------------------


class TestFuseRelativeScore:
    def test_empty_inputs(self) -> None:
        results = fuse_relative_score([], [], 0.5, 10)
        assert results == []

    def test_balanced_alpha(self) -> None:
        kw = [_make_result("a", 1.0), _make_result("b", 0.0)]
        vec = [("a", 1.0), ("b", 0.0)]
        results = fuse_relative_score(kw, vec, 0.5, 10)
        assert len(results) >= 1
        # "a" has both keyword and vector score = 1.0 → highest hybrid
        top = results[0]
        assert top.function.name == "a"
        assert top.hybrid_score == pytest.approx(1.0)

    def test_pure_keyword(self) -> None:
        kw = [_make_result("a", 1.0), _make_result("b", 0.5)]
        results = fuse_relative_score(kw, [], 0.0, 10)
        names = [r.function.name for r in results]
        assert "a" in names

    def test_pure_vector(self) -> None:
        kw = [_make_result("a", 1.0)]
        vec = [("a", 1.0), ("b", 0.5)]
        results = fuse_relative_score(kw, vec, 1.0, 10)
        names = [r.function.name for r in results]
        assert "a" in names

    def test_limit_applied(self) -> None:
        kw = [_make_result(f"f{i}", float(10 - i)) for i in range(10)]
        vec = [(f"f{i}", 0.9) for i in range(10)]
        results = fuse_relative_score(kw, vec, 0.5, 3)
        assert len(results) <= 3

    def test_source_classification(self) -> None:
        # Both "kw_only" and "vec_only" must be in keyword results so they
        # appear in the func_lookup (fuse only returns results for known funcs).
        kw = [_make_result("kw_only", 1.0), _make_result("vec_only", 0.0)]
        vec = [("vec_only", 1.0)]
        results = fuse_relative_score(kw, vec, 0.5, 10)
        sources = {r.function.name: r.source for r in results}
        assert sources.get("kw_only") == "keyword"
        assert sources.get("vec_only") == "vector"


# ---------------------------------------------------------------------------
# hybrid_search (integration with backends)
# ---------------------------------------------------------------------------


class TestHybridSearch:
    def teardown_method(self) -> None:
        """Reset backends after each test."""
        set_hybrid_backends(None, None)

    def test_pure_keyword_alpha_zero(self) -> None:
        mock_search = MagicMock(spec=SemanticCodeSearch)
        mock_search.search.return_value = [_make_result("a", 1.0)]
        mock_search._functions = []
        set_hybrid_backends(keyword_search=mock_search, vector_store=None)

        results = hybrid_search("test", alpha=0.0, limit=5)
        assert len(results) >= 1
        assert results[0].source == "keyword"
        assert results[0].keyword_score > 0

    def test_pure_vector_alpha_one(self) -> None:
        mock_search = MagicMock(spec=SemanticCodeSearch)
        mock_search.search.return_value = [_make_result("a", 1.0)]
        mock_search._functions = [_make_func("a")]
        mock_store = MagicMock()
        mock_store.search.return_value = [("a", 0.9)]
        set_hybrid_backends(keyword_search=mock_search, vector_store=mock_store)

        results = hybrid_search("test", query_vector=[0.1, 0.2], alpha=1.0, limit=5)
        assert len(results) >= 1
        assert results[0].source == "vector"
        assert results[0].vector_score > 0

    def test_balanced_hybrid(self) -> None:
        mock_search = MagicMock(spec=SemanticCodeSearch)
        mock_search.search.return_value = [_make_result("a", 2.0), _make_result("b", 1.0)]
        mock_search._functions = [_make_func("a"), _make_func("b")]
        mock_store = MagicMock()
        mock_store.search.return_value = [("a", 0.9), ("b", 0.5)]
        set_hybrid_backends(keyword_search=mock_search, vector_store=mock_store)

        results = hybrid_search("test", query_vector=[0.1], alpha=0.5, limit=5)
        assert len(results) >= 1
        # "a" should be top (high in both)
        assert results[0].function.name == "a"

    def test_no_vector_store(self) -> None:
        mock_search = MagicMock(spec=SemanticCodeSearch)
        mock_search.search.return_value = [_make_result("a", 1.0)]
        mock_search._functions = []
        set_hybrid_backends(keyword_search=mock_search, vector_store=None)

        results = hybrid_search("test", alpha=0.5, limit=5)
        # With no vector results, only keyword leg contributes
        assert all(r.keyword_score >= 0 for r in results)

    def test_no_query_vector(self) -> None:
        mock_search = MagicMock(spec=SemanticCodeSearch)
        mock_search.search.return_value = [_make_result("a", 1.0)]
        mock_search._functions = []
        mock_store = MagicMock()
        mock_store.search.return_value = []
        set_hybrid_backends(keyword_search=mock_search, vector_store=mock_store)

        results = hybrid_search("test", query_vector=None, alpha=0.5, limit=5)
        # Vector leg returns empty, only keyword contributes
        assert all(r.keyword_score >= 0 for r in results)

    def test_over_fetch_factor(self) -> None:
        """hybrid_search should over-fetch by 3x for better fusion."""
        mock_search = MagicMock(spec=SemanticCodeSearch)
        mock_search.search.return_value = []
        mock_search._functions = []
        mock_store = MagicMock()
        mock_store.search.return_value = []
        set_hybrid_backends(keyword_search=mock_search, vector_store=mock_store)

        hybrid_search("test", query_vector=[0.1], alpha=0.5, limit=5)
        # Verify over-fetch: limit=5 → over_fetch=15
        mock_search.search.assert_called_once_with("test", limit=15)
        mock_store.search.assert_called_once()
