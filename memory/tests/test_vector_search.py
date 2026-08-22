"""Tests for the VectorStore with full_scan_threshold and metadata filtering.

Covers Pattern 3 (Qdrant-style filter-during-traversal + brute-force/
indexed search selection) from ``memory/vector.py``.
"""

from __future__ import annotations

import pytest

from memory.vector import VectorStore

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestVectorStoreConstruction:
    def test_default_dim(self) -> None:
        store = VectorStore()
        assert store._dim == 384

    def test_custom_dim(self) -> None:
        store = VectorStore(dim=128)
        assert store._dim == 128

    def test_default_full_scan_threshold(self) -> None:
        store = VectorStore()
        assert store.full_scan_threshold == 1000

    def test_custom_full_scan_threshold(self) -> None:
        store = VectorStore(full_scan_threshold=100)
        assert store.full_scan_threshold == 100

    def test_empty_store_len(self) -> None:
        store = VectorStore()
        assert len(store) == 0


# ---------------------------------------------------------------------------
# add + search
# ---------------------------------------------------------------------------


class TestVectorStoreAddSearch:
    def test_add_increments_len(self) -> None:
        store = VectorStore(dim=3)
        store.add("v1", [1.0, 0.0, 0.0])
        assert len(store) == 1

    def test_add_with_metadata(self) -> None:
        store = VectorStore(dim=3)
        store.add("v1", [1.0, 0.0, 0.0], {"type": "doc"})
        assert store._metadata[0] == {"type": "doc"}

    def test_add_without_metadata_defaults_empty(self) -> None:
        store = VectorStore(dim=3)
        store.add("v1", [1.0, 0.0, 0.0])
        assert store._metadata[0] == {}

    def test_search_empty_store(self) -> None:
        store = VectorStore(dim=3)
        results = store.search([1.0, 0.0, 0.0])
        assert results == []

    def test_search_returns_id_score_tuples(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0])
        store.add("b", [0.0, 1.0, 0.0])
        results = store.search([1.0, 0.0, 0.0], limit=2)
        assert len(results) >= 1
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)

    def test_search_finds_most_similar(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0])
        store.add("b", [0.0, 1.0, 0.0])
        store.add("c", [0.9, 0.1, 0.0])
        results = store.search([1.0, 0.0, 0.0], limit=1)
        assert results[0][0] == "a"
        assert results[0][1] > 0.9

    def test_search_sorted_by_descending_score(self) -> None:
        store = VectorStore(dim=3)
        store.add("low", [0.5, 0.5, 0.0])
        store.add("high", [1.0, 0.0, 0.0])
        store.add("mid", [0.8, 0.2, 0.0])
        results = store.search([1.0, 0.0, 0.0], limit=3)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_limit(self) -> None:
        store = VectorStore(dim=3)
        for i in range(10):
            store.add(f"v{i}", [float(i) / 10, 0.0, 0.0])
        results = store.search([1.0, 0.0, 0.0], limit=3)
        assert len(results) <= 3


# ---------------------------------------------------------------------------
# full_scan_threshold behavior
# ---------------------------------------------------------------------------


class TestFullScanThreshold:
    def test_below_threshold_uses_brute_force(self) -> None:
        store = VectorStore(dim=3, full_scan_threshold=100)
        store.add("a", [1.0, 0.0, 0.0])
        # With 1 vector < 100 threshold, brute force is used
        results = store.search([1.0, 0.0, 0.0])
        assert len(results) == 1
        assert results[0][0] == "a"

    def test_at_threshold_uses_indexed(self) -> None:
        """When count >= threshold, indexed path is taken (falls back to brute)."""
        store = VectorStore(dim=2, full_scan_threshold=5)
        for i in range(5):
            store.add(f"v{i}", [float(i), 0.0])
        results = store.search([1.0, 0.0], limit=3)
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# Metadata filtering
# ---------------------------------------------------------------------------


class TestMetadataFiltering:
    def test_equality_filter(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0], {"type": "doc"})
        store.add("b", [1.0, 0.0, 0.0], {"type": "code"})
        results = store.search([1.0, 0.0, 0.0], limit=10, filter_metadata={"type": "doc"})
        ids = [r[0] for r in results]
        assert "a" in ids
        assert "b" not in ids

    def test_filter_no_matches(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0], {"type": "doc"})
        results = store.search([1.0, 0.0, 0.0], limit=10, filter_metadata={"type": "nonexistent"})
        assert results == []

    def test_filter_missing_key(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0], {"type": "doc"})
        results = store.search([1.0, 0.0, 0.0], limit=10, filter_metadata={"missing": "x"})
        assert results == []

    def test_ne_operator(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0], {"category": "x"})
        store.add("b", [1.0, 0.0, 0.0], {"category": "y"})
        results = store.search([1.0, 0.0, 0.0], limit=10, filter_metadata={"category": {"$ne": "x"}})
        ids = [r[0] for r in results]
        assert "b" in ids
        assert "a" not in ids

    def test_gte_operator(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0], {"score": 5})
        store.add("b", [1.0, 0.0, 0.0], {"score": 10})
        results = store.search([1.0, 0.0, 0.0], limit=10, filter_metadata={"score": {"$gte": 8}})
        ids = [r[0] for r in results]
        assert "b" in ids
        assert "a" not in ids

    def test_lte_operator(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0], {"score": 5})
        store.add("b", [1.0, 0.0, 0.0], {"score": 10})
        results = store.search([1.0, 0.0, 0.0], limit=10, filter_metadata={"score": {"$lte": 5}})
        ids = [r[0] for r in results]
        assert "a" in ids
        assert "b" not in ids

    def test_gt_operator(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0], {"score": 5})
        store.add("b", [1.0, 0.0, 0.0], {"score": 10})
        results = store.search([1.0, 0.0, 0.0], limit=10, filter_metadata={"score": {"$gt": 5}})
        ids = [r[0] for r in results]
        assert "b" in ids

    def test_lt_operator(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0], {"score": 5})
        store.add("b", [1.0, 0.0, 0.0], {"score": 10})
        results = store.search([1.0, 0.0, 0.0], limit=10, filter_metadata={"score": {"$lt": 10}})
        ids = [r[0] for r in results]
        assert "a" in ids

    def test_in_operator(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0], {"tag": "x"})
        store.add("b", [1.0, 0.0, 0.0], {"tag": "y"})
        store.add("c", [1.0, 0.0, 0.0], {"tag": "z"})
        results = store.search([1.0, 0.0, 0.0], limit=10, filter_metadata={"tag": {"$in": ["x", "y"]}})
        ids = {r[0] for r in results}
        assert ids == {"a", "b"}

    def test_multiple_conditions(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0], {"type": "doc", "lang": "en"})
        store.add("b", [1.0, 0.0, 0.0], {"type": "doc", "lang": "fr"})
        store.add("c", [1.0, 0.0, 0.0], {"type": "code", "lang": "en"})
        results = store.search([1.0, 0.0, 0.0], limit=10, filter_metadata={"type": "doc", "lang": "en"})
        ids = {r[0] for r in results}
        assert ids == {"a"}


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_zero_vector_query(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0])
        results = store.search([0.0, 0.0, 0.0])
        # Zero query vector → cosine similarity = 0 → no results
        assert results == []

    def test_zero_vector_stored(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [0.0, 0.0, 0.0])
        results = store.search([1.0, 0.0, 0.0])
        # Zero stored vector → cosine similarity = 0 → no results
        assert results == []

    def test_orthogonal_vectors(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0])
        results = store.search([0.0, 1.0, 0.0])
        # Orthogonal → cosine = 0 → no results
        assert results == []

    def test_identical_vectors(self) -> None:
        store = VectorStore(dim=3)
        store.add("a", [1.0, 0.0, 0.0])
        results = store.search([1.0, 0.0, 0.0])
        assert len(results) == 1
        assert results[0][1] == pytest.approx(1.0, rel=1e-5)
