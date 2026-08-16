"""Tests for memory/temporal.py — temporal knowledge graph."""

from __future__ import annotations

from memory.temporal import TemporalFact, TemporalFactStore


class TestTemporalFactStore:
    def test_set_and_query_current(self) -> None:
        store = TemporalFactStore()
        store.set_fact("X", "ceo", "Alice", "2021-01-01")
        assert store.query_fact("X", "ceo") == "Alice"

    def test_query_at_specific_time(self) -> None:
        store = TemporalFactStore()
        store.set_fact("X", "ceo", "Alice", "2021-01-01")
        store.set_fact("X", "ceo", "Bob", "2024-04-10")
        assert store.query_fact("X", "ceo", at="2022-06-01") == "Alice"
        assert store.query_fact("X", "ceo", at="2024-07-01") == "Bob"

    def test_history_returns_all_versions(self) -> None:
        store = TemporalFactStore()
        store.set_fact("X", "status", "dev", "2024-01-01")
        store.set_fact("X", "status", "prod", "2024-06-01")
        history = store.history("X", "status")
        assert len(history) == 2

    def test_setting_new_fact_closes_old(self) -> None:
        store = TemporalFactStore()
        store.set_fact("X", "ceo", "Alice", "2021-01-01")
        store.set_fact("X", "ceo", "Bob", "2024-01-01")
        history = store.history("X", "ceo")
        assert history[0].valid_to is not None
        assert history[1].valid_to is None

    def test_query_nonexistent_returns_none(self) -> None:
        store = TemporalFactStore()
        assert store.query_fact("X", "nonexistent") is None

    def test_query_all_facts_filtered(self) -> None:
        store = TemporalFactStore()
        store.set_fact("X", "a", "1", "2024-01-01")
        store.set_fact("Y", "b", "2", "2024-01-01")
        results = store.query_all_facts(subject="X")
        assert len(results) == 1
        assert results[0].subject == "X"

    def test_fact_is_valid_at(self) -> None:
        fact = TemporalFact("X", "ceo", "Alice", "2021-01-01", "2024-01-01")
        assert fact.is_valid_at("2022-01-01") is True
        assert fact.is_valid_at("2020-01-01") is False
        assert fact.is_valid_at("2024-06-01") is False
