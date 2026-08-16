"""Tests for memory/consolidation.py — consolidation primitives."""

from __future__ import annotations

from memory.consolidation import ConsolidationEngine


class TestConsolidationEngine:
    def test_dedupe_finds_near_duplicates(self) -> None:
        engine = ConsolidationEngine(similarity_threshold=10)
        entries = [
            {"id": "1", "content": "The quick brown fox jumps over the lazy dog today"},
            {"id": "2", "content": "The quick brown fox jumps over the lazy dog now"},
            {"id": "3", "content": "A completely different fact about quantum physics"},
        ]
        report = engine.dedupe_entities(entries, dry_run=True)
        assert report.examined == 3
        assert report.merged_count >= 1

    def test_dedupe_dry_run_doesnt_modify(self) -> None:
        engine = ConsolidationEngine()
        entries = [{"id": "1", "content": "test"}, {"id": "2", "content": "test"}]
        report = engine.dedupe_entities(entries, dry_run=True)
        assert all(d["action"] == "would_merge" for d in report.details if d.get("action"))

    def test_summarize_long_traces(self) -> None:
        engine = ConsolidationEngine()
        entries = [
            {"id": "1", "content": "short"},
            {"id": "2", "content": "x" * 6000},
        ]
        report = engine.summarize_long_traces(entries, max_length=5000, dry_run=True)
        assert report.summarized_count == 1

    def test_detect_superseded_facts(self) -> None:
        engine = ConsolidationEngine()
        entries = [
            {"id": "1", "content": "active fact"},
            {"id": "2", "content": "old fact", "valid_to": "2024-01-01"},
            {"id": "3", "content": "replaced", "superseded_by": "new-id"},
        ]
        report = engine.detect_superseded_facts(entries, dry_run=True)
        assert report.superseded_count == 2

    def test_empty_entries(self) -> None:
        engine = ConsolidationEngine()
        report = engine.dedupe_entities([], dry_run=True)
        assert report.examined == 0
        assert report.merged_count == 0
