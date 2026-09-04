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
        self._seen: dict[int, set[str]] = {}

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

        Only the contiguous reachable prefix is incremented: a touchpoint
        carries its own ``reached`` set (or a single ``step_index`` for
        backward compat). Advancing to step N requires passing through all
        earlier steps — steps are only counted when the full prefix path
        is present. Each user (``user_id``/``user``/``id`` when present)
        is counted once per step (dedupe via seen-user set).

        Baseline semantics: the first step's ``conversion_from_prev`` is
        1.0 when it has any traffic (it is the baseline), else 0.0.
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
        # Contiguous reachable prefix: if the touchpoint declares which
        # steps it actually passed through (via `reached`/`steps`), only
        # count the contiguous prefix from 0. A bare `step_index` keeps
        # legacy behavior (prefix 0..idx) since it implies traversal.
        reached = touchpoint.get("reached", touchpoint.get("steps"))
        if reached is not None:
            if not isinstance(reached, (list, tuple, set)):
                raise ValidationError("'reached' must be a list of step indexes/names")
            reached_idx: set[int] = set()
            for r in reached:
                if isinstance(r, int):
                    reached_idx.add(r)
                elif isinstance(r, str):
                    for i, s in enumerate(self.steps):
                        if s.name == r:
                            reached_idx.add(i)
            prefix = 0
            while prefix <= idx and prefix in reached_idx:
                prefix += 1
            # `prefix` is count of contiguous steps from 0 within reached.
            end = min(prefix, idx + 1)
        else:
            end = idx + 1
        # Dedupe same user: count once per step.
        user_id = touchpoint.get("user_id", touchpoint.get("user", touchpoint.get("id")))
        for i in range(end):
            if user_id is not None:
                seen = self._seen.setdefault(i, set())
                key = str(user_id)
                if key in seen:
                    continue
                seen.add(key)
            self.steps[i].reached += 1

    def dropoff(self) -> list[dict[str, Any]]:
        """Return per-step conversion rate and drop-off vs the previous step.

        Baseline semantics: step 0 is the funnel entry baseline, so its
        ``conversion_from_prev`` is 1.0 whenever it has any traffic
        (0.0 when empty). Later steps are relative to the previous step.
        """
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
