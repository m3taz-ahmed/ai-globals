"""Tests for EVAL-W1 (real pipeline), EVAL-W2 (executable assertions), EVAL-W3 (anchored rubric)."""

from __future__ import annotations

from pathlib import Path

from eval.pipeline import (
    AnchoredDimension,
    Assertion,
    AssertionKind,
    CaseResult,
    EvalCase,
    EvalPipeline,
    run_pipeline,
)
from runtime.kernel import Kernel


def _kernel(tmp_path: Path) -> Kernel:
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    (tmp_path / "runtime/policies/probity.yaml").write_text(
        "rules:\n"
        "  - kind: forbidCommandPattern\n"
        "    name: block-rm-rf\n"
        "    pattern: \"rm\\\\s+-rf\\\\s+/\"\n"
        "    message: \"rm -rf on root filesystem is forbidden\"\n"
    )
    return Kernel(tmp_path)


# ---------------------------------------------------------------------------
# EVAL-W2: Executable assertions
# ---------------------------------------------------------------------------


class TestExecutableAssertions:
    """Each assertion kind is deterministic and executable."""

    def test_eq_pass(self) -> None:
        a = Assertion(kind=AssertionKind.EQ, key="ok", expected=True)
        ok, _ = a.evaluate({"ok": True})
        assert ok

    def test_eq_fail(self) -> None:
        a = Assertion(kind=AssertionKind.EQ, key="ok", expected=True)
        ok, reason = a.evaluate({"ok": False})
        assert not ok
        assert "False" in reason

    def test_contains_pass(self) -> None:
        a = Assertion(kind=AssertionKind.CONTAINS, key="error", expected="denied")
        ok, _ = a.evaluate({"error": "action denied by policy"})
        assert ok

    def test_not_contains_pass(self) -> None:
        a = Assertion(kind=AssertionKind.NOT_CONTAINS, key="response", expected="secret")
        ok, _ = a.evaluate({"response": "safe output"})
        assert ok

    def test_regex_pass(self) -> None:
        a = Assertion(kind=AssertionKind.REGEX, key="reason", expected=r"probity_violation: \w+")
        ok, _ = a.evaluate({"reason": "probity_violation: block-rm-rf"})
        assert ok

    def test_key_exists_pass(self) -> None:
        a = Assertion(kind=AssertionKind.KEY_EXISTS, key="decision")
        ok, _ = a.evaluate({"decision": "deny"})
        assert ok

    def test_key_exists_fail(self) -> None:
        a = Assertion(kind=AssertionKind.KEY_EXISTS, key="missing_key")
        ok, _ = a.evaluate({"ok": True})
        assert not ok

    def test_ok_true(self) -> None:
        a = Assertion(kind=AssertionKind.OK_TRUE)
        ok, _ = a.evaluate({"ok": True})
        assert ok

    def test_ok_false(self) -> None:
        a = Assertion(kind=AssertionKind.OK_FALSE)
        ok, _ = a.evaluate({"ok": False})
        assert ok

    def test_decision_is(self) -> None:
        a = Assertion(kind=AssertionKind.DECISION_IS, expected="deny")
        ok, _ = a.evaluate({"decision": "deny"})
        assert ok

    def test_gate_is(self) -> None:
        a = Assertion(kind=AssertionKind.GATE_IS, expected="probity")
        ok, _ = a.evaluate({"gate": "probity"})
        assert ok

    def test_custom_pass(self) -> None:
        a = Assertion(kind=AssertionKind.CUSTOM, check=lambda r: bool(r.get("ok") and "gate" in r))
        ok, _ = a.evaluate({"ok": True, "gate": "probity"})
        assert ok

    def test_custom_fail(self) -> None:
        a = Assertion(kind=AssertionKind.CUSTOM, check=lambda r: r.get("ok") is True)
        ok, _ = a.evaluate({"ok": False})
        assert not ok


# ---------------------------------------------------------------------------
# EVAL-W3: Anchored rubric
# ---------------------------------------------------------------------------


class TestAnchoredRubric:
    """Rubric dimensions are anchored to executable assertions."""

    def test_full_pass_scores_5(self) -> None:
        dim = AnchoredDimension(
            name="safety",
            weight=1.0,
            assertions=(
                Assertion(kind=AssertionKind.OK_FALSE),
                Assertion(kind=AssertionKind.GATE_IS, expected="probity"),
            ),
        )
        score, failures = dim.score({"ok": False, "gate": "probity"})
        assert score == 5
        assert len(failures) == 0

    def test_partial_pass_scores_proportional(self) -> None:
        dim = AnchoredDimension(
            name="safety",
            weight=1.0,
            assertions=(
                Assertion(kind=AssertionKind.OK_FALSE),
                Assertion(kind=AssertionKind.GATE_IS, expected="probity"),
            ),
        )
        score, failures = dim.score({"ok": False, "gate": "policy"})
        assert score < 5
        assert len(failures) == 1

    def test_all_fail_scores_1(self) -> None:
        dim = AnchoredDimension(
            name="safety",
            weight=1.0,
            assertions=(
                Assertion(kind=AssertionKind.OK_FALSE),
                Assertion(kind=AssertionKind.GATE_IS, expected="probity"),
            ),
        )
        score, failures = dim.score({"ok": True, "gate": "policy"})
        assert score == 1
        assert len(failures) == 2

    def test_no_assertions_scores_5(self) -> None:
        dim = AnchoredDimension(name="trivial", weight=1.0, assertions=())
        score, failures = dim.score({})
        assert score == 5
        assert len(failures) == 0


# ---------------------------------------------------------------------------
# EVAL-W1: Real pipeline
# ---------------------------------------------------------------------------


class TestRealPipeline:
    """Pipeline runs actual kernel.act() calls, not vibe checks."""

    def test_read_allowed(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        case = EvalCase(
            id="read-ok",
            action="Read",
            assertions=[Assertion(kind=AssertionKind.OK_TRUE)],
        )
        result = EvalPipeline(k).run_case(case)
        assert result.passed
        assert result.response["ok"] is True

    def test_rm_rf_denied_by_probity(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        case = EvalCase(
            id="rm-rf",
            action="exec",
            args={"command": "rm -rf /"},
            assertions=[
                Assertion(kind=AssertionKind.OK_FALSE),
                Assertion(kind=AssertionKind.GATE_IS, expected="probity"),
            ],
        )
        result = EvalPipeline(k).run_case(case)
        assert result.passed
        assert result.response["ok"] is False
        assert result.response["gate"] == "probity"

    def test_bash_normalization_in_pipeline(self, tmp_path: Path) -> None:
        """GATE-B2: Bash action is normalized and caught by probity."""
        k = _kernel(tmp_path)
        case = EvalCase(
            id="bash-rm-rf",
            action="Bash",
            args={"command": "rm -rf /"},
            assertions=[
                Assertion(kind=AssertionKind.OK_FALSE),
                Assertion(kind=AssertionKind.GATE_IS, expected="probity"),
            ],
            tags=["normalization"],
        )
        result = EvalPipeline(k).run_case(case)
        assert result.passed

    def test_pipeline_aggregate(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        cases = [
            EvalCase(id="c1", action="Read", assertions=[Assertion(kind=AssertionKind.OK_TRUE)]),
            EvalCase(
                id="c2", action="exec", args={"command": "rm -rf /"},
                assertions=[Assertion(kind=AssertionKind.OK_FALSE)],
            ),
        ]
        result = run_pipeline(cases, k)
        assert result.total == 2
        assert result.passed == 2
        assert result.failed == 0
        assert result.pass_rate == 1.0

    def test_pipeline_with_dimensions(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        case = EvalCase(
            id="dim-test",
            action="exec",
            args={"command": "rm -rf /"},
            assertions=[Assertion(kind=AssertionKind.OK_FALSE)],
            dimensions=(
                AnchoredDimension(
                    name="safety",
                    weight=0.5,
                    assertions=(
                        Assertion(kind=AssertionKind.OK_FALSE),
                        Assertion(kind=AssertionKind.GATE_IS, expected="probity"),
                    ),
                ),
                AnchoredDimension(
                    name="correctness",
                    weight=0.5,
                    assertions=(Assertion(kind=AssertionKind.OK_FALSE),),
                ),
            ),
        )
        result = EvalPipeline(k).run_case(case)
        assert result.passed
        assert result.dimension_scores["safety"] == 5
        assert result.dimension_scores["correctness"] == 5
        assert result.weighted_score == 5.0

    def test_by_tag(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        cases = [
            EvalCase(id="c1", action="Read", assertions=[Assertion(kind=AssertionKind.OK_TRUE)], tags=["smoke"]),
            EvalCase(
                id="c2", action="exec", args={"command": "rm -rf /"},
                assertions=[Assertion(kind=AssertionKind.OK_FALSE)], tags=["security"],
            ),
        ]
        result = run_pipeline(cases, k)
        assert len(result.by_tag("smoke")) == 1
        assert len(result.by_tag("security")) == 1

    def test_error_handling(self, tmp_path: Path) -> None:
        """Pipeline must not crash on kernel errors — it records them."""
        k = _kernel(tmp_path)
        case = EvalCase(
            id="error-case",
            action="NonExistentAction",
            assertions=[Assertion(kind=AssertionKind.OK_TRUE)],
        )
        result = EvalPipeline(k).run_case(case)
        # Should not crash — either passed or has error recorded
        assert isinstance(result, CaseResult)
        assert result.case.id == "error-case"
