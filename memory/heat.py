#!/usr/bin/env python3
"""Heat-based memory prioritization.

Multi-factor heat scoring for memory sections, inspired by MemoryOS.
Heat = alpha * visit_count + beta * interaction_length + gamma * recency.

Usage::

    from memory.heat import HeatScorer

    scorer = HeatScorer()
    heat = scorer.compute(visit_count=5, interaction_length=200, last_accessed=now)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

# Default weights (from MemoryOS)
HEAT_ALPHA = 0.4   # visit frequency weight
HEAT_BETA = 0.3    # interaction length weight
HEAT_GAMMA = 0.3   # recency weight
RECENCY_TAU_HOURS = 24.0  # recency decay time constant


@dataclass
class HeatScorer:
    """Compute heat scores for memory prioritization.

    Higher heat = more important/relevant memory. Uses max-heap
    semantics for hottest-section tracking.
    """

    alpha: float = HEAT_ALPHA
    beta: float = HEAT_BETA
    gamma: float = HEAT_GAMMA
    tau_hours: float = RECENCY_TAU_HOURS

    def compute(
        self,
        visit_count: int = 0,
        interaction_length: int = 0,
        last_accessed: float | None = None,
        max_interaction: int = 1000,
    ) -> float:
        """Compute heat score in range [0, 1].

        Args:
            visit_count: Number of times this memory was accessed.
            interaction_length: Length of interaction content (chars).
            last_accessed: Unix timestamp of last access.
            max_interaction: Normalization factor for interaction length.
        """
        now = time.time()
        ts = last_accessed if last_accessed is not None else now
        recency = self._time_decay(ts, now)
        normalized_visits = min(visit_count / 10.0, 1.0)
        normalized_length = min(interaction_length / max(max_interaction, 1), 1.0)
        raw = (
            self.alpha * normalized_visits
            + self.beta * normalized_length
            + self.gamma * recency
        )
        return min(max(raw, 0.0), 1.0)

    def _time_decay(self, past: float, now: float) -> float:
        """Exponential time decay: recent = 1.0, old → 0.0."""
        hours_ago = max((now - past) / 3600.0, 0.0)
        return math.exp(-hours_ago / self.tau_hours)

    def rank(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rank entries by heat score (highest first)."""
        scored = []
        for entry in entries:
            heat = self.compute(
                visit_count=entry.get("visit_count", 0),
                interaction_length=entry.get("interaction_length", 0),
                last_accessed=entry.get("last_accessed"),
            )
            scored.append({**entry, "heat": heat})
        scored.sort(key=lambda e: e["heat"], reverse=True)
        return scored


if __name__ == "__main__":
    scorer = HeatScorer()
    print(f"Hot: {scorer.compute(visit_count=10, interaction_length=500):.3f}")
    print(f"Cold: {scorer.compute(visit_count=0, interaction_length=10, last_accessed=0):.3f}")
