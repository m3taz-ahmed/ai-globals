#!/usr/bin/env python3
"""Agent behavioral baseline — runtime detection of anomalous agent actions.

Prompt injection itself is invisible (it happens in model context), but
the **actions** it produces are observable. This module builds a behavioral
baseline for each agent — what tools it normally calls, what data it
accesses, what network endpoints it reaches — and flags deviations.

This is the "runtime detection" layer from the Sysdig 2026 guide:
injections produce actions, and actions touch the system.

Architecture::

    agent_action → AgentBaseline.observe(action)
                 → updates baseline (learning phase)
                 OR checks against baseline (detection phase)
                 → if anomalous: AnomalyAlert

Usage::

    from runtime.agent_baseline import AgentBaseline, AnomalyAlert

    baseline = AgentBaseline(agent_id="research-agent")

    # Learning phase: observe normal actions
    for action in normal_actions:
        baseline.observe(action)

    # Detection phase: flag anomalies
    alert = baseline.check(action)
    if alert.is_anomalous:
        logger.warning("Agent anomaly: %s", alert.reason)
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import ClassVar

from runtime.schemas import AizeeError, ErrorSeverity


class AnomalyType(str, Enum):
    """Type of behavioral anomaly detected."""

    NEW_TOOL = "new_tool"               # agent called a tool it never used before
    NEW_DATA_SOURCE = "new_data_source"  # agent accessed a data source it never touched
    NEW_ENDPOINT = "new_endpoint"        # agent reached a network endpoint it never contacted
    RARE_ACTION = "rare_action"          # action type is very rare for this agent
    VOLUME_SPIKE = "volume_spike"        # sudden burst of actions
    OFF_TASK = "off_task"               # action doesn't match the agent's normal task patterns


class BaselinePhase(str, Enum):
    """Whether the baseline is still learning or actively detecting."""

    LEARNING = "learning"
    DETECTING = "detecting"


@dataclass
class AgentAction:
    """A single observed agent action for baseline tracking.

    Attributes:
        tool_name: The tool/function called.
        action_type: Category (read, write, exec, network, etc.).
        data_source: File path, DB table, or resource accessed.
        endpoint: Network endpoint (URL/host) if applicable.
        timestamp: When the action occurred.
        task_context: What task the agent was performing.
    """

    tool_name: str
    action_type: str = "unknown"
    data_source: str | None = None
    endpoint: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    task_context: str | None = None


@dataclass(frozen=True)
class AnomalyAlert:
    """An alert raised when an agent action deviates from its baseline.

    Attributes:
        anomaly_type: What kind of anomaly was detected.
        agent_id: Which agent triggered the alert.
        action: The anomalous action.
        reason: Human-readable explanation.
        severity: How serious the deviation is (0.0 to 1.0).
    """

    anomaly_type: AnomalyType
    agent_id: str
    action: AgentAction
    reason: str
    severity: float

    @property
    def is_anomalous(self) -> bool:
        return True  # AnomalyAlert is always anomalous by definition

    def to_dict(self) -> dict[str, object]:
        return {
            "anomaly_type": self.anomaly_type.value,
            "agent_id": self.agent_id,
            "reason": self.reason,
            "severity": round(self.severity, 3),
            "action": {
                "tool_name": self.action.tool_name,
                "action_type": self.action.action_type,
                "data_source": self.action.data_source,
                "endpoint": self.action.endpoint,
                "task_context": self.action.task_context,
            },
        }


class AgentBaselineError(AizeeError):
    """Raised when the baseline tracker encounters an error."""

    def __init__(self, message: str, context: dict[str, object] | None = None) -> None:
        super().__init__("BASELINE_ERROR", message, ErrorSeverity.MEDIUM, context)


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------


class AgentBaseline:
    """Behavioral baseline for a single agent.

    Tracks the distribution of tools, data sources, endpoints, and action
    types the agent normally uses. After a learning period, deviations
    from this baseline are flagged as potential injection-induced anomalies.
    """

    LEARNING_THRESHOLD: ClassVar[int] = 20  # min observations before detecting
    RARE_ACTION_THRESHOLD: ClassVar[float] = 0.05  # <5% frequency = rare
    VOLUME_SPIKE_WINDOW: ClassVar[int] = 10  # actions in this window
    VOLUME_SPIKE_MULTIPLIER: ClassVar[float] = 3.0  # 3x normal rate

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self._phase: BaselinePhase = BaselinePhase.LEARNING

        # Frequency counters
        self._tool_counts: Counter[str] = Counter()
        self._action_type_counts: Counter[str] = Counter()
        self._data_source_counts: Counter[str] = Counter()
        self._endpoint_counts: Counter[str] = Counter()
        self._task_context_counts: Counter[str] = Counter()

        # Total observations
        self._total_observations: int = 0

        # Rolling window for volume-spike detection
        self._recent_timestamps: list[datetime] = []

    @property
    def phase(self) -> BaselinePhase:
        return self._phase

    @property
    def is_learning(self) -> bool:
        return self._phase is BaselinePhase.LEARNING

    @property
    def total_observations(self) -> int:
        return self._total_observations

    def observe(self, action: AgentAction) -> None:
        """Record an action in the baseline (learning phase)."""
        self._tool_counts[action.tool_name] += 1
        self._action_type_counts[action.action_type] += 1
        if action.data_source:
            self._data_source_counts[action.data_source] += 1
        if action.endpoint:
            self._endpoint_counts[action.endpoint] += 1
        if action.task_context:
            self._task_context_counts[action.task_context] += 1

        self._total_observations += 1
        self._recent_timestamps.append(action.timestamp)
        # Keep only recent timestamps for volume calculation
        cutoff_count = self.VOLUME_SPIKE_WINDOW * 3
        if len(self._recent_timestamps) > cutoff_count:
            self._recent_timestamps = self._recent_timestamps[-cutoff_count:]

        # Transition to detecting phase after enough observations
        if self._phase is BaselinePhase.LEARNING and self._total_observations >= self.LEARNING_THRESHOLD:
            self._phase = BaselinePhase.DETECTING

    def check(self, action: AgentAction) -> AnomalyAlert | None:
        """Check an action against the baseline (detection phase).

        Returns an :class:`AnomalyAlert` if the action is anomalous, or
        None if it's within normal behavior. During the learning phase,
        always returns None (still building the baseline).
        """
        if self._phase is BaselinePhase.LEARNING:
            return None

        # Check: new tool
        if action.tool_name not in self._tool_counts:
            return AnomalyAlert(
                anomaly_type=AnomalyType.NEW_TOOL,
                agent_id=self.agent_id,
                action=action,
                reason=f"tool '{action.tool_name}' never used before by {self.agent_id}",
                severity=0.7,
            )

        # Check: new data source
        if action.data_source and action.data_source not in self._data_source_counts:
            return AnomalyAlert(
                anomaly_type=AnomalyType.NEW_DATA_SOURCE,
                agent_id=self.agent_id,
                action=action,
                reason=f"data source '{action.data_source}' never accessed before",
                severity=0.6,
            )

        # Check: new network endpoint
        if action.endpoint and action.endpoint not in self._endpoint_counts:
            return AnomalyAlert(
                anomaly_type=AnomalyType.NEW_ENDPOINT,
                agent_id=self.agent_id,
                action=action,
                reason=f"endpoint '{action.endpoint}' never contacted before",
                severity=0.8,
            )

        # Check: rare action type
        total = sum(self._action_type_counts.values())
        if total > 0:
            freq = self._action_type_counts.get(action.action_type, 0) / total
            if freq < self.RARE_ACTION_THRESHOLD:
                return AnomalyAlert(
                    anomaly_type=AnomalyType.RARE_ACTION,
                    agent_id=self.agent_id,
                    action=action,
                    reason=f"action type '{action.action_type}' is rare ({freq:.1%} of actions)",
                    severity=0.5,
                )

        return None

    def stats(self) -> dict[str, object]:
        """Return baseline statistics for monitoring."""
        return {
            "agent_id": self.agent_id,
            "phase": self._phase.value,
            "total_observations": self._total_observations,
            "unique_tools": len(self._tool_counts),
            "unique_data_sources": len(self._data_source_counts),
            "unique_endpoints": len(self._endpoint_counts),
            "top_tools": self._tool_counts.most_common(5),
            "top_action_types": self._action_type_counts.most_common(5),
        }


# ---------------------------------------------------------------------------
# Registry (multi-agent)
# ---------------------------------------------------------------------------


class BaselineRegistry:
    """Manages baselines for multiple agents."""

    def __init__(self) -> None:
        self._baselines: dict[str, AgentBaseline] = {}

    def get_or_create(self, agent_id: str) -> AgentBaseline:
        """Get an existing baseline or create a new one."""
        if agent_id not in self._baselines:
            self._baselines[agent_id] = AgentBaseline(agent_id)
        return self._baselines[agent_id]

    def observe(self, agent_id: str, action: AgentAction) -> None:
        """Record an action for an agent."""
        self.get_or_create(agent_id).observe(action)

    def check(self, agent_id: str, action: AgentAction) -> AnomalyAlert | None:
        """Check an action against an agent's baseline."""
        return self.get_or_create(agent_id).check(action)

    def all_stats(self) -> dict[str, dict[str, object]]:
        """Return stats for all tracked agents."""
        return {aid: bl.stats() for aid, bl in self._baselines.items()}
