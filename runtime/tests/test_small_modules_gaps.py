"""Gap tests for small/medium runtime modules: feature_flags, pipeline_analytics,
heat, agent_manager, crm transitions, blade linter, filament auditor,
local_responder, drip_engine, context_manager."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest

from memory.heat import HeatScorer, _to_float, _to_timestamp
from runtime.blade_template_linter import BladeTemplateLinter
from runtime.context_manager import ContextManager, Message, Role, compress_with_llm
from runtime.crm_manager import (
    Opportunity,
    OpportunityStage,
    Task,
    TaskStage,
)
from runtime.drip_engine import DripEngine, Trigger, _as_aware
from runtime.feature_flags import FeatureFlagger
from runtime.filament_access_auditor import FilamentAccessAuditor
from runtime.local_responder import LocalResponder
from runtime.managers.agent_manager import AgentManager
from runtime.persona import PersonaDetector
from runtime.pipeline_analytics import PipelineAnalytics
from runtime.schemas import ValidationError


class TestFeatureFlags:
    def setup_method(self):
        self.ff = FeatureFlagger()

    def test_none_segments(self):
        # rollout 100 → everyone in
        assert self.ff.evaluate("f", "u1", None, 100) is True

    def test_segments_not_dict(self):
        with pytest.raises(ValidationError):
            self.ff.evaluate("f", "u", "nope", 50)

    def test_rollout_out_of_range(self):
        with pytest.raises(ValidationError):
            self.ff.evaluate("f", "u", {}, 101)

    def test_seg_cfg_none(self):
        assert self.ff.evaluate("f", "u", {"s": None}, 0) is False

    def test_seg_cfg_not_dict(self):
        with pytest.raises(ValidationError):
            self.ff.evaluate("f", "u", {"s": 42}, 0)

    def test_ids_list_match(self):
        assert self.ff.evaluate("f", "u1", {"s": {"ids": ["u1", "u2"]}}, 0) is True

    def test_ids_str_match(self):
        assert self.ff.evaluate("f", "u1", {"s": {"ids": "u1"}}, 0) is True

    def test_seg_pct_non_int(self):
        with pytest.raises(ValidationError):
            self.ff.evaluate("f", "u", {"s": {"pct": "50"}}, 0)

    def test_seg_pct_bool(self):
        with pytest.raises(ValidationError):
            self.ff.evaluate("f", "u", {"s": {"pct": True}}, 0)

    def test_seg_pct_out_of_range(self):
        with pytest.raises(ValidationError):
            self.ff.evaluate("f", "u", {"s": {"pct": 200}}, 0)

    def test_seg_pct_100_match(self):
        assert self.ff.evaluate("f", "anyone", {"s": {"pct": 100}}, 0) is True

    def test_global_rollout_zero(self):
        assert self.ff.evaluate("f", "u", {}, 0) is False


class TestPipelineAnalytics:
    def test_won_not_bool(self):
        with pytest.raises(ValidationError):
            PipelineAnalytics().record_bid("up", "web", 100, "yes")

    def test_amount_not_number(self):
        with pytest.raises(ValidationError):
            PipelineAnalytics().record_bid("up", "web", "abc", True)

    def test_amount_negative(self):
        with pytest.raises(ValidationError):
            PipelineAnalytics().record_bid("up", "web", -5, True)

    def test_amount_nan(self):
        with pytest.raises(ValidationError):
            PipelineAnalytics().record_bid("up", "web", float("inf"), True)

    def test_win_rate_filters(self):
        pa = PipelineAnalytics()
        pa.record_bid("upwork", "web", 100, True)
        pa.record_bid("upwork", "web", 100, False)
        pa.record_bid("fiverr", "seo", 50, None)  # pending - excluded
        pa.record_bid("fiverr", "seo", 50, True)
        assert pa.win_rate() == pytest.approx(2 / 3)
        assert pa.win_rate(platform="upwork") == pytest.approx(0.5)
        assert pa.win_rate(niche="seo") == pytest.approx(1.0)
        assert pa.win_rate(platform="nobody") == 0.0

    def test_proposal_ab_winner(self):
        pa = PipelineAnalytics()
        assert pa.proposal_ab_winner() is None
        pa.record_proposal_variant("A", True)
        pa.record_proposal_variant("A", True)
        pa.record_proposal_variant("B", False)
        assert pa.proposal_ab_winner() == "A"


class TestHeat:
    def test_to_float_variants(self):
        assert _to_float(True) == 1.0
        assert _to_float(3) == 3.0
        assert _to_float("4.5") == 4.5
        assert _to_float("nope") == 0.0
        assert _to_float(None) == 0.0
        assert _to_float([1]) == 0.0

    def test_to_timestamp_variants(self):
        assert _to_timestamp(None) is None
        assert _to_timestamp(True) is None
        assert _to_timestamp(123.0) == 123.0
        assert _to_timestamp("456") == 456.0
        assert _to_timestamp("2024-01-01T00:00:00") is not None
        assert _to_timestamp("garbage") is None
        assert _to_timestamp({}) is None

    def test_compute_bounds(self):
        s = HeatScorer()
        hot = s.compute(visit_count=10, interaction_length=1000, last_accessed=time.time())
        cold = s.compute(visit_count=0, interaction_length=0,
                         last_accessed=time.time() - 3600 * 24 * 30)
        assert 0.0 <= cold < hot <= 1.0

    def test_compute_none_last_accessed(self):
        s = HeatScorer()
        v = s.compute(visit_count=5, interaction_length=100, last_accessed=None)
        assert 0.0 <= v <= 1.0

    def test_rank(self):
        s = HeatScorer()
        ranked = s.rank([
            {"id": "a", "visit_count": "5", "last_accessed": "2020-01-01"},
            {"id": "b", "visit_count": 20, "last_accessed": time.time()},
            {"id": "c"},  # all defaults
        ])
        assert ranked[0]["id"] == "b"
        assert all("heat" in r for r in ranked)


class TestAgentManager:
    def _mgr(self, tmp_path):
        return AgentManager(tmp_path, PersonaDetector())

    def test_spawn_explicit_persona(self, tmp_path):
        m = self._mgr(tmp_path)
        r = m.spawn_agent("a1", "ARCH", ["scope"])
        assert r["ok"] is True and r["persona"] == "ARCH"

    def test_spawn_empty_persona(self, tmp_path):
        m = self._mgr(tmp_path)
        r = m.spawn_agent("a1", "  ,  ", ["scope"])
        assert r["ok"] is False

    def test_spawn_duplicate(self, tmp_path):
        m = self._mgr(tmp_path)
        m.spawn_agent("a1", "ARCH", ["s"])
        r = m.spawn_agent("a1", "ARCH", ["s"])
        assert r["ok"] is False and "already exists" in r["error"]

    def test_spawn_auto_detect_fail(self, tmp_path, monkeypatch):
        m = self._mgr(tmp_path)
        monkeypatch.setattr(m.persona, "detect_multiple",
                            lambda p: (_ for _ in ()).throw(RuntimeError("x")))
        r = m.spawn_agent("a1", "auto", ["s"])
        assert r["ok"] is False and "detection failed" in r["error"].lower()

    def test_spawn_auto_no_personas(self, tmp_path, monkeypatch):
        m = self._mgr(tmp_path)
        monkeypatch.setattr(m.persona, "detect_multiple",
                            lambda p: {"personas": [], "lords": []})
        r = m.spawn_agent("a1", "auto", ["s"])
        assert r["ok"] is False

    def test_spawn_auto_success(self, tmp_path, monkeypatch):
        m = self._mgr(tmp_path)
        monkeypatch.setattr(m.persona, "detect_multiple",
                            lambda p: {"personas": ["ARCH"], "lords": ["security"]})
        r = m.spawn_agent("a1", "auto", ["s"])
        assert r["ok"] is True
        assert "security" in r["lords"]

    def test_respawn_not_found(self, tmp_path):
        m = self._mgr(tmp_path)
        r = m.respawn_agent("ghost")
        assert r["ok"] is False and "not found" in r["error"]

    def test_respawn_success(self, tmp_path):
        m = self._mgr(tmp_path)
        m.spawn_agent("a1", "ARCH", ["s"])
        r = m.respawn_agent("a1")
        assert r["ok"] is True

    def test_respawn_limit(self, tmp_path, monkeypatch):
        m = self._mgr(tmp_path)
        m.spawn_agent("a1", "ARCH", ["s"])
        monkeypatch.setattr(m.health, "can_respawn", lambda aid: False)
        r = m.respawn_agent("a1")
        assert r["ok"] is False and "respawn limit" in r["error"]

    def test_health_and_delegate(self, tmp_path):
        m = self._mgr(tmp_path)
        m.spawn_agent("a1", "ARCH", ["s"])
        assert isinstance(m.check_health(), list)
        assert isinstance(m.check_agents_health(), list)
        assert isinstance(m.list_agents(), list)


class TestCrmTransitions:
    def test_opp_valid(self):
        o = Opportunity("o1", "c1")
        o.transition(OpportunityStage.QUALIFIED)
        assert o.stage == OpportunityStage.QUALIFIED

    def test_opp_invalid(self):
        o = Opportunity("o1", "c1")
        with pytest.raises(ValidationError):
            o.transition(OpportunityStage.WON)  # NEW -> WON not allowed

    def test_opp_terminal_no_outgoing(self):
        o = Opportunity("o1", "c1", stage=OpportunityStage.WON)
        with pytest.raises(ValidationError):
            o.transition(OpportunityStage.LOST)

    def test_opp_terminal_reenter(self):
        o = Opportunity("o1", "c1", stage=OpportunityStage.WON)
        with pytest.raises(ValidationError):
            o.transition(OpportunityStage.WON)

    def test_opp_same_stage_ok(self):
        o = Opportunity("o1", "c1", stage=OpportunityStage.NEW)
        o.transition(OpportunityStage.NEW)  # same stage, non-terminal → ok

    def test_task_valid(self):
        t = Task("t1", "do")
        t.transition(TaskStage.DONE)
        assert t.stage == TaskStage.DONE

    def test_task_terminal(self):
        t = Task("t1", "do", stage=TaskStage.CANCELLED)
        with pytest.raises(ValidationError):
            t.transition(TaskStage.TODO)

    def test_task_terminal_reenter(self):
        t = Task("t1", "do", stage=TaskStage.DONE)
        with pytest.raises(ValidationError):
            t.transition(TaskStage.DONE)


class TestBladeLinter:
    def test_missing_file(self, tmp_path):
        assert BladeTemplateLinter().lint_file(tmp_path / "nope.php") == []

    def test_lint_files(self, tmp_path):
        f = tmp_path / "v.blade.php"
        f.write_text("{!! $raw !!}")
        findings = BladeTemplateLinter().lint_files([f])
        assert any(x.rule_id == "BL001" for x in findings)

    def test_non_blade_skipped(self):
        findings = BladeTemplateLinter().lint_content("plain text", "x.txt")
        assert findings == []

    def test_all_rules(self):
        content = """@extends('layout')
{!! $html !!}
<form method="POST" action="/admin/users">
<script>alert(1)</script>
<script>window.data = {{ $d }}</script>
<input value="{{ old('email') }}">
@auth('web') <div>secret</div> @endauth
"""
        findings = BladeTemplateLinter().lint_content(content, "v.blade.php")
        rules = {f.rule_id for f in findings}
        assert {"BL001", "BL002", "BL003", "BL005", "BL009", "BL006", "BL008"} <= rules

    def test_csrf_present_no_bl002(self):
        content = "@extends('l')\n@csrf\n<form></form>"
        findings = BladeTemplateLinter().lint_content(content, "v.blade.php")
        assert not any(f.rule_id == "BL002" for f in findings)

    def test_summary(self):
        linter = BladeTemplateLinter()
        findings = linter.lint_content("{!! $x !!}", "v.blade.php")
        s = linter.summary(findings)
        assert s["total"] == len(findings)
        assert s["by_severity"]["error"] >= 1


class TestFilamentAuditor:
    def test_missing_file(self, tmp_path):
        assert FilamentAccessAuditor().audit_file(tmp_path / "nope.php") == []

    def test_audit_files(self, tmp_path):
        f = tmp_path / "R.php"
        f.write_text("<?php class UserResource extends Resource {}")
        findings = FilamentAccessAuditor().audit_files([f])
        assert any(x.rule_id == "FA002" for x in findings)

    def test_non_php_skipped(self):
        assert FilamentAccessAuditor().audit_content("no php here", "x.txt") == []

    def test_panel_no_auth(self):
        php = "<?php class AdminPanelProvider extends PanelProvider { }"
        findings = FilamentAccessAuditor().audit_content(php, "P.php")
        assert any(f.rule_id == "FA001" and f.severity.value == "critical"
                   for f in findings)

    def test_panel_with_auth(self):
        php = "<?php class P extends PanelProvider { } ->middleware('auth')"
        findings = FilamentAccessAuditor().audit_content(php, "P.php")
        assert not any(f.rule_id == "FA001" for f in findings)

    def test_can_wildcard(self):
        php = "<?php $x->can('*'); $y->can(true); $z->can(fn() => true);"
        findings = FilamentAccessAuditor().audit_content(php, "P.php")
        assert sum(1 for f in findings if f.rule_id == "FA003") >= 1

    def test_table_no_authorize(self):
        php = "<?php $t->table([...]);"
        findings = FilamentAccessAuditor().audit_content(php, "P.php")
        assert any(f.rule_id == "FA004" for f in findings)

    def test_is_accessible_true(self):
        php = "<?php public function isAccessible(): bool { return true; }"
        findings = FilamentAccessAuditor().audit_content(php, "P.php")
        assert any(f.rule_id == "FA005" for f in findings)

    def test_nav_no_visible(self):
        php = "<?php NavigationItem::make()->label('X');"
        findings = FilamentAccessAuditor().audit_content(php, "P.php")
        assert any(f.rule_id == "FA006" for f in findings)

    def test_summary_and_dict(self):
        a = FilamentAccessAuditor()
        findings = a.audit_content("<?php class R extends Resource {}", "x.php")
        s = a.summary(findings)
        assert s["total"] == len(findings)
        d = findings[0].to_dict()
        assert d["rule_id"] == "FA002"


class TestLocalResponder:
    def test_no_provider(self):
        r = LocalResponder()
        assert "unavailable" in r.reply("status").lower()

    def test_provider_fails(self):
        r = LocalResponder(lambda: (_ for _ in ()).throw(RuntimeError("x")))
        out = r.reply("status")
        assert "unavailable" in out.lower()

    def test_help(self):
        assert "intents" in LocalResponder().reply("help me").lower()

    def test_budget_dict(self):
        r = LocalResponder(lambda: {"budgets": {"daily": "1000 tok"}})
        assert "budget" in r.reply("budget?").lower()

    def test_budget_empty_dict(self):
        r = LocalResponder(lambda: {"budgets": {}})
        assert "unlimited" in r.reply("budget").lower()

    def test_budget_list(self):
        r = LocalResponder(lambda: {"budgets": ["a", "b"]})
        assert "2 active" in r.reply("budget")

    def test_budget_empty_list(self):
        r = LocalResponder(lambda: {"budgets": []})
        assert "unlimited" in r.reply("budget").lower()

    def test_status(self):
        r = LocalResponder(lambda: {"version": "5.0", "workflows": {"a": 1},
                                    "rules": ["r"], "personas": {}, "skills": [1, 2]})
        out = r.reply("status")
        assert "v5.0" in out and "workflows" in out

    def test_workflows(self):
        r = LocalResponder(lambda: {"workflows": {"w1": {}, "w2": {}, "w3": {},
                                                  "w4": {}, "w5": {}, "w6": {}}})
        out = r.reply("list workflows")
        assert "6 registered" in out and "+1 more" in out

    def test_workflows_bad_type(self):
        r = LocalResponder(lambda: {"workflows": 42})
        out = r.reply("workflows")
        assert "0 registered" in out

    def test_rules(self):
        r = LocalResponder(lambda: {"rules": {"r1": {}}, "guardian_rules": [1, 2]})
        out = r.reply("rules")
        assert "1 policy" in out and "2 guardian" in out

    def test_skills(self):
        r = LocalResponder(lambda: {"skills": {"s1": {}, "s2": {}}})
        assert "2 skill" in r.reply("skills")

    def test_stack(self):
        r = LocalResponder(lambda: {"tech_stack": {"php": {}, "python": {}}})
        out = r.reply("tech stack")
        assert "php" in out and "python" in out

    def test_stack_empty(self):
        r = LocalResponder(lambda: {"tech_stack": "nope"})
        assert "none detected" in r.reply("stack")

    def test_fallback(self):
        out = LocalResponder().reply("write me a poem")
        assert "No LLM backend" in out


class TestDripEngine:
    def test_as_aware(self):
        naive = datetime(2024, 1, 1)
        aware = _as_aware(naive)
        assert aware.tzinfo is timezone.utc
        still = _as_aware(aware)
        assert still is aware

    def test_add_sequence_dup(self):
        e = DripEngine()
        e.add_sequence("s")
        with pytest.raises(ValidationError):
            e.add_sequence("s")

    def test_add_step_negative_delay(self):
        e = DripEngine()
        seq = e.add_sequence("s")
        with pytest.raises(ValidationError):
            e.add_step(seq, Trigger.ON_ENTER, None, "act", delay_hours=-1)

    def test_unknown_sequence(self):
        with pytest.raises(ValidationError):
            DripEngine().sequence("nope")

    def test_ready_steps_flow(self):
        e = DripEngine()
        seq = e.add_sequence("s")
        s1 = e.add_step(seq, Trigger.ON_ENTER, None, "a1", delay_hours=0)
        s2 = e.add_step(seq, Trigger.ON_EVENT, lambda c: c.get("vip"), "a2")
        s3 = e.add_step(seq, Trigger.MANUAL, None, "a3", delay_hours=24)
        s4 = e.add_step(seq, Trigger.MANUAL,
                        lambda c: (_ for _ in ()).throw(RuntimeError("x")), "a4")
        # Not entered → nothing ready
        assert e.ready_steps() == []
        now = datetime.now(timezone.utc)
        e.enter(s1, now)
        e.enter(s2, now)
        e.enter(s3, now - timedelta(hours=25))
        e.enter(s4, now)
        ready = e.ready_steps(now, context={"vip": True})
        assert s1 in ready and s2 in ready and s3 in ready
        assert s4 not in ready  # raising condition skipped
        # condition false → skipped
        ready2 = e.ready_steps(now, context={"vip": False})
        assert s2 not in ready2
        # fired → excluded
        e.mark_fired(s1)
        assert s1 not in e.ready_steps(now)

    def test_naive_now(self):
        e = DripEngine()
        seq = e.add_sequence("s")
        s1 = e.add_step(seq, Trigger.ON_ENTER, None, "a")
        e.enter(s1, datetime(2020, 1, 1))  # naive → coerced
        assert e.ready_steps(datetime(2020, 1, 2))  # naive now → coerced

    def test_bad_entered_at(self):
        e = DripEngine()
        seq = e.add_sequence("s")
        s1 = e.add_step(seq, Trigger.ON_ENTER, None, "a")
        s1.entered_at = "not-a-date"  # type: ignore[assignment]
        assert e.ready_steps() == []


class TestContextManager:
    def test_ctor_validation(self):
        with pytest.raises(ValueError):
            ContextManager(max_tokens=10)
        with pytest.raises(ValueError):
            ContextManager(recent_window=0)
        with pytest.raises(ValueError):
            ContextManager(compression_ratio=0)
        with pytest.raises(ValueError):
            ContextManager(compression_ratio=1.5)

    def test_trim_noop(self):
        cm = ContextManager(max_tokens=10000)
        msgs = [Message(Role.USER, "hi")]
        assert cm.trim(msgs) == msgs

    def test_trim_splits(self):
        cm = ContextManager(max_tokens=200, recent_window=2)
        msgs = [
            Message(Role.SYSTEM, "sys prompt"),
            *[Message(Role.USER, f"old message {i} " + "x" * 200) for i in range(10)],
            Message(Role.ASSISTANT, "recent 1"),
            Message(Role.USER, "recent 2"),
        ]
        out = cm.trim(msgs)
        assert out[0].role == Role.SYSTEM
        assert out[-1].content == "recent 2"
        # compression reduces total tokens (messages compress in place; merging
        # only happens when the per-message budget is exceeded)
        assert cm.estimate_tokens(out) < cm.estimate_tokens(msgs)

    def test_split_system_mid(self):
        cm = ContextManager()
        msgs = [
            Message(Role.SYSTEM, "s1"),
            Message(Role.USER, "u"),
            Message(Role.SYSTEM, "s2-late"),  # not leading → goes to rest
        ]
        system, rest = cm._split_system(msgs)
        assert len(system) == 1 and len(rest) == 2

    def test_split_recent_atomic(self):
        cm = ContextManager(recent_window=2)
        msgs = [
            Message(Role.USER, "a"),
            Message(Role.ASSISTANT, "call", group_id="g1"),
            Message(Role.TOOL, "result", group_id="g1"),
            Message(Role.USER, "last"),
        ]
        recent, middle = cm._split_recent(msgs, 2)
        # split point would land inside g1 → pulled whole group into recent
        assert len(recent) == 3 and len(middle) == 1

    def test_is_atomic_helper(self):
        from runtime.context_manager import _is_atomic_group
        msgs = [
            Message(Role.ASSISTANT, "a", group_id="g"),
            Message(Role.TOOL, "t", group_id="g"),
            Message(Role.USER, "u"),
        ]
        assert _is_atomic_group(msgs, 0) and _is_atomic_group(msgs, 1)
        assert not _is_atomic_group(msgs, 2)
        solo = [Message(Role.USER, "x", group_id="orphan")]
        assert not _is_atomic_group(solo, 0)

    def test_compress_no_budget(self):
        cm = ContextManager(max_tokens=100, recent_window=1)
        middle = [Message(Role.USER, "m1"), Message(Role.USER, "m2")]
        out = cm._compress_middle(middle, 0)
        assert len(out) == 1 and "compressed" in out[0].content

    def test_compress_overflow_merges(self):
        cm = ContextManager(max_tokens=200, compression_ratio=0.05)
        middle = [Message(Role.USER, "Sentence one. Sentence two. Sentence three." * 20)
                  for _ in range(5)]
        out = cm._compress_middle(middle, 30)
        assert len(out) < len(middle)

    def test_compress_one_short(self):
        cm = ContextManager()
        m = Message(Role.USER, "tiny")
        assert cm._compress_one(m, 100) is m

    def test_compress_one_two_sentences(self):
        cm = ContextManager()
        m = Message(Role.USER, "One. Two.", tokens=100)
        out = cm._compress_one(m, 5)
        assert out.content.endswith("...")

    def test_summarize_all_roles(self):
        cm = ContextManager()
        out = cm._summarize_all([Message(Role.USER, "a"), Message(Role.TOOL, "b")])
        assert "tool" in out.content and "user" in out.content

    def test_merge(self):
        cm = ContextManager()
        a = Message(Role.USER, "hello", metadata={"k": 1})
        b = Message(Role.USER, "world", metadata={"j": 2})
        m = cm._merge(a, b)
        assert "[+1 msg]" in m.content and m.metadata == {"k": 1, "j": 2}

    def test_compress_with_llm(self):
        out = compress_with_llm([Message(Role.USER, "hi")], lambda p: "SUMMARY")
        assert out == "SUMMARY"
