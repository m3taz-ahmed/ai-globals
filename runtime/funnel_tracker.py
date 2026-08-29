"""Funnel drop-off tracker.

Records an ordered set of funnel steps and the touchpoints that reach each
step, then computes per-step conversion and drop-off. Inspired by Umami's
funnel event schema (2.7.5). Pure-Python; raises ``ValidationError`` on
duplicate steps or negative indexes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from runtime.schemas import ValidationError


@dataclass
class FunnelStep:
    """A single step in a conversion funnel."""

    name: str
    reached: int = 0


class Funnel:
    """Ordered funnel with drop-off analytics."""

    def __init__(self, name: str = "funnel") -> None:
        self.name = name
        self.steps: list[FunnelStep] = []

    def add_step(self, name: str) -> FunnelStep:
        """Append a step to the funnel in order."""
        if any(s.name == name for s in self.steps):
            raise ValidationError(
                "duplicate funnel step", context={"step": name}
            )
        step = FunnelStep(name=name)
        self.steps.append(step)
        return step

    def record(self, touchpoint: dict[str, Any]) -> None:
        """Record a touchpoint that reached up to ``step_index``.

        The touchpoint must contain ``step_index`` (0-based) indicating the
        furthest step reached. All steps <= that index are incremented.
        """
        if not isinstance(touchpoint, dict) or "step_index" not in touchpoint:
            raise ValidationError("touchpoint needs 'step_index'")
        idx = touchpoint["step_index"]
        if not isinstance(idx, int) or idx < 0:
            raise ValidationError("step_index must be a non-negative int")
        if idx >= len(self.steps):
            raise ValidationError(
                "step_index out of range",
                context={"step_index": idx, "steps": len(self.steps)},
            )
        for i in range(idx + 1):
            self.steps[i].reached += 1

    def dropoff(self) -> list[dict[str, Any]]:
        """Return per-step conversion rate and drop-off vs the previous step."""
        result: list[dict[str, Any]] = []
        prev = None
        for step in self.steps:
            if prev is None:
                conversion = 1.0 if step.reached > 0 else 0.0
                dropoff = 0.0
            elif prev == 0:
                conversion = 0.0
                dropoff = 1.0
            else:
                conversion = step.reached / prev
                dropoff = 1.0 - conversion
            result.append(
                {
                    "step": step.name,
                    "reached": step.reached,
                    "conversion_from_prev": round(conversion, 4),
                    "dropoff_from_prev": round(dropoff, 4),
                }
            )
            prev = step.reached
        return result
