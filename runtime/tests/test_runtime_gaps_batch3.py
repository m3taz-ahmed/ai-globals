"""Gap coverage batch: agent_gateway, metrics, mcp_orchestrator, agent_sli, budget, codegraph."""
from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import runtime.metrics as mt
from runtime.agent_gateway import (
    AgentGateway,
    GatewayError,
    GuardrailContext,
    GuardrailPhase,
    GuardrailResult,
    Verdict,
)
from runtime.agent_sli import AgentSliCollector, SliStatus
from runtime.budget import (
    Budget,
    BudgetAction,
    BudgetManager,
    BudgetTargetScope,
    BudgetWindowManager,
    make_window,
)
from runtime.codegraph import CodeGraphBuilder, ReachabilityAnalyzer
from runtime.mcp_orchestrator import McpOrchestrator, Plan, Step, StepStatus
from runtime.schemas import ValidationError


class TestAgentGateway:
    def test_to_gate_verdict_allow(self):
        v = GuardrailResult(Verdict.ALLOW, "g", reason="ok").to_gate_verdict()
        assert v is not None

    def test_gateway_error(self):
        e = GatewayError("boom")
        assert "boom" in str(e)

    def test_severity_rank_unknown(self):
        gw = AgentGateway()
        with pytest.raises(GatewayError):
            gw._severity_rank(None)  # type: ignore[arg-type]

    def test_guardrail_exception_blocks(self):
        gw = AgentGateway()

        def boom(ctx):
            raise RuntimeError("explode")

        gw.register("boom", GuardrailPhase.PRE_LLM, boom)
        verdict, results = gw.check_request(GuardrailContext(prompt="hi"))
        assert verdict == Verdict.BLOCK
        assert any(r.guardrail_name == "boom" for r in results)
        gw.unregister("boom")

    def test_run_phase_empty_allows(self):
        gw = AgentGateway()
        for name in gw.list_guardrails():
            gw.unregister(name["name"])
        verdict, results = gw.check_request(GuardrailContext(prompt="x"))
        assert verdict == Verdict.ALLOW
        assert results == []

    def test_verdict_log_trim(self):
        gw = AgentGateway()
        gw._verdict_log.extend({"i": i} for i in range(1001))
        gw._log("request", Verdict.ALLOW, [], GuardrailContext(prompt="p"))
        assert len(gw._verdict_log) <= 501


class TestMetrics:
    def test_missing_labels(self):
        c = mt.Counter("m1", "doc", labels=("a", "b"))
        with pytest.raises(mt.LabelValueError):
            c.labels(a="1")

    def test_max_children(self):
        c = mt.Counter("m2", "doc", labels=("l",))
        with patch.object(mt.Metric, "MAX_CHILDREN", 1):
            c.labels(l="a")
            with pytest.raises(mt.LabelValueError):
                c.labels(l="b")

    def test_counter_negative(self):
        with pytest.raises(ValidationError):
            mt.Counter("m3", "d").inc(-1)

    def test_summary_quantile_unsorted(self):
        child = mt._SummaryChild(quantiles=(0.5,))
        child.observe(3.0)
        child.observe(1.0)
        child.observe(2.0)
        assert child._quantile(0.5) == pytest.approx(2.0)

    def test_generate_latest_restricted(self):
        reg = mt.CollectorRegistry()
        c = mt.Counter("m4", "doc")
        reg.register(c)
        c.inc()
        rr = mt.RestrictedRegistry(reg, ["m4"])
        out = mt.generate_latest(rr)
        assert "m4" in out

    def test_generate_latest_dup_names(self):
        reg = mt.CollectorRegistry()
        a = mt.Counter("m5", "d")
        b = mt.Counter("m5", "d")  # same name, different object
        reg.register(a)
        reg._collectors["m5b"] = b  # inject second collector, same name
        out = mt.generate_latest(reg)
        assert out.count("HELP m5") == 1

    def test_format_metrics_typeerror(self):
        k = SimpleNamespace(
            status=lambda: {
                "workflows": object(), "rules": object(), "budgets": object(),
            },
            budget=SimpleNamespace(usage={"sess": {"tokens": 3, "calls": 1}}),
        )
        out = mt.format_metrics(k)  # type: ignore[arg-type]
        assert "aizee_workflows_total 0" in out
        assert 'scope="sess"' in out


class FakeCall:
    def __init__(self, result=None, error=""):
        self.result = result
        self.error = error


class FakeAgent:
    def __init__(self, mapping=None):
        self.mapping = mapping or {}

    async def call_tool(self, tool, args):
        entry = self.mapping.get(tool)
        if entry is None:
            return FakeCall(result={"tool": tool, "args": args})
        if isinstance(entry, Exception):
            raise entry
        return entry


class TestMcpOrchestrator:
    def _run(self, plan, agent=None):
        orch = McpOrchestrator(agent or FakeAgent())
        return asyncio.run(orch.execute(plan))

    def test_arg_ref_no_dot(self):
        plan = Plan(id="p", steps=[Step(id="s", tool="t", arguments={"a": "${plain}"})])
        res = self._run(plan)
        assert res["s"].status == StepStatus.COMPLETED

    def test_arg_ref_missing_step(self):
        plan = Plan(id="p", steps=[Step(id="s", tool="t", arguments={"a": "${ghost.x}"})])
        res = self._run(plan)
        assert res["s"].status == StepStatus.COMPLETED

    def test_arg_ref_completed(self):
        agent = FakeAgent({"t1": FakeCall(result={"v": 42})})
        plan = Plan(id="p", steps=[
            Step(id="s1", tool="t1"),
            Step(id="s2", tool="t2", arguments={"a": "${s1.v}"}, depends_on=["s1"]),
        ])
        res = self._run(plan, agent)
        assert res["s2"].status == StepStatus.COMPLETED

    def test_execute_async_alias(self):
        orch = McpOrchestrator(FakeAgent())
        plan = Plan(id="p", steps=[Step(id="s", tool="t")])
        res = asyncio.run(orch.execute_async(plan))
        assert res["s"].status == StepStatus.COMPLETED

    def test_unsatisfiable_dep(self):
        plan = Plan(id="p", steps=[
            Step(id="s", tool="t", depends_on=["ghost"]),
        ])
        res = self._run(plan)
        assert res["s"].status == StepStatus.FAILED
        assert "unsatisfiable" in res["s"].error

    def test_circular_deadlock(self):
        plan = Plan(id="p", steps=[
            Step(id="a", tool="t", depends_on=["b"]),
            Step(id="b", tool="t", depends_on=["a"]),
        ])
        res = self._run(plan)
        assert res["a"].status == StepStatus.FAILED
        assert res["b"].status == StepStatus.FAILED

    def test_failed_chain_missing_and_diamond(self):
        orch = McpOrchestrator(FakeAgent())
        plan = Plan(id="p", steps=[
            Step(id="a", tool="t"),
            Step(id="b", tool="t", depends_on=["a", "a", "ghost"]),
            Step(id="c", tool="t", depends_on=["b", "a"]),
        ])
        chain = orch._failed_chain(plan, "c")
        ids = {s.id for s in chain}
        assert "a" in ids and "b" in ids

    def test_rollback_ancestors(self):
        agent = FakeAgent({
            "ok": FakeCall(result="done"),
            "bad": FakeCall(error="nope"),
            "rb": FakeCall(result="rolled"),
        })
        plan = Plan(id="p", steps=[
            Step(id="s1", tool="ok", rollback_tool="rb"),
            Step(id="s2", tool="ok"),  # no rollback_tool -> skipped
            Step(id="s3", tool="bad", depends_on=["s1", "s2"]),
        ])
        res = self._run(plan, agent)
        assert res["s3"].status == StepStatus.FAILED
        assert res["s1"].status == StepStatus.ROLLED_BACK


class TestAgentSli:
    def test_empty_tie(self):
        c = AgentSliCollector()
        res = c._compute_tie("cls", [])
        assert res.name == "tool_invocation_efficiency" or res.task_class == "cls"

    def test_ratio_yellow(self):
        assert AgentSliCollector._ratio_status(0.5, 0.3, 0.7) == SliStatus.YELLOW

    def test_drift_red(self):
        assert AgentSliCollector._drift_status(0.9, 0.3, 0.7) == SliStatus.RED


class TestBudget:
    def test_window_scope_mismatch(self):
        wm = BudgetWindowManager()
        wm.register_window(make_window(BudgetTargetScope.AGENT, "a1", limit=10))
        assert wm.check_budget_limit(BudgetTargetScope.SESSION, "a1", 1.0) == BudgetAction.WARN

    def test_window_low_utilization_warn(self):
        wm = BudgetWindowManager()
        wm.register_window(make_window(BudgetTargetScope.SESSION, "s", limit=100, action=BudgetAction.REJECT))
        assert wm.check_budget_limit(BudgetTargetScope.SESSION, "s", 1.0) == BudgetAction.WARN

    def test_window_alert_threshold_warn_action(self):
        wm = BudgetWindowManager()
        w = make_window(BudgetTargetScope.SESSION, "s", limit=100, action=BudgetAction.WARN)
        w.spend = 85.0
        wm.register_window(w)
        # util >= 0.8 but action WARN -> stays WARN
        assert wm.check_budget_limit(BudgetTargetScope.SESSION, "s", 1.0) == BudgetAction.WARN

    def test_should_stop_subagent_no_limit(self):
        wm = BudgetWindowManager()
        wm.register_window(make_window(BudgetTargetScope.SESSION, "s", limit=0))
        assert wm.should_stop_subagent(BudgetTargetScope.SESSION, "s") is False

    def test_should_stop_subagent_with_limit(self):
        wm = BudgetWindowManager()
        w = make_window(BudgetTargetScope.SESSION, "s", limit=100)
        w.spend = 99.0
        wm.register_window(w)
        wm.should_stop_subagent(BudgetTargetScope.SESSION, "s")

    def test_daily_period_key_unchanged(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("daily-scope", Budget(max_tokens=10**9, period="daily"))
        bm.check("daily-scope", tokens=1)
        bm.check("daily-scope", tokens=1)  # second call: period_key equal -> skip reset

    def test_no_window_manager(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.window_manager = None
        bm.set_budget("s", Budget(max_tokens=10))
        res = bm.check("s", tokens=1)
        assert res["ok"] is True

    def test_window_warn_action_path(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        w = make_window(BudgetTargetScope.SESSION, "session", limit=100)
        bm.window_manager.register_window(w)
        bm.set_budget("session", Budget(max_tokens=10**9))
        res = bm.check("session", tokens=1, cost=1.0)
        assert res["ok"] is True

    def test_warn_on_exceed(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("w", Budget(max_tokens=5, on_exceed="warn"))
        res = bm.check("w", tokens=10)
        assert res["action"] == "warn"

    def test_fallback_on_exceed(self, tmp_path: Path):
        bm = BudgetManager(tmp_path)
        bm.set_budget("f", Budget(max_tokens=5, on_exceed="fallback", fallback_model="cheap"))
        res = bm.check("f", tokens=10)
        assert res["action"] == "fallback"
        assert res["fallback_model"] == "cheap"


class TestCodegraph:
    def test_get_function(self, tmp_path: Path):
        f = tmp_path / "m.py"
        f.write_text("def foo():\n    pass\n")
        g = CodeGraphBuilder().build_from_file(f)
        assert g.get_function("foo") is not None
        assert g.get_function("nope") is None

    def test_build_from_directory(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("def fa():\n    pass\n")
        (tmp_path / "b.txt").write_text("not python")
        pkg = tmp_path / "__pycache__"
        pkg.mkdir()
        (pkg / "c.py").write_text("def fc():\n    pass\n")
        g = CodeGraphBuilder().build_from_directory(tmp_path)
        assert g.get_function("fa") is not None
        assert g.get_function("fc") is None  # __pycache__ skipped

    def test_build_custom_extensions(self, tmp_path: Path):
        (tmp_path / "a.txt").write_text("def ft():\n    pass\n")
        g = CodeGraphBuilder().build_from_directory(tmp_path, extensions={".txt"})
        assert g.get_function("ft") is not None

    def test_callee_attribute_and_none(self, tmp_path: Path):
        f = tmp_path / "m.py"
        f.write_text(
            "def caller():\n"
            "    obj.method()\n"
            "    items[0]()\n"
        )
        g = CodeGraphBuilder().build_from_file(f)
        callees = [e.callee for e in g.get_calls_from("caller")]
        assert "method" in callees

    def test_find_paths_self(self, tmp_path: Path):
        f = tmp_path / "m.py"
        f.write_text("def a():\n    b()\ndef b():\n    pass\n")
        g = CodeGraphBuilder().build_from_file(f)
        ra = ReachabilityAnalyzer(g)
        assert ra.find_paths("a", "a") == [["a"]]

    def test_find_paths_max_length(self, tmp_path: Path):
        f = tmp_path / "m.py"
        f.write_text(
            "def a():\n    b()\ndef b():\n    c()\ndef c():\n    d()\ndef d():\n    pass\n"
        )
        g = CodeGraphBuilder().build_from_file(f)
        ra = ReachabilityAnalyzer(g, max_path_length=2)
        assert ra.find_paths("a", "d") == []

    def test_find_paths_cycle(self, tmp_path: Path):
        f = tmp_path / "m.py"
        f.write_text(
            "def a():\n    b()\ndef b():\n    a()\n    c()\ndef c():\n    pass\n"
        )
        g = CodeGraphBuilder().build_from_file(f)
        ra = ReachabilityAnalyzer(g)
        paths = ra.find_paths("a", "c")
        assert paths == [["a", "b", "c"]]
