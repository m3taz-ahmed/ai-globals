#!/usr/bin/env python3
"""Feedback-loop memory for agent actions.

Re-implements the preloop pattern: store action outcomes, reflect on them,
and adjust future action selection based on historical success/failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Outcome:
    """An observed outcome of an agent action."""

    action: str
    ok: bool
    reward: float
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class FeedbackLoop:
    """Stores outcomes and ranks actions by historical success."""

    def __init__(self, capacity: int = 1000) -> None:
        self._outcomes: list[Outcome] = []
        self._capacity = capacity

    def record(self, outcome: Outcome) -> None:
        self._outcomes.append(outcome)
        if len(self._outcomes) > self._capacity:
            self._outcomes.pop(0)

    def score(self, action: str, tag: str | None = None) -> float:
        """Return a success score for an action, optionally filtered by tag."""
        matches = [o for o in self._outcomes if o.action == action and (tag is None or tag in o.tags)]
        if not matches:
            return 0.5
        total_reward = sum(o.reward for o in matches)
        return total_reward / len(matches)

    def best_action(self, actions: list[str], tag: str | None = None) -> str | None:
        """Select the action with the highest historical score."""
        if not actions:
            return None
        return max(actions, key=lambda a: self.score(a, tag))

    def reflect(self, action: str, min_samples: int = 3) -> dict[str, Any]:
        """Return a reflection summary for an action."""
        matches = [o for o in self._outcomes if o.action == action]
        total = len(matches)
        if total < min_samples:
            return {"action": action, "samples": total, "advice": "collect more data"}
        success_rate = sum(1 for o in matches if o.ok) / total
        avg_reward = sum(o.reward for o in matches) / total
        return {
            "action": action,
            "samples": total,
            "success_rate": success_rate,
            "average_reward": avg_reward,
            "advice": "keep" if success_rate > 0.7 else "tune" if success_rate > 0.4 else "avoid",
        }
