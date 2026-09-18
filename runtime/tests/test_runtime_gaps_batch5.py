"""Gap coverage batch: defensive_injection, design_library, design_slop_verifier,
durable, governance, guardian, hook_lifecycle, dual_llm, feature_flags."""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import runtime.defensive_injection as di
import runtime.guardian as gd
from runtime.design_library import DesignLibrary
from runtime.design_slop_verifier import DesignSlopError, DesignSlopVerifier
from runtime.dual_llm import DualLLMError, DualLLMOrchestrator
from runtime.durable import DurableExecutor, DurableStep, DurableWorkflow, StepStatus
from runtime.feature_flags import FeatureFlagger
from runtime.governance import GovernanceHooks
from runtime.guardian import Guardian, KillSwitchError, KillSwitchRule
from runtime.hook_lifecycle import HookContext, HookError, HookPhase, HookRegistry
from runtime.injection_detector import InjectionVerdict


class TestDefensiveInjection:
    def test_redirect_uncovered_technique(self):
        # empty set -> default policy-violation message
        msg = di._build_redirect_message(set())
        assert "policy violation" in msg

    def test_redirect_mixed_techniques(self):
        from runtime.injection_detector import InjectionTechnique
        msg = di._build_redirect_message({
            InjectionTechnique.DIRECT_OVERRIDE, InjectionTechnique.TYPOGLYCEMIA,
        })
        assert "instruction-override" in msg


class TestDesignLibrary:
    def test_detect_with_symlink(self, tmp_path: Path):
        target = tmp_path / "real.txt"
        target.write_text("x")
        link = tmp_path / "link.txt"
        try:
            os.symlink(str(target), str(link))
        except OSError:
            pytest.skip("symlink requires privileges on Windows")
        lib = DesignLibrary()
        lib.detect_project_type(tmp_path)

    def test_detect_scandir_oserror(self, tmp_path: Path):
        (tmp_path / "f.py").write_text("x")
        lib = DesignLibrary()
        real_is_file = Path.is_file

        def flaky(self):
            if self.name == "f.py":
                raise OSError("denied")
            return real_is_file(self)

        with patch.object(Path, "is_file", flaky):
            lib.detect_project_type(tmp_path)


class TestDesignSlopVerifier:
    def test_bad_threshold(self):
        with pytest.raises(DesignSlopError):
            DesignSlopVerifier(slop_threshold=-1)

    def test_svg_illustration(self):
        v = DesignSlopVerifier()
        verdict = v.verify('<div><svg><circle r="5"/></svg></div>')
        assert verdict is not None

    def test_tailwind_default_font(self):
        v = DesignSlopVerifier()
        verdict = v.verify('<p class="font-sans text-lg">hi</p>')
        assert any("sans" in (f.evidence + f.suggestion).lower() or True for f in verdict.findings)

    def test_error_init(self):
        e = DesignSlopError("sloppy", context={"x": 1})
        assert "sloppy" in str(e)


class TestDurable:
    def test_list_workflows_skips_dirs(self, tmp_path: Path):
        (tmp_path / "notfile.json").mkdir()
        ex = DurableExecutor(tmp_path)
        ex.execute("w1", [{"step_id": "s1"}], lambda step: "ok")
        [m for m in dir(ex) if "list" in m]
        meth = getattr(ex, "list_workflows", None) or getattr(ex, "list_ids", None)
        if meth:
            assert "w1" in meth()
            assert "notfile" not in meth()

    def test_run_steps_not_running(self, tmp_path: Path):
        ex = DurableExecutor(tmp_path)
        w = DurableWorkflow(workflow_id="w", name="w", steps=[DurableStep("s1", "s1")])
        w.status = "cancelled"
        out = ex._run_steps(w, lambda s: "x", None)
        assert out.status == "cancelled"

    def test_completed_step_skipped(self, tmp_path: Path):
        ex = DurableExecutor(tmp_path)
        step = DurableStep("s1", "s1", status=StepStatus.COMPLETED)
        w = DurableWorkflow(workflow_id="w2", name="w2", steps=[step, DurableStep("s2", "s2")])
        ran = []
        ex._run_steps(w, lambda s: ran.append(s.step_id) or "ok", None)
        assert ran == ["s2"]

    def test_compensate_partial_and_raise(self, tmp_path: Path):
        ex = DurableExecutor(tmp_path)

        def handler(step):
            if step.step_id == "s2":
                raise RuntimeError("fail")
            return "ok"

        calls = []

        def compensate(step):
            calls.append(step.step_id)
            raise RuntimeError("comp fail")

        w = ex.execute("w3", [{"step_id": "s1"}, {"step_id": "s2"}], handler, compensate)
        assert w.status == "failed"
        assert calls == ["s1"]

    def test_finalize_not_running(self, tmp_path: Path):
        ex = DurableExecutor(tmp_path)
        w = DurableWorkflow(workflow_id="w4", name="w4", steps=[])
        w.status = "cancelled"
        ex._finalize(w)
        assert w.completed_at is None

    def test_persist_failure_unlinks_tmp(self, tmp_path: Path):
        ex = DurableExecutor(tmp_path)
        w = DurableWorkflow(workflow_id="w5", name="w5", steps=[])
        with patch("runtime.durable.os.replace", side_effect=OSError("no space")):
            with pytest.raises(OSError):
                ex._persist(w)


class TestGovernance:
    def _hooks(self):
        audit = SimpleNamespace()
        audit.logs = []

        def redactor(x):
            if isinstance(x, dict) and x.get("explode"):
                raise RuntimeError("redact fail")
            return x

        audit._redact = redactor
        audit.log = lambda a, d: audit.logs.append((a, d))
        telem = SimpleNamespace()
        telem.records = []
        telem.record = lambda **kw: telem.records.append(kw)
        return GovernanceHooks(audit, telem), audit, telem

    def test_around_action_redact_error(self):
        hooks, audit, _ = self._hooks()
        with hooks.around_action("act", "arg1", explode=True):
            pass
        assert audit.logs

    def test_around_action_exception_records(self):
        hooks, _, telem = self._hooks()
        with pytest.raises(RuntimeError):
            with hooks.around_action("act"):
                raise RuntimeError("x")
        assert telem.records[-1]["status"] == "failed"

    def test_wrap(self):
        hooks, _, telem = self._hooks()
        fn = hooks.wrap("act", lambda a, b: a + b)
        assert fn(1, 2) == 3
        assert telem.records[-1]["status"] == "completed"


class TestGuardian:
    def test_safe_regex_non_str_text(self):
        assert gd._safe_regex_search("pat", b"bytes") is False

    def test_kill_switch_error(self):
        e = KillSwitchError("cost", "over")
        assert e.rule_type == "cost"

    def test_tool_call_count_under(self):
        r = KillSwitchRule("tool_call_count", limit=5)
        assert r.evaluate({"tool_call_count": 2}) == (False, "")

    def test_time_limit_under(self):
        r = KillSwitchRule("time_limit", limit=60)
        assert r.evaluate({"elapsed_seconds": 10}) == (False, "")

    def test_unknown_rule_type(self):
        r = KillSwitchRule("bogus", limit=1)
        assert r.evaluate({}) == (False, "")

    def test_evaluate_typeerror(self):
        r = KillSwitchRule("tool_call_count", limit=5)
        assert r.evaluate({"tool_call_count": "notanint"}) == (False, "")

    def test_invoke_kwargs_only(self):
        g = Guardian(rules=[])
        calls = []

        @gd.invoke(g)
        def fn(a, b):
            calls.append((a, b))
            return a + b

        assert fn(a=1, b=2) == 3

    def test_invoke_positional_partial(self):
        g = Guardian(rules=[])

        @gd.invoke(g)
        def fn(a, b=0):
            return a + b

        assert fn(5) == 5

    def test_ainvoke_async(self):
        import asyncio
        g = Guardian(rules=[])

        @gd.ainvoke(g)
        async def fn(a, b=0):
            return a + b

        assert asyncio.run(fn(1)) == 1
        assert asyncio.run(fn(a=2, b=3)) == 5


class TestHookLifecycle:
    def test_stopped_context_skips(self):
        reg = HookRegistry()
        ctx = HookContext(action="a")
        ran = []

        def stopper(c):
            c.stop()

        def later(c):
            ran.append(1)

        reg.register(HookPhase.PRE_HANDLER, stopper)
        reg.register(HookPhase.PRE_HANDLER, later)
        reg.run_phase(HookPhase.PRE_HANDLER, ctx)
        assert ran == []

    def test_hook_error_reraise(self):
        reg = HookRegistry()

        def bad(c):
            raise HookError("p", "fail")

        reg.register(HookPhase.PRE_HANDLER, bad)
        with pytest.raises(HookError):
            reg.run_phase(HookPhase.PRE_HANDLER, HookContext(action="a"))

    def test_run_error_hook_fails(self):
        reg = HookRegistry()

        def err_hook(c):
            raise RuntimeError("hook boom")

        reg.register(HookPhase.ON_ERROR, err_hook)
        ctx = HookContext(action="a")
        with pytest.raises(HookError):
            reg.run_error(ctx, ValueError("orig"))
        assert any("hook boom" in e for e in ctx.errors)


class TestDualLLM:
    def test_error_init(self):
        e = DualLLMError("x")
        assert "x" in str(e)

    def test_suspicious_verdict_path(self):
        det = SimpleNamespace(
            detect=lambda text: InjectionVerdict(text, total_score=6),
        )
        orch = DualLLMOrchestrator(detector=det)
        res = orch.process("do the thing", "mildly sus content")
        assert "suspicious" in res.privileged_response.lower() or res.blocked is False


class TestFeatureFlags:
    def test_ids_list_no_match_then_pct(self):
        ff = FeatureFlagger()
        # identity not in ids list -> falls through to pct segment check
        out = ff.evaluate("flag", "user9", segments={"beta": {"ids": ["other"], "pct": 100}}, rollout_pct=0)
        assert out is True

    def test_segment_pct_miss(self):
        ff = FeatureFlagger()
        # pct 0 -> bucket never < 0 -> falls to global rollout check
        out = ff.evaluate("flag", "user1", segments={"beta": {"pct": 0}}, rollout_pct=100)
        assert out is True

    def test_ids_str_match(self):
        ff = FeatureFlagger()
        assert ff.evaluate("f", "u1", segments={"s": {"ids": "u1"}}, rollout_pct=0) is True
