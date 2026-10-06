"""Tests for runtime/agent_sli.py — agent SLI collector."""

from __future__ import annotations

import pytest

from runtime.agent_sli import (
    AgentSliCollector,
    AgentSliError,
    SliName,
    SliStatus,
    TaskRecord,
)


def _task(cls="c", **kw) -> TaskRecord:
    kw.setdefault("task_id", "t")
    kw.setdefault("task_class", cls)
    kw.setdefault("completed", True)
    return TaskRecord(**kw)


def _collector(n_records=10, **task_kw) -> AgentSliCollector:
    c = AgentSliCollector(baseline_window=100)
    for i in range(n_records):
        kw = dict(task_kw)
        kw["task_id"] = f"t{i}"
        c.record(_task(**kw))
    return c


class TestInit:
    def test_window_too_small(self):
        with pytest.raises(AgentSliError, match=">= 10"):
            AgentSliCollector(baseline_window=5)

    def test_error_type(self):
        err = AgentSliError("x", {"k": 1})
        assert err.error_code == "SLI_ERROR"


class TestCollect:
    def test_empty_class(self):
        assert AgentSliCollector().collect("nothing") == []

    def test_four_slis_returned(self):
        c = _collector()
        results = c.collect("c")
        assert len(results) == 4
        names = {r.name for r in results}
        assert names == {SliName.DECISION_QUALITY_RATE, SliName.TOOL_INVOCATION_EFFICIENCY,
                         SliName.HUMAN_ESCALATION_RATE, SliName.APPROVAL_QUEUE_DEPTH_DRIFT}

    def test_to_dict(self):
        c = _collector(decision_confidence=0.9)
        d = c.collect("c")[0].to_dict()
        assert d["name"] == SliName.DECISION_QUALITY_RATE
        assert d["status"] in ("green", "yellow", "red")


class TestDQR:
    def test_all_good_green(self):
        c = _collector(decision_confidence=0.9, required_escalation=False)
        r = next(x for x in c.collect("c") if x.name == SliName.DECISION_QUALITY_RATE)
        assert r.value == 1.0 and r.status is SliStatus.GREEN

    def test_all_bad_red(self):
        c = _collector(decision_confidence=0.2)
        r = next(x for x in c.collect("c") if x.name == SliName.DECISION_QUALITY_RATE)
        assert r.value == 0.0 and r.status is SliStatus.RED

    def test_yellow_zone(self):
        c = AgentSliCollector()
        for i in range(10):
            conf = 0.9 if i < 7 else 0.3  # 70% good
            c.record(_task(task_id=f"t{i}", decision_confidence=conf))
        r = next(x for x in c.collect("c") if x.name == SliName.DECISION_QUALITY_RATE)
        assert r.status is SliStatus.YELLOW

    def test_escalation_disqualifies(self):
        c = _collector(decision_confidence=0.9, required_escalation=True)
        r = next(x for x in c.collect("c") if x.name == SliName.DECISION_QUALITY_RATE)
        assert r.value == 0.0


class TestTIE:
    def test_ratio_one_green(self):
        c = _collector(tool_calls=5)
        r = next(x for x in c.collect("c") if x.name == SliName.TOOL_INVOCATION_EFFICIENCY)
        assert r.value == 1.0 and r.status is SliStatus.GREEN

    def test_high_ratio_red(self):
        c = AgentSliCollector()
        # first half: 1 tool call (baseline); second half: 10 (drift up)
        for i in range(20):
            c.record(_task(task_id=f"t{i}", tool_calls=1 if i < 10 else 10))
        r = next(x for x in c.collect("c") if x.name == SliName.TOOL_INVOCATION_EFFICIENCY)
        assert r.value > 2.0 and r.status is SliStatus.RED

    def test_zero_baseline(self):
        c = AgentSliCollector()
        for i in range(10):
            c.record(_task(task_id=f"t{i}", tool_calls=0 if i < 5 else 5))
        r = next(x for x in c.collect("c") if x.name == SliName.TOOL_INVOCATION_EFFICIENCY)
        assert r.value == float("inf") and r.status is SliStatus.RED


class TestHER:
    def test_low_escalation_green(self):
        c = _collector(required_escalation=False)
        r = next(x for x in c.collect("c") if x.name == SliName.HUMAN_ESCALATION_RATE)
        assert r.value == 0.0 and r.status is SliStatus.GREEN

    def test_high_escalation_red(self):
        c = _collector(required_escalation=True)
        r = next(x for x in c.collect("c") if x.name == SliName.HUMAN_ESCALATION_RATE)
        assert r.value == 1.0 and r.status is SliStatus.RED

    def test_yellow_zone(self):
        c = AgentSliCollector()
        for i in range(10):
            c.record(_task(task_id=f"t{i}", required_escalation=i < 2))  # 20%
        r = next(x for x in c.collect("c") if x.name == SliName.HUMAN_ESCALATION_RATE)
        assert r.status is SliStatus.YELLOW


class TestAQDD:
    def test_no_drift_green(self):
        c = _collector(pending_approval=False)
        r = next(x for x in c.collect("c") if x.name == SliName.APPROVAL_QUEUE_DEPTH_DRIFT)
        assert r.value == 0.0 and r.status is SliStatus.GREEN

    def test_drift_red(self):
        c = AgentSliCollector()
        for i in range(10):
            c.record(_task(task_id=f"t{i}", pending_approval=i >= 5))  # 5 new pending
        r = next(x for x in c.collect("c") if x.name == SliName.APPROVAL_QUEUE_DEPTH_DRIFT)
        assert r.value == 5.0
        assert r.status is SliStatus.YELLOW  # drift == yellow threshold → <= → YELLOW


class TestThresholds:
    def test_set_threshold(self):
        c = AgentSliCollector()
        for i in range(10):  # 8 good, 2 low-confidence → DQR = 0.8 < 0.85 → YELLOW
            c.record(_task(task_id=f"t{i}", decision_confidence=0.9 if i < 8 else 0.3))
        r = next(x for x in c.collect("c") if x.name == SliName.DECISION_QUALITY_RATE)
        assert r.status is SliStatus.YELLOW
        c.set_threshold(SliName.DECISION_QUALITY_RATE, 0.75)
        r = next(x for x in c.collect("c") if x.name == SliName.DECISION_QUALITY_RATE)
        assert r.status is SliStatus.GREEN

    def test_negative_threshold(self):
        with pytest.raises(AgentSliError):
            AgentSliCollector().set_threshold("x", -1)


class TestAggregate:
    def test_breached(self):
        c = _collector(decision_confidence=0.1)  # DQR red
        assert c.breached("c") is True

    def test_not_breached(self):
        c = _collector(decision_confidence=0.95, tool_calls=2)
        assert c.breached("c") is False

    def test_breached_unknown_class(self):
        assert AgentSliCollector().breached("ghost") is False

    def test_summary(self):
        c = _collector(decision_confidence=0.9)
        c.record(_task(cls="other", decision_confidence=0.1))
        s = c.summary()
        assert set(s.keys()) == {"c", "other"}
        assert len(s["c"]) == 4
