#!/usr/bin/env python3
"""Memory decay scheduler (from OpenMemory).

Schedules periodic decay of memory salience based on sector-specific
decay rates. Runs as a background task that updates memory scores.

Usage::

    from memory.decay_scheduler import DecayScheduler

    scheduler = DecayScheduler(interval_seconds=3600)
    scheduler.register_entries(entries)
    scheduler.run_cycle()  # Run one decay cycle
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from memory.sectors import Sector, SectorClassifier


@dataclass
class DecayableEntry:
    """A memory entry that can decay over time."""

    id: str
    sector: Sector
    initial_salience: float
    created_at: float
    last_decayed_at: float = 0.0
    current_salience: float = 0.0

    def __post_init__(self) -> None:
        if self.current_salience == 0.0:
            self.current_salience = self.initial_salience
        if self.last_decayed_at == 0.0:
            self.last_decayed_at = self.created_at


@dataclass
class DecayScheduler:
    """Schedule and execute memory decay cycles (from OpenMemory).

    Runs periodic decay updates on registered entries. Entries below
    a minimum salience threshold can be marked for eviction.
    """

    interval_seconds: float = 3600.0  # 1 hour default
    min_salience: float = 0.01  # Below this = evict
    _entries: dict[str, DecayableEntry] = field(default_factory=dict)
    _classifier: SectorClassifier = field(default_factory=SectorClassifier)
    _last_run: float = 0.0

    def register_entry(
        self,
        entry_id: str,
        sector: Sector,
        salience: float,
        created_at: float | None = None,
    ) -> DecayableEntry:
        """Register a memory entry for decay tracking."""
        now = created_at if created_at is not None else time.time()
        entry = DecayableEntry(
            id=entry_id, sector=sector,
            initial_salience=salience, created_at=now,
        )
        self._entries[entry_id] = entry
        return entry

    def run_cycle(self, now: float | None = None) -> dict[str, Any]:
        """Run one decay cycle. Returns summary stats.

        Decay is computed from the entry's TOTAL age (``now - created_at``),
        not since the last cycle — otherwise salience would jump back up
        after every cycle and eviction would never fire.
        """
        current_time = now if now is not None else time.time()
        decayed_count = 0
        evicted: list[str] = []
        for entry_id, entry in list(self._entries.items()):
            days_since = max(0.0, (current_time - entry.created_at) / 86400.0)
            new_salience = self._classifier.decay_score(
                entry.sector, entry.initial_salience, days_since,
            )
            entry.current_salience = new_salience
            entry.last_decayed_at = current_time
            decayed_count += 1
            if new_salience < self.min_salience:
                evicted.append(entry_id)
                del self._entries[entry_id]
        self._last_run = current_time
        return {
            "decayed": decayed_count,
            "evicted": len(evicted),
            "evicted_ids": evicted,
            "remaining": len(self._entries),
        }

    def should_run(self, now: float | None = None) -> bool:
        """Check if enough time has passed for another cycle."""
        current_time = now if now is not None else time.time()
        return (current_time - self._last_run) >= self.interval_seconds

    def get_entry(self, entry_id: str) -> DecayableEntry | None:
        return self._entries.get(entry_id)

    @property
    def entry_count(self) -> int:
        return len(self._entries)


if __name__ == "__main__":
    scheduler = DecayScheduler(interval_seconds=0)
    scheduler.register_entry("1", Sector.EPISODIC, 1.0, created_at=time.time() - 86400 * 30)
    result = scheduler.run_cycle()
    print(f"Decayed: {result['decayed']}, Evicted: {result['evicted']}")
