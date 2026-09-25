#!/usr/bin/env python3
"""Task-contract data models: enums, errors, tasks, plans."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity

TASK_DIR = ".task"
PLAN_FILE = "plan.json"
REVIEW_DIR = "reviews"
CLASSIFICATIONS_FILE = "classifications.jsonl"
STRICT_ENV = "AIZEE_TASK_STRICT"


class TaskContractError(AizeeError):
    """Raised when a task-contract invariant is violated."""

    def __init__(
        self,
        error_code: str,
        message: str,
        context: dict[str, Any] | None = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ) -> None:
        super().__init__(error_code, message, severity, context)


class Classification(str, Enum):
    """Work-size classification for incoming prompts."""

    TRIVIAL = "trivial"
    STANDARD = "standard"
    COMPLEX = "complex"


class TaskStatus(str, Enum):
    """Lifecycle of a single contract task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"  # evidence recorded, awaiting completion
    DONE = "done"
    BLOCKED = "blocked"


class PlanStatus(str, Enum):
    """Lifecycle of a task plan."""

    ACTIVE = "active"
    DONE = "done"
    ABANDONED = "abandoned"


class Risk(str, Enum):
    """Risk level declared per task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def _status_of(raw: str) -> TaskStatus:
    try:
        return TaskStatus(raw)
    except ValueError:
        return TaskStatus.PENDING


def _risk_of(raw: str) -> Risk:
    try:
        return Risk(raw)
    except ValueError:
        return Risk.LOW


def now_stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ContractTask:
    """One atomic unit of contracted work.

    ``produces`` is the handoff contract: downstream tasks may depend on this
    task and get its artifact verified before they start. ``files`` declares
    edit scope — tasks finished with no declared scope are flagged at review.
    """

    id: str
    title: str
    description: str = ""
    depends_on: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    produces: str = ""  # artifact contract: file, interface, migration, doc
    acceptance: list[str] = field(default_factory=list)  # check descriptions
    verify_cmd: str = ""  # optional command; must exit 0
    risk: Risk = Risk.LOW
    status: TaskStatus = TaskStatus.PENDING
    evidence: str = ""
    review_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "depends_on": list(self.depends_on),
            "files": list(self.files),
            "produces": self.produces,
            "acceptance": list(self.acceptance),
            "verify_cmd": self.verify_cmd,
            "risk": self.risk.value,
            "status": self.status.value,
            "evidence": self.evidence,
            "review_note": self.review_note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContractTask:
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            depends_on=[str(d) for d in data.get("depends_on", [])],
            files=[str(f) for f in data.get("files", [])],
            produces=str(data.get("produces", "")),
            acceptance=[str(a) for a in data.get("acceptance", [])],
            verify_cmd=str(data.get("verify_cmd", "")),
            risk=_risk_of(str(data.get("risk", "low"))),
            status=_status_of(str(data.get("status", "pending"))),
            evidence=str(data.get("evidence", "")),
            review_note=str(data.get("review_note", "")),
        )


@dataclass
class TaskPlan:
    """The active work plan stored at ``<project>/.task/plan.json``."""

    id: str
    title: str
    prompt_summary: str = ""
    classification: str = Classification.STANDARD.value
    classification_reason: str = ""
    status: PlanStatus = PlanStatus.ACTIVE
    tasks: list[ContractTask] = field(default_factory=list)
    active_task_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)
    amendments: list[dict[str, Any]] = field(default_factory=list)

    def task(self, task_id: str) -> ContractTask:
        for t in self.tasks:
            if t.id == task_id:
                return t
        raise TaskContractError(
            "TASK_NOT_FOUND", f"task '{task_id}' not in plan '{self.id}'", {"task_id": task_id}
        )

    def next_pending(self) -> ContractTask | None:
        done = {t.id for t in self.tasks if t.status == TaskStatus.DONE}
        for t in self.tasks:
            if t.status == TaskStatus.PENDING and all(d in done for d in t.depends_on):
                return t
        return None

    def record(self, event: str, detail: dict[str, Any] | None = None) -> None:
        stamp = now_stamp()
        self.history.append({"event": event, "at": stamp, "detail": detail or {}})
        self.updated_at = stamp

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "prompt_summary": self.prompt_summary,
            "classification": self.classification,
            "classification_reason": self.classification_reason,
            "status": self.status.value,
            "active_task_id": self.active_task_id,
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "history": list(self.history),
            "amendments": list(self.amendments),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskPlan:
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            prompt_summary=str(data.get("prompt_summary", "")),
            classification=str(data.get("classification", Classification.STANDARD.value)),
            classification_reason=str(data.get("classification_reason", "")),
            status=PlanStatus(str(data.get("status", PlanStatus.ACTIVE.value))),
            tasks=[ContractTask.from_dict(t) for t in data.get("tasks", [])],
            active_task_id=str(data.get("active_task_id", "")),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            history=list(data.get("history", [])),
            amendments=list(data.get("amendments", [])),
        )
