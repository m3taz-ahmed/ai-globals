"""Gap tests for runtime/agent_baseline.py."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from runtime.agent_baseline import (
    AgentAction,
    AgentBaseline,
    AgentBaselineError,
    AnomalyType,
    BaselinePhase,
    BaselineRegistry,
)

_NOW = datetime.now(timezone.utc)


def _action(**kw) -> AgentAction:
    kw.setdefault("tool_name", "read_file")
    kw.setdefault("action_type", "read")
    kw.setdefault("timestamp", _NOW)
    return AgentAction(**kw)


def _trained(agent_id: str = "a1") -> AgentBaseline:
    b = AgentBaseline(agent_id)
    for i in range(AgentBaseline.LEARNING_THRESHOLD):
        b.observe(_action(timestamp=_NOW + timedelta(seconds=i)))
    return b


class TestBasics:
    def test_error_ctor(self):
        assert AgentBaselineError("x").error_code == "BASELINE_ERROR"

    def test_props(self):
        b = AgentBaseline("a")
        assert b.phase is BaselinePhase.LEARNING
        assert b.is_learning
        assert b.total_observations == 0

    def test_observe_with_context_fields(self):
        b = AgentBaseline("a")
        b.observe(_action(data_source="db", endpoint="https://x", task_context="deploy"))
        assert b.total_observations == 1
        assert "deploy" in b._task_context_counts

    def test_timestamp_trim(self):
        b = AgentBaseline("a")
        cutoff = AgentBaseline.VOLUME_SPIKE_WINDOW * 3
        for i in range(cutoff + 5):
            b.observe(_action(timestamp=_NOW + timedelta(seconds=i)))
        assert len(b._recent_timestamps) == cutoff

    def test_learning_check_returns_none(self):
        b = AgentBaseline("a")
        assert b.check(_action(tool_name="brand_new")) is None

    def test_to_dict(self):
        b = _trained()
        alert = b.check(_action(tool_name="never_seen"))
        assert alert is not None
        d = alert.to_dict()
        assert d["anomaly_type"] == AnomalyType.NEW_TOOL.value
        assert d["action"]["tool_name"] == "never_seen"


class TestAnomalyChecks:
    def test_new_data_source(self):
        b = _trained()
        alert = b.check(_action(data_source="secret_db"))
        assert alert is not None
        assert alert.anomaly_type is AnomalyType.NEW_DATA_SOURCE

    def test_new_endpoint(self):
        b = _trained()
        alert = b.check(_action(endpoint="https://evil.example"))
        assert alert is not None
        assert alert.anomaly_type is AnomalyType.NEW_ENDPOINT

    def test_rare_action(self):
        b = _trained()
        # train with a rare action type (1/20 < 5%? need <5%: train 21+)
        b.observe(_action(action_type="exec"))
        alert = b.check(_action(action_type="exec"))
        assert alert is not None
        assert alert.anomaly_type is AnomalyType.RARE_ACTION

    def test_normal_action_no_alert(self):
        b = _trained()
        assert b.check(_action()) is None

    def test_volume_spike_insufficient_data(self):
        b = _trained()
        b._recent_timestamps = b._recent_timestamps[:5]
        assert b._check_volume_spike(_action()) is None

    def test_volume_spike_exception_returns_none(self):
        b = _trained()
        # non-subtractable timestamps -> caught -> None
        b._recent_timestamps = [object()] * 15  # type: ignore[list-item]
        assert b._check_volume_spike(_action()) is None

    def test_volume_spike_zero_span(self):
        b = _trained()
        b._recent_timestamps = [_NOW] * 15  # identical -> zero spans
        assert b._check_volume_spike(_action()) is None

    def test_volume_spike_fires(self):
        b = _trained()
        # long history spread over time, then a fast burst
        base = _NOW - timedelta(hours=10)
        b._recent_timestamps = [base + timedelta(hours=i) for i in range(20)]
        b._recent_timestamps += [base + timedelta(hours=20, seconds=i * 0.001) for i in range(10)]
        alert = b._check_volume_spike(_action())
        assert alert is not None
        assert alert.anomaly_type is AnomalyType.VOLUME_SPIKE
        assert alert.is_anomalous

    def test_check_returns_spike_alert(self):
        b = _trained()
        base = _NOW - timedelta(hours=10)
        b._recent_timestamps = [base + timedelta(hours=i) for i in range(20)]
        b._recent_timestamps += [base + timedelta(hours=20, seconds=i * 0.001) for i in range(10)]
        alert = b.check(_action())
        assert alert is not None
        assert alert.anomaly_type is AnomalyType.VOLUME_SPIKE

    def test_stats(self):
        b = _trained()
        s = b.stats()
        assert s["phase"] == "detecting"
        assert s["unique_tools"] == 1


class TestRegistry:
    def test_unknown_agent_creates_and_returns_none(self):
        reg = BaselineRegistry()
        assert reg.check("ghost", _action()) is None
        assert "ghost" in reg._baselines

    def test_known_agent_delegates(self):
        reg = BaselineRegistry()
        reg.observe("a", _action())
        assert reg.check("a", _action()) is None  # learning

    def test_all_stats(self):
        reg = BaselineRegistry()
        reg.observe("a", _action())
        reg.observe("b", _action())
        out = reg.all_stats()
        assert set(out) == {"a", "b"}
