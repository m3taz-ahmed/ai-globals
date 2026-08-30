"""Tests for memory/decay_scheduler.py — memory decay scheduling."""

from __future__ import annotations

import time

from memory.decay_scheduler import DecayScheduler
from memory.sectors import Sector


class TestDecayScheduler:
    def test_register_entry(self) -> None:
        scheduler = DecayScheduler()
        entry = scheduler.register_entry("1", Sector.SEMANTIC, 1.0)
        assert entry.id == "1"
        assert entry.current_salience == 1.0

    def test_run_cycle_decays(self) -> None:
        scheduler = DecayScheduler(min_salience=0.0)
        scheduler.register_entry("1", Sector.EPISODIC, 1.0, created_at=time.time() - 86400 * 30)
        result = scheduler.run_cycle()
        assert result["decayed"] == 1
        entry = scheduler.get_entry("1")
        assert entry is not None
        assert entry.current_salience < 1.0

    def test_evict_below_threshold(self) -> None:
        scheduler = DecayScheduler(min_salience=0.5)
        scheduler.register_entry("1", Sector.EMOTIONAL, 1.0, created_at=time.time() - 86400 * 365)
        result = scheduler.run_cycle()
        assert result["evicted"] == 1
        assert scheduler.get_entry("1") is None

    def test_should_run_after_interval(self) -> None:
        scheduler = DecayScheduler(interval_seconds=0.3)
        base = 1000.0
        scheduler._last_run = base
        # Pass `now` explicitly — deterministic, no sleep needed
        assert scheduler.should_run(now=base + 0.5) is True

    def test_should_not_run_before_interval(self) -> None:
        scheduler = DecayScheduler(interval_seconds=3600)
        scheduler._last_run = time.time()
        assert scheduler.should_run() is False

    def test_entry_count(self) -> None:
        scheduler = DecayScheduler()
        scheduler.register_entry("1", Sector.SEMANTIC, 1.0)
        scheduler.register_entry("2", Sector.EPISODIC, 0.8)
        assert scheduler.entry_count == 2
