"""Coverage for drip_engine, memory/heat, managers/agent_manager."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from memory.heat import HeatScorer, _to_float, _to_timestamp
from runtime.drip_engine import DripEngine, Trigger, _as_aware
from runtime.managers.agent_manager import AgentManager
from runtime.schemas import ValidationError


class TestAsAware:
    def test_naive_to_utc(self):
        d = _as_aware(datetime(2026, 1, 1))
        assert d.tzinfo is timezone.utc

    def test_aware_passthrough(self):
        d = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert _as_aware(d) is d

    def test_non_datetime_raises(self):
        with pytest.raises(TypeError):
            _as_aware("not a datetime")
        with pytest.raises(TypeError):
            _as_aware(None)


class TestDripEngine:
    def test_add_sequence_duplicate(self):
        e = DripEngine()
        e.add_sequence("s1")
        with pytest.raises(ValidationError):
            e.add_sequence("s1")

    def test_add_step_negative_delay(self):
        e = DripEngine()
        seq = e.add_sequence("s")
        with pytest.raises(ValidationError):
            e.add_step(seq, Trigger.ON_ENTER, None, "act", delay_hours=-1)

    def test_ready_steps_flow(self):
        e = DripEngine()
        seq = e.add_sequence("s")
        step = e.add_step(seq, Trigger.ON_ENTER, None, "send_email", delay_hours=1.0)
        # not entered yet
        assert e.ready_steps() == []
        e.enter(step, now=datetime.now(timezone.utc) - timedelta(hours=2))
        ready = e.ready_steps()
        assert step in ready
        e.mark_fired(step)
        assert e.ready_steps() == []

    def test_delay_not_elapsed(self):
        e = DripEngine()
        seq = e.add_sequence("s")
        step = e.add_step(seq, Trigger.ON_ENTER, None, "a", delay_hours=5)
        e.enter(step, now=datetime.now(timezone.utc) - timedelta(hours=1))
        assert e.ready_steps() == []

    def test_condition_true_false_raising(self):
        e = DripEngine()
        seq = e.add_sequence("s")
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        s_true = e.add_step(seq, Trigger.ON_ENTER, lambda c: c.get("vip"), "a")
        s_false = e.add_step(seq, Trigger.ON_ENTER, lambda c: False, "b")
        s_raise = e.add_step(seq, Trigger.ON_ENTER, MagicMock(side_effect=RuntimeError), "c")
        for s in (s_true, s_false, s_raise):
            e.enter(s, now=past)
        ready = e.ready_steps(context={"vip": True})
        assert s_true in ready and s_false not in ready and s_raise not in ready

    def test_corrupt_entered_at_skipped(self):
        e = DripEngine()
        seq = e.add_sequence("s")
        step = e.add_step(seq, Trigger.ON_ENTER, None, "a")
        step.entered_at = "corrupt-string"  # type: ignore[assignment]
        assert e.ready_steps() == []

    def test_naive_entered_at_treated_utc(self):
        e = DripEngine()
        seq = e.add_sequence("s")
        step = e.add_step(seq, Trigger.ON_ENTER, None, "a")
        e.enter(step)
        step.entered_at = datetime.now() - timedelta(hours=10)  # naive
        assert step in e.ready_steps()

    def test_enter_now_default_and_sequence_lookup(self):
        e = DripEngine()
        seq = e.add_sequence("s")
        step = e.add_step(seq, Trigger.MANUAL, None, "a")
        e.enter(step)
        assert step.entered_at is not None
        assert e.sequence("s") is seq
        with pytest.raises(ValidationError):
            e.sequence("ghost")


class TestHeat:
    def test_to_float_variants(self):
        assert _to_float(True) == 1.0
        assert _to_float(5) == 5.0
        assert _to_float(2.5) == 2.5
        assert _to_float(" 3.5 ") == 3.5
        assert _to_float("nope") == 0.0
        assert _to_float(None) == 0.0
        assert _to_float([1]) == 0.0

    def test_to_timestamp_variants(self):
        assert _to_timestamp(None) is None
        assert _to_timestamp(True) is None
        assert _to_timestamp(100) == 100.0
        assert _to_timestamp(1.5) == 1.5
        assert _to_timestamp(" 42 ") == 42.0
        assert _to_timestamp("2026-01-01T00:00:00") is not None
        assert _to_timestamp("not-a-date") is None
        assert _to_timestamp([1]) is None

    def test_compute_bounds(self):
        s = HeatScorer()
        hot = s.compute(visit_count=10, interaction_length=500)
        cold = s.compute(visit_count=0, interaction_length=10, last_accessed=0)
        assert 0.0 <= cold < hot <= 1.0

    def test_compute_clamps(self):
        s = HeatScorer(alpha=5, beta=5, gamma=5)
        assert s.compute(visit_count=100, interaction_length=1e6) == 1.0

    def test_rank_orders_and_annotates(self):
        s = HeatScorer()
        now = time.time()
        entries = [
            {"id": "old", "visit_count": 1, "interaction_length": 10, "last_accessed": 0},
            {"id": "hot", "visit_count": "9", "interaction_length": "800", "last_accessed": now},
        ]
        ranked = s.rank(entries)
        assert ranked[0]["id"] == "hot"
        assert all("heat" in e for e in ranked)


class TestAgentManager:
    def _mgr(self, tmp_path):
        detector = MagicMock()
        return AgentManager(tmp_path, detector), detector

    def test_spawn_explicit_persona(self, tmp_path):
        mgr, _ = self._mgr(tmp_path)
        r = mgr.spawn_agent("a1", "ARCH,DEV", ["read"])
        assert r["ok"] is True
        assert r["personas"] == ["ARCH", "DEV"]
        assert r["id"] == "a1"

    def test_spawn_blank_persona_error(self, tmp_path):
        mgr, _ = self._mgr(tmp_path)
        r = mgr.spawn_agent("a1", "  , ", ["read"])
        assert r["ok"] is False
        assert "persona" in r["error"].lower()

    def test_spawn_auto_persona_detection(self, tmp_path):
        mgr, detector = self._mgr(tmp_path)
        detector.detect_multiple.return_value = {"personas": ["ARCH"], "lords": ["sec"]}
        r = mgr.spawn_agent("a1", "auto", ["read"], lords=["extra"])
        assert r["ok"] is True
        assert r["personas"] == ["ARCH"]
        assert set(r["lords"]) == {"sec", "extra"}

    def test_spawn_auto_detect_raises(self, tmp_path):
        mgr, detector = self._mgr(tmp_path)
        detector.detect_multiple.side_effect = RuntimeError("det boom")
        r = mgr.spawn_agent("a1", "auto", ["read"])
        assert r["ok"] is False
        assert "detection failed" in r["error"].lower()

    def test_spawn_auto_no_personas(self, tmp_path):
        mgr, detector = self._mgr(tmp_path)
        detector.detect_multiple.return_value = {"personas": []}
        r = mgr.spawn_agent("a1", "auto", ["read"])
        assert r["ok"] is False
        assert "no personas" in r["error"].lower()

    def test_spawn_auto_personas_not_list(self, tmp_path):
        mgr, detector = self._mgr(tmp_path)
        detector.detect_multiple.return_value = {"personas": "ARCH"}
        r = mgr.spawn_agent("a1", "generalist", ["read"])
        assert r["ok"] is False

    def test_spawn_duplicate(self, tmp_path):
        mgr, _ = self._mgr(tmp_path)
        mgr.spawn_agent("a1", "ARCH", ["read"])
        r = mgr.spawn_agent("a1", "ARCH", ["read"])
        assert r["ok"] is False
        assert "already exists" in r["error"]

    def test_spawn_invalid_id(self, tmp_path):
        mgr, _ = self._mgr(tmp_path)
        r = mgr.spawn_agent("bad id!!", "ARCH", ["read"])
        assert r["ok"] is False

    def test_spawn_non_string_scope_item(self, tmp_path):
        # scope items must be non-empty strings; a non-str item is rejected
        mgr, _ = self._mgr(tmp_path)
        r = mgr.spawn_agent("a1", "ARCH", ["read", 123])  # type: ignore[list-item]
        assert r["ok"] is False

    def test_spawn_empty_string_scope_item(self, tmp_path):
        mgr, _ = self._mgr(tmp_path)
        r = mgr.spawn_agent("a1", "ARCH", [""])
        assert r["ok"] is False

    def test_delegate_and_list(self, tmp_path):
        mgr, _ = self._mgr(tmp_path)
        mgr.spawn_agent("a1", "ARCH", ["read"])
        r = mgr.delegate("a1", "unknown_action")
        assert r["ok"] is False  # outside scope
        agents = mgr.list_agents()
        assert len(agents) == 1 and agents[0]["id"] == "a1"

    def test_health_and_respawn(self, tmp_path):
        mgr, _ = self._mgr(tmp_path)
        mgr.spawn_agent("a1", "ARCH", ["read"])
        assert mgr.check_health() == []
        assert mgr.check_agents_health() == []
        r = mgr.respawn_agent("a1")
        assert r["ok"] is True and r["respawn_count"] == 1

    def test_respawn_not_found(self, tmp_path):
        mgr, _ = self._mgr(tmp_path)
        assert mgr.respawn_agent("ghost")["ok"] is False

    def test_respawn_limit_exceeded(self, tmp_path):
        mgr, _ = self._mgr(tmp_path)
        mgr.spawn_agent("a1", "ARCH", ["read"])
        for _ in range(mgr.health.max_respawns):
            mgr.respawn_agent("a1")
        r = mgr.respawn_agent("a1")
        assert r["ok"] is False
        assert "respawn limit" in r["error"]
