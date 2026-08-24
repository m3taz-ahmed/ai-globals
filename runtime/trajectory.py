#!/usr/bin/env python3
"""Run-level trajectory tracking with stall detection for aiZee.

Inspired by Decapod's ``trajectory.rs``: every kernel action is recorded
as a trajectory step with intent, boundaries, inspected files, checks,
and loop signals. The tracker detects stalled runs (contiguous failed
attempts without progress) and convergence (intent preserved + proof
gathered).

This complements ``runtime/audit.py`` (append-only log) by adding
*run-level* state and *stall detection* — the audit log records what
happened, the trajectory records whether the run is converging.

Usage::

    from runtime.trajectory import TrajectoryTracker
    tracker = TrajectoryTracker(original_intent="add auth feature")
    tracker.start_run("run-1", "add login form", boundary="auth module")
    tracker.record_step("run-1", action="write", file="auth.py", status="ok")
    if tracker.is_stalled("run-1"):
        print("Run stalled — escalate or stop")
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class StepStatus(str, Enum):
    """Status of a single trajectory step."""

    OK = "ok"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class RunStatus(str, Enum):
    """Status of a whole run."""

    RUNNING = "running"
    CONVERGED = "converged"
    STALLED = "stalled"
    ABORTED = "aborted"


class FailureCategory(str, Enum):
    """10-category failure taxonomy (from microsoft/AgentRx).

    Classifies the root cause of a failed trajectory step.
    """

    INSTRUCTION_ADHERENCE = "instruction_adherence"  # Did not follow instructions/plan
    INVENTION = "invention"  # Invented new information not in context
    INVALID_INVOCATION = "invalid_invocation"  # Wrong tool, wrong args, wrong format
    MISINTERPRETATION = "misinterpretation"  # Misinterpreted tool output
    INTENT_PLAN_MISALIGNMENT = "intent_plan_misalignment"  # Plan diverged from intent
    UNDERSPECIFIED_INTENT = "underspecified_intent"  # User intent too vague
    INTENT_NOT_SUPPORTED = "intent_not_supported"  # Task outside agent capabilities
    GUARDRAILS_TRIGGERED = "guardrails_triggered"  # Policy/guardrail blocked the action
    SYSTEM_FAILURE = "system_failure"  # Infrastructure error (timeout, crash)
    INCONCLUSIVE = "inconclusive"  # Could not determine root cause


@dataclass
class TrajectoryStep:
    """A single recorded action in a run."""

    action: str
    status: StepStatus
    timestamp: float = field(default_factory=time.time)
    file: str | None = None
    check: str | None = None
    evidence: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    failure_category: FailureCategory | None = None  # Set when status is FAILED/BLOCKED
    tool_name: str | None = None  # Tool invoked (for NDJSON trace schema)
    tool_input: dict[str, Any] | None = None  # Tool args (for NDJSON trace schema)
    tool_output: str | None = None  # Tool result (for NDJSON trace schema)


@dataclass
class TrajectoryRun:
    """A single run with its steps and intent."""

    run_id: str
    original_intent: str
    derived_intent: str = ""
    boundary: str = ""
    scope: str = ""
    steps: list[TrajectoryStep] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    status: RunStatus = RunStatus.RUNNING
    inspected_files: set[str] = field(default_factory=set)
    modified_files: set[str] = field(default_factory=set)
    checks: dict[str, str] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)

    @property
    def contiguous_failures(self) -> int:
        """Count of trailing failed/blocked steps."""
        count = 0
        for step in reversed(self.steps):
            if step.status in (StepStatus.FAILED, StepStatus.BLOCKED):
                count += 1
            else:
                break
        return count

    @property
    def has_progress(self) -> bool:
        """True if at least one ok step exists."""
        return any(s.status is StepStatus.OK for s in self.steps)


class TrajectoryTracker:
    """Tracks run-level trajectories and detects stalls.

    A stall is detected when ``contiguous_failures >= stall_threshold``
    and the run has not converged. This signals the agent to escalate
    or stop rather than retry blindly.
    """

    def __init__(self, original_intent: str = "", stall_threshold: int = 3) -> None:
        if stall_threshold < 1:
            raise ValueError("stall_threshold must be >= 1")
        self.original_intent = original_intent
        self.stall_threshold = stall_threshold
        self._runs: dict[str, TrajectoryRun] = {}

    def start_run(
        self,
        run_id: str | None = None,
        derived_intent: str = "",
        boundary: str = "",
        scope: str = "",
    ) -> str:
        """Start a new run. Returns the run_id."""
        rid = run_id or uuid.uuid4().hex
        self._runs[rid] = TrajectoryRun(
            run_id=rid,
            original_intent=self.original_intent,
            derived_intent=derived_intent,
            boundary=boundary,
            scope=scope,
        )
        return rid

    def record_step(
        self,
        run_id: str,
        action: str,
        status: StepStatus,
        file: str | None = None,
        check: str | None = None,
        evidence: str | None = None,
        failure_category: FailureCategory | None = None,
        tool_name: str | None = None,
        tool_input: dict[str, Any] | None = None,
        tool_output: str | None = None,
        **metadata: Any,
    ) -> TrajectoryStep:
        """Record a step in a run."""
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"unknown run_id {run_id!r}")
        step = TrajectoryStep(
            action=action,
            status=status,
            file=file,
            check=check,
            evidence=evidence,
            metadata=metadata,
            failure_category=failure_category,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
        )
        run.steps.append(step)
        if file:
            if status is StepStatus.OK:
                run.modified_files.add(file)
            else:
                run.inspected_files.add(file)
        if check:
            run.checks[check] = status.value
        # Auto-update run status on stall.
        if self.is_stalled(run_id):
            run.status = RunStatus.STALLED
        return step

    def record_assumption(self, run_id: str, assumption: str) -> None:
        """Record an unverified assumption for epistemic custody."""
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"unknown run_id {run_id!r}")
        run.assumptions.append(assumption)

    def is_stalled(self, run_id: str) -> bool:
        """Detect a stalled run (contiguous failures >= threshold)."""
        run = self._runs.get(run_id)
        if run is None:
            return False
        if run.status is RunStatus.STALLED:
            return True
        if run.status is not RunStatus.RUNNING:
            return False
        return run.contiguous_failures >= self.stall_threshold

    def mark_converged(self, run_id: str, evidence: str = "") -> None:
        """Mark a run as converged (intent preserved + proof gathered)."""
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"unknown run_id {run_id!r}")
        run.status = RunStatus.CONVERGED
        if evidence:
            run.checks["convergence_evidence"] = evidence

    def abort(self, run_id: str, reason: str = "") -> None:
        """Abort a run."""
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"unknown run_id {run_id!r}")
        run.status = RunStatus.ABORTED
        if reason:
            run.checks["abort_reason"] = reason

    def get_run(self, run_id: str) -> TrajectoryRun | None:
        return self._runs.get(run_id)

    @property
    def runs(self) -> dict[str, TrajectoryRun]:
        return dict(self._runs)

    def status(self, run_id: str) -> dict[str, Any]:
        """Return a summary dict for observability."""
        run = self._runs.get(run_id)
        if run is None:
            return {"error": "unknown run"}
        return {
            "run_id": run.run_id,
            "status": run.status.value,
            "steps": len(run.steps),
            "contiguous_failures": run.contiguous_failures,
            "has_progress": run.has_progress,
            "inspected_files": len(run.inspected_files),
            "modified_files": len(run.modified_files),
            "checks": dict(run.checks),
            "assumptions": len(run.assumptions),
            "stalled": self.is_stalled(run_id),
        }

    def export_ndjson(self, run_id: str, output_path: Path) -> int:
        """Export a run's trajectory as NDJSON (from agent-trace).

        Each line is a JSON event with type, timestamp, and payload.
        Zero-dependency: no database needed, just a flat file.

        Returns the number of events written.
        """
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"unknown run_id {run_id!r}")
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with output_path.open("w", encoding="utf-8") as f:
            # Run start event
            f.write(json.dumps({
                "type": "run_start",
                "ts": run.started_at,
                "run_id": run.run_id,
                "intent": run.derived_intent or run.original_intent,
                "boundary": run.boundary,
            }) + "\n")
            count += 1
            for step in run.steps:
                event: dict[str, Any] = {
                    "type": "step",
                    "ts": step.timestamp,
                    "run_id": run.run_id,
                    "action": step.action,
                    "status": step.status.value,
                }
                if step.tool_name:
                    event["tool"] = step.tool_name
                if step.tool_input is not None:
                    event["tool_input"] = step.tool_input
                if step.tool_output is not None:
                    event["tool_output"] = step.tool_output
                if step.file:
                    event["file"] = step.file
                if step.failure_category:
                    event["failure_category"] = step.failure_category.value
                if step.metadata:
                    event["metadata"] = step.metadata
                f.write(json.dumps(event, default=str) + "\n")
                count += 1
            # Run end event
            f.write(json.dumps({
                "type": "run_end",
                "ts": time.time(),
                "run_id": run.run_id,
                "status": run.status.value,
                "total_steps": len(run.steps),
            }) + "\n")
            count += 1
        return count

    def failure_summary(self, run_id: str) -> dict[str, int]:
        """Summarize failures by category (from microsoft/AgentRx taxonomy).

        Returns a dict mapping FailureCategory.value to count.
        """
        run = self._runs.get(run_id)
        if run is None:
            return {}
        summary: dict[str, int] = {}
        for step in run.steps:
            if step.status in (StepStatus.FAILED, StepStatus.BLOCKED):
                cat = step.failure_category or FailureCategory.INCONCLUSIVE
                key = cat.value
                summary[key] = summary.get(key, 0) + 1
        return summary
