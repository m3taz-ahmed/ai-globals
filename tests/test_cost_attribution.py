"""Tests for runtime/cost_attribution.py — per-agent cost + anomaly detection.

Covers: enums, dataclasses, record/aggregate, spike + budget breach
detection, set_budget, thread safety, clear.
AAA pattern, one behavior per test. FAST tier — no MCP, no kernel.
"""

from __future__ import annotations

import threading

import pytest

from runtime.cost_attribution import (
    CostAnomaly,
    CostAnomalyType,
    CostAttribution,
    CostRecord,
)

# -- enums ----------------------------------------------------------------


class TestCostAnomalyType:
    def test_values(self) -> None:
        assert CostAnomalyType.SPIKE.value == "spike"
        assert CostAnomalyType.BUDGET_BREACH.value == "budget_breach"
        assert CostAnomalyType.UNEXPECTED_PROVIDER.value == "unexpected_provider"

    def test_is_str(self) -> None:
        assert isinstance(CostAnomalyType.SPIKE, str)


# -- dataclasses ----------------------------------------------------------


class TestCostRecord:
    def test_defaults(self) -> None:
        rec = CostRecord(
            agent_id="a1", model_id="m1",
            tokens_in=10, tokens_out=5, cost_usd=1.0,
        )
        assert rec.ts == ""


class TestCostAnomaly:
    def test_defaults(self) -> None:
        anomaly = CostAnomaly(
            anomaly_type=CostAnomalyType.SPIKE,
            agent_id="a1", detail="d",
        )
        assert anomaly.severity == "high"


# -- fixtures -------------------------------------------------------------


def _rec(
    agent_id: str = "coder",
    model_id: str = "gpt-4o",
    cost: float = 1.0,
) -> CostRecord:
    return CostRecord(
        agent_id=agent_id, model_id=model_id,
        tokens_in=100, tokens_out=50, cost_usd=cost,
    )


@pytest.fixture
def ca() -> CostAttribution:
    return CostAttribution(spike_threshold=10.0)


# -- recording / aggregation ---------------------------------------------


class TestRecording:
    def test_record_returns_empty_when_no_anomaly(
        self, ca: CostAttribution,
    ) -> None:
        anomalies = ca.record(_rec(cost=1.0))
        assert anomalies == []

    def test_record_appends(self, ca: CostAttribution) -> None:
        ca.record(_rec(cost=1.0))
        ca.record(_rec(agent_id="other", cost=2.0))
        assert ca.total_cost() == 3.0

    def test_total_cost_all(self, ca: CostAttribution) -> None:
        ca.record(_rec(cost=1.0))
        ca.record(_rec(cost=2.0))
        assert ca.total_cost() == 3.0

    def test_total_cost_by_agent(self, ca: CostAttribution) -> None:
        ca.record(_rec(agent_id="a", cost=1.0))
        ca.record(_rec(agent_id="b", cost=2.0))
        assert ca.total_cost("a") == 1.0
        assert ca.total_cost("b") == 2.0

    def test_cost_by_agent(self, ca: CostAttribution) -> None:
        ca.record(_rec(agent_id="a", cost=1.0))
        ca.record(_rec(agent_id="b", cost=2.0))
        ca.record(_rec(agent_id="a", cost=3.0))
        assert ca.cost_by_agent() == {"a": 4.0, "b": 2.0}

    def test_cost_by_model(self, ca: CostAttribution) -> None:
        ca.record(_rec(model_id="m1", cost=1.0))
        ca.record(_rec(model_id="m2", cost=2.0))
        ca.record(_rec(model_id="m1", cost=3.0))
        assert ca.cost_by_model() == {"m1": 4.0, "m2": 2.0}


# -- anomaly detection ----------------------------------------------------


class TestAnomalyDetection:
    def test_record_detects_spike(self, ca: CostAttribution) -> None:
        anomalies = ca.record(_rec(cost=12.0))
        assert any(a.anomaly_type == CostAnomalyType.SPIKE for a in anomalies)

    def test_record_no_spike_below_threshold(
        self, ca: CostAttribution,
    ) -> None:
        anomalies = ca.record(_rec(cost=10.0))
        assert not any(a.anomaly_type == CostAnomalyType.SPIKE for a in anomalies)

    def test_record_detects_budget_breach(self) -> None:
        ca = CostAttribution(budget_per_agent={"coder": 5.0})
        anomalies = ca.record(_rec(cost=6.0))
        assert any(a.anomaly_type == CostAnomalyType.BUDGET_BREACH for a in anomalies)

    def test_record_no_breach_within_budget(self) -> None:
        ca = CostAttribution(budget_per_agent={"coder": 10.0})
        anomalies = ca.record(_rec(cost=5.0))
        assert not any(
            a.anomaly_type == CostAnomalyType.BUDGET_BREACH for a in anomalies
        )

    def test_detect_anomalies_full_scan_spike(self, ca: CostAttribution) -> None:
        ca.record(_rec(cost=12.0))
        ca.record(_rec(cost=1.0))
        anomalies = ca.detect_anomalies()
        assert sum(1 for a in anomalies if a.anomaly_type == CostAnomalyType.SPIKE) == 1

    def test_detect_anomalies_full_scan_breach(self) -> None:
        ca = CostAttribution(budget_per_agent={"coder": 5.0})
        ca.record(_rec(cost=3.0))
        ca.record(_rec(cost=3.0))
        anomalies = ca.detect_anomalies()
        assert any(
            a.anomaly_type == CostAnomalyType.BUDGET_BREACH for a in anomalies
        )

    def test_detect_anomalies_empty(self, ca: CostAttribution) -> None:
        assert ca.detect_anomalies() == []


# -- budgets --------------------------------------------------------------


class TestBudgets:
    def test_set_budget_then_breach(self, ca: CostAttribution) -> None:
        ca.set_budget("coder", 5.0)
        anomalies = ca.record(_rec(cost=6.0))
        assert any(
            a.anomaly_type == CostAnomalyType.BUDGET_BREACH for a in anomalies
        )

    def test_set_budget_replaces(self) -> None:
        ca = CostAttribution(budget_per_agent={"coder": 5.0})
        ca.set_budget("coder", 100.0)
        anomalies = ca.record(_rec(cost=6.0))
        assert not any(
            a.anomaly_type == CostAnomalyType.BUDGET_BREACH for a in anomalies
        )


# -- clear ----------------------------------------------------------------


class TestClear:
    def test_clear_removes_records_and_budgets(self) -> None:
        ca = CostAttribution(budget_per_agent={"coder": 5.0})
        ca.record(_rec(cost=6.0))
        ca.clear()
        assert ca.total_cost() == 0.0
        anomalies = ca.record(_rec(cost=6.0))
        assert not any(
            a.anomaly_type == CostAnomalyType.BUDGET_BREACH for a in anomalies
        )


# -- thread safety --------------------------------------------------------


class TestThreadSafety:
    def test_concurrent_records(self) -> None:
        ca = CostAttribution(spike_threshold=1_000_000.0)
        n_threads = 20
        per_thread = 50

        def worker(tid: int) -> None:
            for _i in range(per_thread):
                ca.record(_rec(agent_id=f"a{tid}", cost=1.0))

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert ca.total_cost() == n_threads * per_thread
