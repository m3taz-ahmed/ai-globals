"""Tests for WS-F: Memory upgrades (W1-W6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.store import MemoryStore, _deterministic_id, _extract_facts


def _store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(root=tmp_path, enable_vector=False)


# ---------------------------------------------------------------------------
# WS-F W1: Deterministic IDs
# ---------------------------------------------------------------------------


class TestDeterministicIds:
    """Memory IDs are deterministic (content-hash based)."""

    def test_same_content_same_id(self) -> None:
        id1 = _deterministic_id("hello world", "semantic")
        id2 = _deterministic_id("hello world", "semantic")
        assert id1 == id2

    def test_different_content_different_id(self) -> None:
        id1 = _deterministic_id("hello world", "semantic")
        id2 = _deterministic_id("hello universe", "semantic")
        assert id1 != id2

    def test_different_kind_different_id(self) -> None:
        id1 = _deterministic_id("hello world", "semantic")
        id2 = _deterministic_id("hello world", "episodic")
        assert id1 != id2

    def test_id_format(self) -> None:
        id1 = _deterministic_id("content", "semantic")
        assert id1.startswith("mem_")
        assert len(id1) == 20  # "mem_" + 16 hex chars


# ---------------------------------------------------------------------------
# WS-F W2: Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    """Adding the same content twice returns the same memory."""

    def test_dedup_same_content(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        m1 = store.add("semantic", "The API uses REST", source="docs")
        m2 = store.add("semantic", "The API uses REST", source="docs")
        assert m1.id == m2.id
        assert store.count() == 1

    def test_no_dedup_different_source(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        m1 = store.add("semantic", "The API uses REST", source="docs")
        m2 = store.add("semantic", "The API uses REST", source="code")
        assert m1.id != m2.id
        assert store.count() == 2

    def test_no_dedup_different_kind(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        m1 = store.add("semantic", "The API uses REST")
        m2 = store.add("episodic", "The API uses REST")
        assert m1.id != m2.id


# ---------------------------------------------------------------------------
# WS-F W3: Fact extraction
# ---------------------------------------------------------------------------


class TestFactExtraction:
    """Facts are extracted from content and stored in metadata."""

    def test_extract_facts_basic(self) -> None:
        content = "The system uses PostgreSQL for storage. It is very fast. Hello."
        facts = _extract_facts(content)
        assert len(facts) >= 1
        assert any("PostgreSQL" in f for f in facts)

    def test_extract_facts_short_sentence_skipped(self) -> None:
        content = "It is. Very short."
        facts = _extract_facts(content)
        assert len(facts) == 0

    def test_facts_stored_in_metadata(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        import json

        m = store.add("semantic", "The system uses PostgreSQL for storage.")
        meta = json.loads(m.meta)
        assert "extracted_facts" in meta
        assert len(meta["extracted_facts"]) >= 1

    def test_no_facts_for_simple_content(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        import json

        m = store.add("episodic", "Hello world")
        meta = json.loads(m.meta)
        # Short content with no verbs → no facts
        assert "extracted_facts" not in meta or len(meta["extracted_facts"]) == 0


# ---------------------------------------------------------------------------
# WS-F W4: Temporal search
# ---------------------------------------------------------------------------


class TestTemporalSearch:
    """Search memories by temporal range."""

    def test_temporal_search_basic(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        m = store.add("semantic", "Test memory")
        # Search a wide range
        results = store.search_temporal("2000-01-01", "2100-01-01")
        assert len(results) >= 1
        assert any(r.id == m.id for r in results)

    def test_temporal_search_filtered_by_kind(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store.add("semantic", "Semantic memory")
        store.add("episodic", "Episodic memory")
        results = store.search_temporal("2000-01-01", "2100-01-01", kind="semantic")
        assert all(r.kind == "semantic" for r in results)

    def test_temporal_search_empty_range(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store.add("semantic", "Test memory")
        # Search a range in the past
        results = store.search_temporal("2000-01-01", "2001-01-01")
        assert len(results) == 0


# ---------------------------------------------------------------------------
# WS-F W5: Decay persistence
# ---------------------------------------------------------------------------


class TestDecayPersistence:
    """Decay scores are persisted and updated on access."""

    def test_initial_decay_score(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        m = store.add("semantic", "Test memory")
        score = store.get_decay_score(m.id)
        assert score == 1.0  # Default for untracked

    def test_record_access_increases_score(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        m = store.add("semantic", "Test memory")
        store.record_access(m.id)
        store.record_access(m.id)
        score = store.get_decay_score(m.id)
        assert score == 1.0  # Capped at 1.0

    def test_apply_decay_reduces_score(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        m = store.add("semantic", "Test memory")
        store.record_access(m.id)  # score = 1.0
        updated = store.apply_decay(decay_rate=0.5)
        assert updated == 1
        score = store.get_decay_score(m.id)
        assert score < 1.0
        assert score >= 0.0

    def test_decay_persists_across_sessions(self, tmp_path: Path) -> None:
        store1 = _store(tmp_path)
        m = store1.add("semantic", "Test memory")
        store1.record_access(m.id)
        store1.apply_decay(decay_rate=0.3)
        score1 = store1.get_decay_score(m.id)
        # Create a new store instance (simulates new session)
        store2 = MemoryStore(root=tmp_path, enable_vector=False)
        score2 = store2.get_decay_score(m.id)
        assert score1 == score2


# ---------------------------------------------------------------------------
# WS-F W6: Search hardening
# ---------------------------------------------------------------------------


class TestSearchHardening:
    """search_safe adds extra sanitization layers."""

    def test_long_query_truncated(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store.add("semantic", "hello world")
        # Very long query should not crash
        long_query = "hello " * 1000
        results = store.search_safe(long_query)
        assert isinstance(results, list)

    def test_null_bytes_removed(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store.add("semantic", "hello world")
        results = store.search_safe("hello\x00world")
        assert isinstance(results, list)

    def test_sql_keywords_stripped(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store.add("semantic", "hello world")
        # Should not crash or inject
        results = store.search_safe("DROP TABLE memories; hello")
        assert isinstance(results, list)

    def test_result_limit_enforced(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        for i in range(10):
            store.add("semantic", f"memory item {i}")
        # Request more than 100 — should be capped
        results = store.search_safe("memory", limit=200)
        assert len(results) <= 100


# ---------------------------------------------------------------------------
# Review fix: delete_by_source_batch length validation
# ---------------------------------------------------------------------------


class TestDeleteBySourceBatchValidation:
    """delete_by_source_batch validates input length (review fix)."""

    def test_oversized_source_rejected(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        oversized = "x" * 1001
        with pytest.raises(ValueError, match="Invalid source"):
            store.delete_by_source_batch([oversized])

    def test_empty_source_rejected(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        with pytest.raises(ValueError, match="Invalid source"):
            store.delete_by_source_batch([""])

    def test_non_string_source_rejected(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        with pytest.raises(ValueError, match="Invalid source"):
            store.delete_by_source_batch([123])  # type: ignore[list-item]

    def test_valid_short_source_accepted(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store.add("semantic", "test content", source="valid-source")
        # Should not raise
        deleted = store.delete_by_source_batch(["valid-source"])
        assert isinstance(deleted, list)
