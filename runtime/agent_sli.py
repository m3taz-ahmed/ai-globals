#!/usr/bin/env python3
"""Agent-specific Service Level Indicators (SLIs).

Inspired by agentsre: tracks decision quality, tool invocation efficiency,
human escalation rate, and approval queue depth drift for agent task classes.

These SLIs measure *agent behavior quality*, not infrastructure health.
A green dashboard means agents are making good decisions, using tools
efficiently, not over-escalating to humans, and not building up approval
backlogs.

Architecture::

    task completion -> AgentSliCollector.record(task)
                    -> accumulates per-task-class records
    collect(task_class) -> list[SliResult]  (4 SLIs)
    breached(task_class) -> bool  (any SLI is RED)

Usage::

    from runtime.agent_sli import AgentSliCollector, TaskRecord

    collector = AgentSliCollector(baseline_window=100)
    collector.record(TaskRecord(
        task_id="t1", task_class="research",
        tool_calls=3, required_escalation=False,
        pending_approval=False, decision_confidence=0.85,
        completed=True, timestamp=time.time(),
    ))
    results = collector.collect("research")
    if collector.breached("research"):
        logger.warning("research agent SLIs breached")
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from statistics import median
from typing import Any, ClassVar

from runtime.schemas import AizeeError, ErrorSeverity

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SliStatus(str, Enum):
    """Health status for a single SLI measurement."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TaskRecord:
    """A single completed (or in-flight) agent task for SLI tracking.

    Attributes:
        task_id: Unique identifier for the task.
        task_class: Category of task (e.g. "research", "coding", "review").
        tool_calls: Number of tool invocations made during this task.
        required_escalation: Whether the task required human escalation.
        pending_approval: Whether the task is waiting for human approval.
        decision_confidence: Agent's self-reported confidence (0.0 to 1.0).
        completed: Whether the task has finished.
        timestamp: Unix timestamp when the task was recorded.
    """

    task_id: str
    task_class: str
    tool_calls: int = 0
    required_escalation: bool = False
    pending_approval: bool = False
    decision_confidence: float = 0.0
    completed: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class SliResult:
    """Result of a single SLI measurement.

    Attributes:
        name: SLI name (e.g. "DecisionQualityRate").
        task_class: Which task class this measurement belongs to.
        value: The measured value (0.0 to 1.0 for rates, raw counts otherwise).
        status: GREEN / YELLOW / RED based on threshold comparison.
        threshold: The threshold used for status determination.
        description: Human-readable explanation of the measurement.
    """

    name: str
    task_class: str
    value: float
    status: SliStatus
    threshold: float
    description: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for logging/API responses."""
        return {
            "name": self.name,
            "task_class": self.task_class,
            "value": round(self.value, 4),
            "status": self.status.value,
            "threshold": self.threshold,
            "description": self.description,
        }


class AgentSliError(AizeeError):
    """Raised when the SLI collector encounters an error."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("SLI_ERROR", message, ErrorSeverity.MEDIUM, context)


# ---------------------------------------------------------------------------
# SLI name constants
# ---------------------------------------------------------------------------


class SliName:
    """Canonical SLI names to avoid magic strings."""

    DECISION_QUALITY_RATE = "DecisionQualityRate"
    TOOL_INVOCATION_EFFICIENCY = "ToolInvocationEfficiency"
    HUMAN_ESCALATION_RATE = "HumanEscalationRate"
    APPROVAL_QUEUE_DEPTH_DRIFT = "ApprovalQueueDepthDrift"


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------


class AgentSliCollector:
    """Collects and computes agent-specific SLIs per task class.

    Maintains a rolling window of task records per task class. After enough
    records accumulate, computes four SLIs:

    1. **DecisionQualityRate (DQR)**: percentage of tasks with
       ``decision_confidence > 0.7`` AND no escalation required.
    2. **ToolInvocationEfficiency (TIE)**: median tool_calls per task,
       compared against the baseline median. A value above 1.0 means the
       agent is using *more* tools than baseline (worse efficiency).
    3. **HumanEscalationRate (HER)**: percentage of tasks requiring
       human escalation.
    4. **ApprovalQueueDepthDrift (AQDD)**: current pending-approval count
       vs the baseline pending-approval count.

    Thread-safe via an ``RLock`` so concurrent ``record()`` and
    ``collect()`` calls are safe.
    """

    DQR_CONFIDENCE_THRESHOLD: ClassVar[float] = 0.7
    DQR_GREEN_THRESHOLD: ClassVar[float] = 0.85
    DQR_YELLOW_THRESHOLD: ClassVar[float] = 0.70

    TIE_GREEN_THRESHOLD: ClassVar[float] = 1.2
    TIE_YELLOW_THRESHOLD: ClassVar[float] = 2.0

    HER_GREEN_THRESHOLD: ClassVar[float] = 0.10
    HER_YELLOW_THRESHOLD: ClassVar[float] = 0.25

    AQDD_GREEN_THRESHOLD: ClassVar[float] = 2.0
    AQDD_YELLOW_THRESHOLD: ClassVar[float] = 5.0

    def __init__(self, baseline_window: int = 100) -> None:
        if baseline_window < 10:
            raise AgentSliError(
                "baseline_window must be >= 10",
                context={"provided": baseline_window},
            )
        self._baseline_window = baseline_window
        self._records: dict[str, deque[TaskRecord]] = defaultdict(
            lambda: deque(maxlen=baseline_window)
        )
        self._thresholds: dict[str, float] = {}
        self._lock = threading.RLock()

    def record(self, task: TaskRecord) -> None:
        """Record a completed or in-flight task.

        Args:
            task: The task record to store.
        """
        with self._lock:
            self._records[task.task_class].append(task)
        _logger.debug(
            "recorded task %s for class %s (confidence=%.2f, tools=%d)",
            task.task_id,
            task.task_class,
            task.decision_confidence,
            task.tool_calls,
        )

    def collect(self, task_class: str) -> list[SliResult]:
        """Compute all four SLIs for the given task class.

        Returns an empty list if no records exist for the task class.
        """
        with self._lock:
            records = list(self._records.get(task_class, ()))
        if not records:
            return []
        return [
            self._compute_dqr(task_class, records),
            self._compute_tie(task_class, records),
            self._compute_her(task_class, records),
            self._compute_aqdd(task_class, records),
        ]

    def breached(self, task_class: str) -> bool:
        """Return True if any SLI for the task class is RED."""
        results = self.collect(task_class)
        return any(r.status is SliStatus.RED for r in results)

    def summary(self) -> dict[str, Any]:
        """Return all SLIs for all task classes as a nested dict."""
        with self._lock:
            classes = list(self._records.keys())
        return {
            cls: [r.to_dict() for r in self.collect(cls)]
            for cls in classes
        }

    def set_threshold(self, sli_name: str, value: float) -> None:
        """Override the default threshold for a named SLI.

        This replaces the green/yellow boundary for the given SLI name.
        The yellow/red boundary remains at the default.
        """
        if value < 0:
            raise AgentSliError(
                "threshold must be non-negative",
                context={"sli_name": sli_name, "value": value},
            )
        with self._lock:
            self._thresholds[sli_name] = value

    # -- SLI computation helpers (each < 30 lines) ---------------------------

    def _compute_dqr(
        self, task_class: str, records: list[TaskRecord]
    ) -> SliResult:
        """Decision Quality Rate: % of tasks with confidence > 0.7 and no escalation."""
        total = len(records)
        good = sum(
            1
            for r in records
            if r.decision_confidence > self.DQR_CONFIDENCE_THRESHOLD
            and not r.required_escalation
        )
        rate = good / total if total > 0 else 0.0
        threshold = self._thresholds.get(
            SliName.DECISION_QUALITY_RATE, self.DQR_GREEN_THRESHOLD
        )
        status = self._rate_status(rate, threshold, self.DQR_YELLOW_THRESHOLD)
        return SliResult(
            name=SliName.DECISION_QUALITY_RATE,
            task_class=task_class,
            value=rate,
            status=status,
            threshold=threshold,
            description=f"{good}/{total} tasks had high confidence and no escalation",
        )

    def _compute_tie(
        self, task_class: str, records: list[TaskRecord]
    ) -> SliResult:
        """Tool Invocation Efficiency: median tool_calls vs baseline median."""
        calls = [r.tool_calls for r in records]
        if not calls:
            return self._empty_tie(task_class)
        current_median = float(median(calls))
        baseline = self._baseline_median(calls)
        if baseline <= 0:
            ratio = 0.0 if current_median == 0 else float("inf")
        else:
            ratio = current_median / baseline
        threshold = self._thresholds.get(
            SliName.TOOL_INVOCATION_EFFICIENCY, self.TIE_GREEN_THRESHOLD
        )
        status = self._ratio_status(ratio, threshold, self.TIE_YELLOW_THRESHOLD)
        return SliResult(
            name=SliName.TOOL_INVOCATION_EFFICIENCY,
            task_class=task_class,
            value=ratio,
            status=status,
            threshold=threshold,
            description=f"median {current_median} tools/task vs baseline {baseline}",
        )

    def _compute_her(
        self, task_class: str, records: list[TaskRecord]
    ) -> SliResult:
        """Human Escalation Rate: % of tasks requiring escalation."""
        total = len(records)
        escalated = sum(1 for r in records if r.required_escalation)
        rate = escalated / total if total > 0 else 0.0
        threshold = self._thresholds.get(
            SliName.HUMAN_ESCALATION_RATE, self.HER_GREEN_THRESHOLD
        )
        status = self._rate_status(
            rate, threshold, self.HER_YELLOW_THRESHOLD, invert=True
        )
        return SliResult(
            name=SliName.HUMAN_ESCALATION_RATE,
            task_class=task_class,
            value=rate,
            status=status,
            threshold=threshold,
            description=f"{escalated}/{total} tasks required human escalation",
        )

    def _compute_aqdd(
        self, task_class: str, records: list[TaskRecord]
    ) -> SliResult:
        """Approval Queue Depth Drift: pending approvals vs baseline."""
        current_pending = sum(1 for r in records if r.pending_approval)
        baseline = self._baseline_pending(records)
        drift = float(current_pending - baseline)
        threshold = self._thresholds.get(
            SliName.APPROVAL_QUEUE_DEPTH_DRIFT, self.AQDD_GREEN_THRESHOLD
        )
        status = self._drift_status(drift, threshold, self.AQDD_YELLOW_THRESHOLD)
        return SliResult(
            name=SliName.APPROVAL_QUEUE_DEPTH_DRIFT,
            task_class=task_class,
            value=drift,
            status=status,
            threshold=threshold,
            description=f"{current_pending} pending vs baseline {baseline}",
        )

    # -- Status determination helpers ----------------------------------------

    @staticmethod
    def _rate_status(
        rate: float,
        green_threshold: float,
        yellow_threshold: float,
        invert: bool = False,
    ) -> SliStatus:
        """Determine status for rate-based SLIs (higher-is-better by default).

        When ``invert`` is True, the SLI is lower-is-better (e.g. escalation
        rate): values below green_threshold are GREEN, above yellow are RED.
        """
        if invert:
            if rate <= green_threshold:
                return SliStatus.GREEN
            if rate <= yellow_threshold:
                return SliStatus.YELLOW
            return SliStatus.RED
        if rate >= green_threshold:
            return SliStatus.GREEN
        if rate >= yellow_threshold:
            return SliStatus.YELLOW
        return SliStatus.RED

    @staticmethod
    def _ratio_status(
        ratio: float,
        green_threshold: float,
        yellow_threshold: float,
    ) -> SliStatus:
        """Determine status for ratio-based SLIs (lower-is-better)."""
        if ratio <= green_threshold:
            return SliStatus.GREEN
        if ratio <= yellow_threshold:
            return SliStatus.YELLOW
        return SliStatus.RED

    @staticmethod
    def _drift_status(
        drift: float,
        green_threshold: float,
        yellow_threshold: float,
    ) -> SliStatus:
        """Determine status for drift-based SLIs (lower-is-better)."""
        if drift <= green_threshold:
            return SliStatus.GREEN
        if drift <= yellow_threshold:
            return SliStatus.YELLOW
        return SliStatus.RED

    # -- Baseline helpers ---------------------------------------------------

    def _baseline_median(self, calls: list[int]) -> float:
        """Compute baseline median from the first half of the window.

        This gives a stable reference point: as the window slides, the
        baseline reflects earlier behavior and the current median reflects
        recent behavior, so the ratio detects drift.
        """
        half = len(calls) // 2
        if half < 1:
            return float(median(calls)) if calls else 0.0
        return float(median(calls[:half]))

    def _baseline_pending(self, records: list[TaskRecord]) -> int:
        """Compute baseline pending-approval count from the first half."""
        half = len(records) // 2
        if half < 1:
            return sum(1 for r in records if r.pending_approval)
        return sum(1 for r in records[:half] if r.pending_approval)

    def _empty_tie(self, task_class: str) -> SliResult:
        """Return a neutral TIE result when no data is available."""
        return SliResult(
            name=SliName.TOOL_INVOCATION_EFFICIENCY,
            task_class=task_class,
            value=0.0,
            status=SliStatus.GREEN,
            threshold=self.TIE_GREEN_THRESHOLD,
            description="no tool call data available",
        )
