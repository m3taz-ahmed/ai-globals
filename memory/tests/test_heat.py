"""Tests for memory/heat.py — heat-based prioritization."""

from __future__ import annotations

import time

from memory.heat import HeatScorer


class TestHeatScorer:
    def test_hot_memory_high_score(self) -> None:
        scorer = HeatScorer()
        now = time.time()
        heat = scorer.compute(visit_count=10, interaction_length=500, last_accessed=now)
        assert heat > 0.5

    def test_cold_memory_low_score(self) -> None:
        scorer = HeatScorer()
        heat = scorer.compute(visit_count=0, interaction_length=10, last_accessed=0)
        assert heat < 0.5

    def test_score_in_range_0_to_1(self) -> None:
        scorer = HeatScorer()
        now = time.time()
        heat = scorer.compute(visit_count=100, interaction_length=10000, last_accessed=now)
        assert 0.0 <= heat <= 1.0

    def test_more_visits_higher_heat(self) -> None:
        scorer = HeatScorer()
        now = time.time()
        low = scorer.compute(visit_count=1, interaction_length=100, last_accessed=now)
        high = scorer.compute(visit_count=10, interaction_length=100, last_accessed=now)
        assert high > low

    def test_more_recent_higher_heat(self) -> None:
        scorer = HeatScorer()
        now = time.time()
        old = scorer.compute(visit_count=5, interaction_length=100, last_accessed=now - 86400)
        recent = scorer.compute(visit_count=5, interaction_length=100, last_accessed=now)
        assert recent > old

    def test_rank_sorts_by_heat(self) -> None:
        scorer = HeatScorer()
        now = time.time()
        entries = [
            {"id": "cold", "visit_count": 0, "interaction_length": 10, "last_accessed": 0},
            {"id": "hot", "visit_count": 10, "interaction_length": 500, "last_accessed": now},
            {"id": "warm", "visit_count": 3, "interaction_length": 100, "last_accessed": now - 3600},
        ]
        ranked = scorer.rank(entries)
        assert ranked[0]["id"] == "hot"
        assert ranked[-1]["id"] == "cold"
        assert all("heat" in e for e in ranked)

    def test_time_decay_exponential(self) -> None:
        scorer = HeatScorer(tau_hours=1.0)
        now = time.time()
        recent = scorer._time_decay(now, now)
        one_hour = scorer._time_decay(now - 3600, now)
        assert recent == 1.0
        assert 0 < one_hour < 1.0
