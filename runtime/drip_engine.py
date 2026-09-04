"""Drip / marketing-automation sequence engine.

A small trigger -> condition -> action state machine inspired by Mautic's
CampaignBundle (2.7.1). Sequences hold ordered steps; each step fires when
its trigger condition is satisfied and its optional delay has elapsed.

Raises ``ValidationError`` on duplicate sequences or unknown references.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from runtime.schemas import ValidationError


class Trigger(str, Enum):
    """Built-in trigger types that can start or advance a step."""

    ON_ENTER = "on_enter"
    ON_EVENT = "on_event"
    ON_DATE = "on_date"
    MANUAL = "manual"


def _as_aware(moment: datetime) -> datetime:
    """Coerce a naive datetime to UTC (aware datetimes pass through)."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


@dataclass
class Step:
    """A single step in a drip sequence."""

    step_id: str
    trigger: Trigger
    action: str
    condition: Callable[[dict[str, Any]], bool] | None = None
    delay_hours: float = 0.0
    entered_at: datetime | None = None
    fired: bool = False


@dataclass
class Sequence:
    """An ordered collection of drip steps."""

    name: str
    steps: list[Step] = field(default_factory=list)


class DripEngine:
    """Holds drip sequences and evaluates which steps are ready to fire."""

    def __init__(self) -> None:
        self._sequences: dict[str, Sequence] = {}

    def add_sequence(self, name: str) -> Sequence:
        """Register a new (empty) sequence and return it."""
        if name in self._sequences:
            raise ValidationError(
                "sequence already exists", context={"name": name}
            )
        seq = Sequence(name=name)
        self._sequences[name] = seq
        return seq

    def add_step(
        self,
        seq: Sequence,
        trigger: Trigger,
        condition: Callable[[dict[str, Any]], bool] | None,
        action: str,
        delay_hours: float = 0.0,
    ) -> Step:
        """Append a step to a sequence.

        Args:
            seq: The target sequence (must be registered via add_sequence).
            trigger: When this step should be considered.
            condition: Optional predicate over context; if it returns False
                the step is skipped.
            action: Identifier of the action to perform when fired.
            delay_hours: Hours to wait after entering before firing.
        """
        if delay_hours < 0:
            raise ValidationError(
                "delay_hours must be non-negative",
                context={"delay_hours": delay_hours},
            )
        step = Step(
            step_id=f"{seq.name}:{len(seq.steps)}",
            trigger=trigger,
            action=action,
            condition=condition,
            delay_hours=delay_hours,
        )
        seq.steps.append(step)
        return step

    def ready_steps(
        self,
        now: datetime | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[Step]:
        """Return all steps whose delay has elapsed and condition is met.

        A step is "ready" if it has been entered (``entered_at`` set), its
        delay has elapsed, it has not already fired, and its condition (if
        any) evaluates True against ``context`` (defaults to empty dict).
        Naive datetimes are treated as UTC; a raising condition skips only
        its own step instead of aborting the whole scan.
        """
        now = _as_aware(now or datetime.now(timezone.utc))
        ctx = context or {}
        ready: list[Step] = []
        for seq in self._sequences.values():
            for step in seq.steps:
                if step.fired or step.entered_at is None:
                    continue
                try:
                    entered = _as_aware(step.entered_at)
                    elapsed = (now - entered).total_seconds() / 3600.0
                except (TypeError, ValueError, OverflowError):
                    continue
                if elapsed < step.delay_hours:
                    continue
                if step.condition is not None:
                    try:
                        if not step.condition(ctx):
                            continue
                    except Exception:
                        continue
                ready.append(step)
        return ready

    def enter(self, step: Step, now: datetime | None = None) -> None:
        """Mark a step as entered (starts its delay countdown)."""
        step.entered_at = _as_aware(now or datetime.now(timezone.utc))

    def mark_fired(self, step: Step) -> None:
        """Mark a step as fired so it is not returned again."""
        step.fired = True

    def sequence(self, name: str) -> Sequence:
        if name not in self._sequences:
            raise ValidationError(
                "unknown sequence", context={"name": name}
            )
        return self._sequences[name]
