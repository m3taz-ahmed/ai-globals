"""Declarative CRM manager: companies, people, opportunities, tasks.

A metadata-driven, lightweight CRM inspired by Twenty's object model and
Huly's plugin registry (2.7.12). Opportunity and Task enforce explicit,
validated stage transitions. Raises ``ValidationError`` on invalid moves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from runtime.schemas import ValidationError


class OpportunityStage(str, Enum):
    """Sales-pipeline stages for an opportunity."""

    NEW = "new"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    WON = "won"
    LOST = "lost"


class TaskStage(str, Enum):
    """Lifecycle stages for a task."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


_OPPORTUNITY_TRANSITIONS: dict[OpportunityStage, set[OpportunityStage]] = {
    OpportunityStage.NEW: {OpportunityStage.QUALIFIED, OpportunityStage.LOST},
    OpportunityStage.QUALIFIED: {OpportunityStage.PROPOSAL, OpportunityStage.LOST},
    OpportunityStage.PROPOSAL: {
        OpportunityStage.WON,
        OpportunityStage.LOST,
        OpportunityStage.QUALIFIED,
    },
    OpportunityStage.WON: set(),
    OpportunityStage.LOST: set(),
}

_TASK_TRANSITIONS: dict[TaskStage, set[TaskStage]] = {
    TaskStage.TODO: {TaskStage.IN_PROGRESS, TaskStage.CANCELLED, TaskStage.DONE},
    TaskStage.IN_PROGRESS: {TaskStage.DONE, TaskStage.CANCELLED, TaskStage.TODO},
    TaskStage.DONE: set(),
    TaskStage.CANCELLED: set(),
}

# Terminal stages have no outgoing transitions (not re-enterable, not leavable).
_TERMINAL_OPPORTUNITY: frozenset[OpportunityStage] = frozenset({OpportunityStage.WON, OpportunityStage.LOST})
_TERMINAL_TASK: frozenset[TaskStage] = frozenset({TaskStage.DONE, TaskStage.CANCELLED})

# NOTE (transition asymmetry, intentional): Opportunity requires stepwise
# progression (NEW→QUALIFIED→PROPOSAL→WON, no skips), while Task allows a
# TODO→DONE fast-track for trivial tasks. Kept for backward compatibility.


@dataclass
class Company:
    """An organization in the CRM."""

    company_id: str
    name: str
    domain: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Person:
    """A contact (person) in the CRM."""

    person_id: str
    name: str
    email: str = ""
    company_id: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Opportunity:
    """A sales opportunity with enforced stage transitions."""

    opportunity_id: str
    company_id: str
    stage: OpportunityStage = OpportunityStage.NEW
    amount: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    def validate_transition(self, target: OpportunityStage) -> None:
        """Raise if moving to ``target`` is not allowed from current stage."""
        if target == self.stage:
            if self.stage in _TERMINAL_OPPORTUNITY:
                raise ValidationError(
                    "terminal opportunity stage is not re-enterable",
                    context={"from": self.stage.value, "to": target.value, "allowed": []},
                )
            return
        if self.stage in _TERMINAL_OPPORTUNITY:
            raise ValidationError(
                "terminal opportunity stage has no outgoing transitions",
                context={"from": self.stage.value, "to": target.value, "allowed": []},
            )
        allowed = _OPPORTUNITY_TRANSITIONS.get(self.stage, set())
        if target not in allowed:

            raise ValidationError(
                "invalid opportunity transition",
                context={
                    "from": self.stage.value,
                    "to": target.value,
                    "allowed": [s.value for s in allowed],
                },
            )

    def transition(self, target: OpportunityStage) -> None:
        """Move to ``target`` after validating the transition."""
        self.validate_transition(target)
        self.stage = target


@dataclass
class Task:
    """A task with enforced lifecycle transitions."""

    task_id: str
    title: str
    stage: TaskStage = TaskStage.TODO
    assignee_id: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def validate_transition(self, target: TaskStage) -> None:
        if target == self.stage:
            if self.stage in _TERMINAL_TASK:
                raise ValidationError(
                    "terminal task stage is not re-enterable",
                    context={"from": self.stage.value, "to": target.value, "allowed": []},
                )
            return
        if self.stage in _TERMINAL_TASK:
            raise ValidationError(
                "terminal task stage has no outgoing transitions",
                context={"from": self.stage.value, "to": target.value, "allowed": []},
            )
        allowed = _TASK_TRANSITIONS.get(self.stage, set())
        if target not in allowed:

            raise ValidationError(
                "invalid task transition",
                context={
                    "from": self.stage.value,
                    "to": target.value,
                    "allowed": [s.value for s in allowed],
                },
            )

    def transition(self, target: TaskStage) -> None:
        self.validate_transition(target)
        self.stage = target
