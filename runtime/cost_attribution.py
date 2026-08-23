"""Per-agent cost attribution with budget anomaly detection.

Inspired by FINOPS persona + Databricks cost allocation: every cost
record is tagged with its agent and model, then aggregated per agent
and per model. Anomalies (spikes, budget breaches, unexpected
providers) are detected on record and on demand.

Usage::

    from runtime.cost_attribution import CostAttribution, CostRecord

    ca = CostAttribution(budget_per_agent={"coder": 5.0}, spike_threshold=10.0)
    anomalies = ca.record(CostRecord(
        agent_id="coder", model_id="gpt-4o",
        tokens_in=1000, tokens_out=500, cost_usd=12.0,
    ))
    assert any(a.anomaly_type == CostAnomalyType.SPIKE for a in anomalies)
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity


class CostAttributionError(AizeeError):
    """Raised when cost attribution encounters an error."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("COST_ATTRIBUTION_ERROR", message, ErrorSeverity.HIGH, context)


class CostAnomalyType(str, Enum):
    """Kinds of cost anomalies the detector can surface."""

    SPIKE = "spike"
    BUDGET_BREACH = "budget_breach"
    UNEXPECTED_PROVIDER = "unexpected_provider"


@dataclass
class CostRecord:
    """A single cost event tagged with agent and model."""

    agent_id: str
    model_id: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    ts: str = ""


@dataclass
class CostAnomaly:
    """A detected cost anomaly."""

    anomaly_type: CostAnomalyType
    agent_id: str
    detail: str
    severity: str = "high"


class CostAttribution:
    """Thread-safe per-agent cost tracker with anomaly detection.

    Records are stored in insertion order. Aggregations are computed
    on demand from the record list. Budgets are per-agent USD caps.
    """

    def __init__(
        self,
        budget_per_agent: dict[str, float] | None = None,
        spike_threshold: float = 10.0,
    ) -> None:
        self._lock = threading.RLock()
        self._records: list[CostRecord] = []
        self._budgets: dict[str, float] = dict(budget_per_agent or {})
        self._spike_threshold = spike_threshold

    # -- recording -------------------------------------------------------

    def record(self, rec: CostRecord) -> list[CostAnomaly]:
        """Append a cost record and return anomalies it triggered."""
        if rec.cost_usd < 0:
            raise CostAttributionError("Cost cannot be negative", context={"agent_id": rec.agent_id, "cost": rec.cost_usd})
        with self._lock:
            self._records.append(rec)
            return self._detect_for_record(rec)

    def _detect_for_record(self, rec: CostRecord) -> list[CostAnomaly]:
        """Detect anomalies caused by a single newly-added record."""
        anomalies: list[CostAnomaly] = []
        if rec.cost_usd > self._spike_threshold:
            anomalies.append(CostAnomaly(
                anomaly_type=CostAnomalyType.SPIKE,
                agent_id=rec.agent_id,
                detail=(
                    f"single record cost {rec.cost_usd} exceeds "
                    f"spike threshold {self._spike_threshold}"
                ),
            ))
        budget = self._budgets.get(rec.agent_id)
        if budget is not None:
            agent_total = sum(
                r.cost_usd for r in self._records if r.agent_id == rec.agent_id
            )
            if agent_total > budget:
                anomalies.append(CostAnomaly(
                    anomaly_type=CostAnomalyType.BUDGET_BREACH,
                    agent_id=rec.agent_id,
                    detail=(
                        f"agent total {agent_total} exceeds "
                        f"budget {budget}"
                    ),
                ))
        return anomalies

    # -- aggregation -----------------------------------------------------

    def total_cost(self, agent_id: str | None = None) -> float:
        """Total cost, optionally filtered by agent."""
        with self._lock:
            if agent_id is None:
                return sum(r.cost_usd for r in self._records)
            return sum(
                r.cost_usd for r in self._records if r.agent_id == agent_id
            )

    def cost_by_agent(self) -> dict[str, float]:
        """Aggregate cost grouped by agent_id."""
        with self._lock:
            out: dict[str, float] = {}
            for r in self._records:
                out[r.agent_id] = out.get(r.agent_id, 0.0) + r.cost_usd
            return out

    def cost_by_model(self) -> dict[str, float]:
        """Aggregate cost grouped by model_id."""
        with self._lock:
            out: dict[str, float] = {}
            for r in self._records:
                out[r.model_id] = out.get(r.model_id, 0.0) + r.cost_usd
            return out

    # -- anomaly detection ----------------------------------------------

    def detect_anomalies(self) -> list[CostAnomaly]:
        """Detect all anomalies across the full record set."""
        with self._lock:
            anomalies: list[CostAnomaly] = []
            for r in self._records:
                if r.cost_usd > self._spike_threshold:
                    anomalies.append(CostAnomaly(
                        anomaly_type=CostAnomalyType.SPIKE,
                        agent_id=r.agent_id,
                        detail=(
                            f"single record cost {r.cost_usd} exceeds "
                            f"spike threshold {self._spike_threshold}"
                        ),
                    ))
            for agent_id, budget in self._budgets.items():
                agent_total = sum(
                    r.cost_usd for r in self._records if r.agent_id == agent_id
                )
                if agent_total > budget:
                    anomalies.append(CostAnomaly(
                        anomaly_type=CostAnomalyType.BUDGET_BREACH,
                        agent_id=agent_id,
                        detail=(
                            f"agent total {agent_total} exceeds "
                            f"budget {budget}"
                        ),
                    ))
            return anomalies

    # -- budgets ---------------------------------------------------------

    def set_budget(self, agent_id: str, budget_usd: float) -> None:
        """Set or replace the USD budget for an agent."""
        with self._lock:
            self._budgets[agent_id] = budget_usd

    # -- maintenance -----------------------------------------------------

    def clear(self) -> None:
        """Remove all records and budgets."""
        with self._lock:
            self._records.clear()
            self._budgets.clear()


__all__ = [
    "CostAnomaly",
    "CostAnomalyType",
    "CostAttribution",
    "CostRecord",
]
