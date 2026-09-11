#!/usr/bin/env python3
"""Library-based durable execution with deterministic replay.

Inspired by edda: no external server required — runs in-process with
crash recovery. Workflow state is persisted to JSON files in a state
directory before and after each step, so a crash at any point can be
resumed from the last completed step.

Key design decisions:
- **JSON persistence**: each workflow is a single JSON file, atomically
  written (temp file + ``os.replace``) to prevent corruption.
- **Deterministic replay**: on recovery, the executor loads the workflow
  state and resumes from ``current_step``, skipping already-completed steps.
- **Compensating actions**: failed steps can declare a ``compensate``
  handler that runs in reverse order, mirroring saga semantics.

Architecture::

    DurableExecutor.execute(workflow_id, steps, handler)
        -> before each step: persist workflow state
        -> run handler(step) -> persist result
        -> on crash: recover(workflow_id) resumes from last checkpoint
        -> on failure: run compensations for completed steps

Usage::

    from runtime.durable import DurableExecutor
    from pathlib import Path

    executor = DurableExecutor(Path("./state/durable"))
    workflow = executor.execute(
        workflow_id="wf-001",
        steps=[
            {"step_id": "s1", "name": "fetch", "args": {"url": "..."}},
            {"step_id": "s2", "name": "transform", "args": {}},
        ],
        handler=lambda step: {"ok": True, "data": "..."},
    )
    if workflow.status != "completed":
        recovered = executor.recover("wf-001")
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class StepStatus(str, Enum):
    """Status of a single durable step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class DurableStep:
    """A single step in a durable workflow.

    Attributes:
        step_id: Unique identifier within the workflow.
        name: Human-readable step name.
        status: Current execution status.
        args: Input arguments for the step handler.
        result: Output from the handler (None until completed).
        error: Error message if the step failed (None otherwise).
        started_at: Unix timestamp when execution started.
        completed_at: Unix timestamp when execution finished.
    """

    step_id: str
    name: str
    status: StepStatus = StepStatus.PENDING
    args: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str | None = None
    started_at: float | None = None
    completed_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON persistence."""
        return {
            "step_id": self.step_id,
            "name": self.name,
            "status": self.status.value,
            "args": self.args,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DurableStep:
        """Deserialize from dict (loaded from JSON)."""
        return cls(
            step_id=data["step_id"],
            name=data["name"],
            status=StepStatus(data.get("status", StepStatus.PENDING.value)),
            args=data.get("args", {}),
            result=data.get("result"),
            error=data.get("error"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )


@dataclass
class DurableWorkflow:
    """A durable workflow with ordered steps and crash-recovery state.

    Attributes:
        workflow_id: Unique identifier for the workflow.
        name: Human-readable workflow name.
        steps: Ordered list of steps.
        current_step: Index of the step to execute next.
        status: Workflow-level status string ("running", "completed", "failed", "cancelled").
        started_at: Unix timestamp when the workflow started.
        completed_at: Unix timestamp when the workflow finished (None if still running).
    """

    workflow_id: str
    name: str
    steps: list[DurableStep] = field(default_factory=list)
    current_step: int = 0
    status: str = "running"
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON persistence."""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
            "current_step": self.current_step,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DurableWorkflow:
        """Deserialize from dict (loaded from JSON)."""
        return cls(
            workflow_id=data["workflow_id"],
            name=data["name"],
            steps=[DurableStep.from_dict(s) for s in data.get("steps", [])],
            current_step=data.get("current_step", 0),
            status=data.get("status", "running"),
            started_at=data.get("started_at", time.time()),
            completed_at=data.get("completed_at"),
        )


class DurableError(AizeeError):
    """Raised when durable execution encounters an error."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("DURABLE_ERROR", message, ErrorSeverity.HIGH, context)


# ---------------------------------------------------------------------------
# Step handler type
# ---------------------------------------------------------------------------

StepHandler = Callable[[DurableStep], Any]
CompensateHandler = Callable[[DurableStep], Any]


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


class DurableExecutor:
    """Executes durable workflows with crash recovery via JSON persistence.

    Each workflow is persisted as a single JSON file in ``state_dir``.
    State is saved before and after every step, so a crash at any point
    leaves a consistent checkpoint on disk. On restart, ``recover()``
    loads the checkpoint and resumes from the last completed step.

    Thread-safe via ``RLock``: multiple workflows can be executed
    concurrently from different threads (each gets its own file).
    """

    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    # -- Public API ----------------------------------------------------------

    def execute(
        self,
        workflow_id: str,
        steps: list[dict[str, Any]],
        handler: StepHandler,
        compensate: CompensateHandler | None = None,
    ) -> DurableWorkflow:
        """Execute a workflow with crash recovery.

        Resumes incomplete workflows; creates new ones if not found.
        See module docstring for full semantics.
        """
        with self._lock:
            existing = self._load_workflow(workflow_id)
            if existing is not None and existing.status == "running":
                workflow = existing
                _logger.info("resuming workflow %s from step %d", workflow_id, workflow.current_step)
            elif existing is not None:
                return existing
            else:
                workflow = self._create_workflow(workflow_id, steps)
                self._persist(workflow)

        return self._run_steps(workflow, handler, compensate)

    def recover(self, workflow_id: str) -> DurableWorkflow | None:
        """Recover an incomplete workflow from persisted state.

        Returns the workflow if it exists and is still running, None otherwise.
        Does NOT re-execute steps — call ``execute()`` to resume.
        """
        with self._lock:
            workflow = self._load_workflow(workflow_id)
        if workflow is None:
            return None
        if workflow.status != "running":
            _logger.info("workflow %s is %s, nothing to recover", workflow_id, workflow.status)
            return workflow
        return workflow

    def list_workflows(self) -> list[str]:
        """Return all workflow IDs found in the state directory."""
        with self._lock:
            ids: list[str] = []
            for path in self._state_dir.glob("*.json"):
                if path.is_file():
                    ids.append(path.stem)
            return sorted(ids)

    def get_workflow(self, workflow_id: str) -> DurableWorkflow | None:
        """Return the persisted workflow state, or None if not found."""
        with self._lock:
            return self._load_workflow(workflow_id)

    def cancel(self, workflow_id: str) -> bool:
        """Cancel a running workflow. Returns True if it was running."""
        with self._lock:
            workflow = self._load_workflow(workflow_id)
            if workflow is None:
                return False
            if workflow.status != "running":
                return False
            workflow.status = "cancelled"
            workflow.completed_at = time.time()
            self._persist(workflow)
        _logger.info("cancelled workflow %s", workflow_id)
        return True

    # -- Internal helpers (each < 30 lines) ---------------------------------

    def _create_workflow(
        self, workflow_id: str, steps: list[dict[str, Any]]
    ) -> DurableWorkflow:
        """Build a new DurableWorkflow from step dicts."""
        durable_steps = [
            DurableStep(
                step_id=s.get("step_id", f"step-{i}"),
                name=s.get("name", f"step-{i}"),
                args=s.get("args", {}),
            )
            for i, s in enumerate(steps)
        ]
        return DurableWorkflow(
            workflow_id=workflow_id,
            name=workflow_id,
            steps=durable_steps,
        )

    def _run_steps(
        self,
        workflow: DurableWorkflow,
        handler: StepHandler,
        compensate: CompensateHandler | None,
    ) -> DurableWorkflow:
        """Execute remaining steps, persisting state before and after each."""
        while workflow.current_step < len(workflow.steps):
            if workflow.status != "running":
                break
            if self._advance_step(workflow, handler, compensate):
                break
        self._finalize(workflow)
        self._persist(workflow)
        return workflow

    def _advance_step(
        self,
        workflow: DurableWorkflow,
        handler: StepHandler,
        compensate: CompensateHandler | None,
    ) -> bool:
        """Execute the current step. Returns True if the loop should stop."""
        step = workflow.steps[workflow.current_step]
        if step.status is StepStatus.COMPLETED:
            workflow.current_step += 1
            return False
        self._persist(workflow)
        ok = self._run_single_step(workflow, step, handler)
        self._persist(workflow)
        if not ok:
            self._compensate(workflow, handler, compensate)
            return True
        workflow.current_step += 1
        return False

    def _run_single_step(
        self,
        workflow: DurableWorkflow,
        step: DurableStep,
        handler: StepHandler,
    ) -> bool:
        """Execute a single step via the handler. Returns True on success."""
        step.status = StepStatus.RUNNING
        step.started_at = time.time()
        try:
            result = handler(step)
        except Exception as exc:
            step.status = StepStatus.FAILED
            step.error = str(exc)
            step.completed_at = time.time()
            _logger.error("step %s failed: %s", step.step_id, exc, exc_info=True)
            return False
        step.result = result
        step.status = StepStatus.COMPLETED
        step.completed_at = time.time()
        _logger.debug("step %s completed", step.step_id)
        return True

    def _compensate(
        self,
        workflow: DurableWorkflow,
        handler: StepHandler,
        compensate: CompensateHandler | None,
    ) -> None:
        """Run compensating actions for completed steps in reverse order."""
        if compensate is None:
            return
        for i in range(workflow.current_step - 1, -1, -1):
            step = workflow.steps[i]
            if step.status is not StepStatus.COMPLETED:
                continue
            try:
                compensate(step)
                step.status = StepStatus.COMPENSATED
            except Exception as exc:
                _logger.error("compensation for %s failed: %s", step.step_id, exc)

    def _finalize(self, workflow: DurableWorkflow) -> None:
        """Set the workflow's final status based on step outcomes."""
        if workflow.status != "running":
            return
        all_done = all(s.status is StepStatus.COMPLETED for s in workflow.steps)
        any_failed = any(s.status is StepStatus.FAILED for s in workflow.steps)
        if all_done:
            workflow.status = "completed"
        elif any_failed:
            workflow.status = "failed"
        workflow.completed_at = time.time()

    def _persist(self, workflow: DurableWorkflow) -> None:
        """Atomically write workflow state to a JSON file."""
        path = self._workflow_path(workflow.workflow_id)
        data = json.dumps(workflow.to_dict(), default=str, indent=2)
        tmp_fd, tmp_path_str = _mkstemp(self._state_dir, workflow.workflow_id)
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                f.write(data)
            os.replace(tmp_path_str, str(path))
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path_str)
            raise

    def _load_workflow(self, workflow_id: str) -> DurableWorkflow | None:
        """Load a workflow from disk, or None if it doesn't exist."""
        path = self._workflow_path(workflow_id)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise DurableError(
                f"failed to load workflow {workflow_id}: {exc}",
                context={"workflow_id": workflow_id},
            ) from exc
        return DurableWorkflow.from_dict(data)

    def _workflow_path(self, workflow_id: str) -> Path:
        """Return the JSON file path for a workflow ID."""
        safe_id = workflow_id.replace("/", "_").replace("\\", "_")
        return self._state_dir / f"{safe_id}.json"


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _mkstemp(state_dir: Path, workflow_id: str) -> tuple[int, str]:
    """Create a temp file in the state dir, returning (fd, path)."""
    import tempfile

    prefix = workflow_id.replace("/", "_").replace("\\", "_")[:32] + "."
    return tempfile.mkstemp(dir=str(state_dir), suffix=".tmp", prefix=prefix)
