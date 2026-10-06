"""Gap tests for eval/pipeline.py."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from eval.pipeline import (
    Assertion,
    AssertionKind,
    CaseResult,
    EvalCase,
    EvalPipeline,
    PipelineResult,
    main,
    run_pipeline,
)


def _a(kind: AssertionKind, **kw) -> Assertion:
    kw.setdefault("description", "d")
    return Assertion(kind=kind, **kw)


class TestAssertionKinds:
    def test_contains_fail(self):
        ok, reason = _a(AssertionKind.CONTAINS, key="k", expected="needle").evaluate({"k": "hay"})
        assert not ok and "not found" in reason

    def test_not_contains_fail(self):
        ok, reason = _a(AssertionKind.NOT_CONTAINS, key="k", expected="bad").evaluate({"k": "so bad"})
        assert not ok and "should be absent" in reason

    def test_regex_fail(self):
        ok, reason = _a(AssertionKind.REGEX, key="k", expected=r"\d+").evaluate({"k": "abc"})
        assert not ok and "did not match" in reason

    def test_decision_is_fail(self):
        ok, _ = _a(AssertionKind.DECISION_IS, expected="deny").evaluate({"decision": "allow"})
        assert not ok

    def test_gate_is(self):
        ok, _ = _a(AssertionKind.GATE_IS, expected="probity").evaluate({"gate": "probity"})
        assert ok
        ok, _ = _a(AssertionKind.GATE_IS, expected="probity").evaluate({"gate": "policy"})
        assert not ok

    def test_custom_raise_and_missing(self):
        ok, reason = _a(AssertionKind.CUSTOM, check=lambda r: 1 / 0).evaluate({})
        assert not ok and "raised" in reason
        ok, reason = _a(AssertionKind.CUSTOM).evaluate({})
        assert not ok and "no check" in reason
        ok, _ = _a(AssertionKind.CUSTOM, check=lambda r: True).evaluate({})
        assert ok

    def test_unknown_kind(self):
        a = _a(AssertionKind.OK_TRUE)
        object.__setattr__(a, "kind", "bogus")  # frozen dataclass
        ok, reason = a.evaluate({})
        assert not ok and "unknown" in reason


class TestResultAggregation:
    def _res(self, passed, response, score=5.0, tags=()):
        case = EvalCase(id="c", action="a", tags=list(tags))
        return CaseResult(case=case, passed=passed, response=response,
                          weighted_score=score)

    def test_per_gate_summary(self):
        p = PipelineResult(results=[
            self._res(True, {"gate": "policy"}),
            self._res(False, {"gate": "policy"}),
            self._res(False, {}),
        ])
        s = p.per_gate_summary()
        assert s["policy"] == {"total": 2, "passed": 1, "failed": 1}
        assert s["unknown"]["failed"] == 1

    def test_per_policy_summary(self):
        p = PipelineResult(results=[
            self._res(False, {"decision": {"rule": "r1"}}),
            self._res(True, {"decision": "scalar-decision"}),
        ])
        s = p.per_policy_summary()
        assert s["r1"]["failed"] == 1
        assert s["scalar-decision"]["passed"] == 1

    def test_by_tag_and_gate(self):
        p = PipelineResult(results=[
            self._res(True, {"gate": "g1"}, tags=("sec",)),
            self._res(False, {"gate": "g2"}),
        ])
        assert len(p.by_tag("sec")) == 1
        assert len(p.by_gate("g2")) == 1
        assert p.mean_weighted_score == 5.0

    def test_empty_mean_score(self):
        p = PipelineResult(results=[self._res(True, {}, score=0.0)])
        assert p.mean_weighted_score == 0.0


class TestPipeline:
    def test_approved_flag_and_kernel_error(self):
        kernel = MagicMock()
        kernel.act.side_effect = RuntimeError("died")
        pipe = EvalPipeline(kernel)
        case = EvalCase(id="c", action="a", approved=True,
                        assertions=[_a(AssertionKind.OK_TRUE)])
        res = pipe.run_case(case)
        assert not res.passed
        assert "kernel.act raised" in res.error
        # approved=True was forwarded
        assert kernel.act.call_args.kwargs.get("approved") is True or \
            kernel.act.call_args[1].get("approved") is True

    def test_dimension_gate(self):
        kernel = MagicMock()
        kernel.act.return_value = {"ok": True}
        dim: Any = MagicMock()
        dim.name = "safety"
        dim.weight = 1.0
        dim.score.return_value = (2, ["low score"])  # <4 -> fail
        case = EvalCase(id="c", action="a", dimensions=(dim,),
                        assertions=[_a(AssertionKind.OK_TRUE)])
        res = EvalPipeline(kernel).run_case(case)
        assert not res.passed
        assert res.dimension_scores["safety"] == 2

    def test_run_pipeline_helper(self):
        kernel = MagicMock()
        kernel.act.return_value = {"ok": True}
        out = run_pipeline([EvalCase(id="c", action="a",
                                     assertions=[_a(AssertionKind.OK_TRUE)])], kernel)
        assert out.passed == 1


class TestMain:
    def test_main_runs(self):
        rc = main()
        assert rc in (0, 1)
