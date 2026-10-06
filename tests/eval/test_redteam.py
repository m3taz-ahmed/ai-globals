"""Tests for EVAL-W5 (red-team + SARIF) and EVAL-W6 (per-policy breakdown)."""

from __future__ import annotations

import json
from pathlib import Path

from eval.pipeline import Assertion, AssertionKind, EvalCase, run_pipeline
from eval.redteam import (
    FindingSeverity,
    FindingStatus,
    RedTeamFinding,
    RedTeamRunner,
    SarifReporter,
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
        "    message: \"rm -rf forbidden\"\n"
        "  - kind: forbidCommandPattern\n"
        "    name: block-force-push\n"
        "    pattern: \"git\\\\s+push\\\\s+(-f|--force)\"\n"
        "    message: \"Force push forbidden\"\n"
        "  - kind: forbidCommandPattern\n"
        "    name: block-reset-hard\n"
        "    pattern: \"git\\\\s+reset\\\\s+--hard\"\n"
        "    message: \"Hard reset forbidden\"\n"
    )
    return Kernel(tmp_path)


# ---------------------------------------------------------------------------
# EVAL-W5: Red-team + SARIF
# ---------------------------------------------------------------------------


class TestRedTeamRunner:
    """Red-team attacks are correctly blocked by gates."""

    def test_rm_rf_blocked(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        runner = RedTeamRunner(k)
        finding = runner.run_attack({
            "rule_id": "RT-001",
            "action": "exec",
            "args": {"command": "rm -rf /"},
            "attack": "rm -rf /",
            "description": "Destructive command",
            "expected_blocked": True,
            "expected_gate": "probity",
        })
        assert finding.status is FindingStatus.BLOCKED
        assert finding.severity is FindingSeverity.NONE
        assert finding.gate == "probity"

    def test_bash_rm_rf_blocked(self, tmp_path: Path) -> None:
        """GATE-B2: Bash action is normalized and blocked."""
        k = _kernel(tmp_path)
        runner = RedTeamRunner(k)
        finding = runner.run_attack({
            "rule_id": "RT-002",
            "action": "Bash",
            "args": {"command": "rm -rf /"},
            "attack": "Bash rm -rf",
            "description": "Bash bypass attempt",
            "expected_blocked": True,
            "expected_gate": "probity",
        })
        assert finding.status is FindingStatus.BLOCKED
        assert finding.gate == "probity"

    def test_run_all_returns_findings(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        runner = RedTeamRunner(k)
        findings = runner.run_all()
        assert len(findings) > 0
        # All should be blocked (no vulnerabilities)
        for f in findings:
            assert f.status is FindingStatus.BLOCKED, f"Attack {f.rule_id} was not blocked: {f.attack}"


class TestSarifReporter:
    """SARIF output is valid 2.1.0 format."""

    def test_sarif_structure(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        runner = RedTeamRunner(k)
        findings = runner.run_all()
        reporter = SarifReporter()
        sarif = reporter.to_sarif(findings)

        assert sarif["version"] == "2.1.0"
        assert "$schema" in sarif
        assert len(sarif["runs"]) == 1
        run = sarif["runs"][0]
        assert run["tool"]["driver"]["name"] == "aizee-redteam"
        assert len(run["results"]) == len(findings)
        assert "rules" in run["tool"]["driver"]

    def test_sarif_json_serializable(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        runner = RedTeamRunner(k)
        findings = runner.run_all()
        reporter = SarifReporter()
        json_str = reporter.to_json(findings)
        # Must be valid JSON
        parsed = json.loads(json_str)
        assert parsed["version"] == "2.1.0"

    def test_sarif_rule_ids(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        runner = RedTeamRunner(k)
        findings = runner.run_all()
        reporter = SarifReporter()
        sarif = reporter.to_sarif(findings)
        rule_ids = {r["id"] for r in sarif["runs"][0]["tool"]["driver"]["rules"]}
        assert "RT-001" in rule_ids

    def test_vulnerability_severity_is_error(self) -> None:
        """If an attack succeeds, SARIF severity must be 'error'."""
        finding = RedTeamFinding(
            rule_id="RT-X",
            attack="test",
            action="exec",
            status=FindingStatus.PASSED,
            severity=FindingSeverity.ERROR,
            description="vulnerability",
        )
        reporter = SarifReporter()
        sarif = reporter.to_sarif([finding])
        assert sarif["runs"][0]["results"][0]["level"] == "error"


# ---------------------------------------------------------------------------
# EVAL-W6: Per-policy / per-gate breakdown
# ---------------------------------------------------------------------------


class TestPerPolicyBreakdown:
    """Pipeline results can be grouped by gate and policy rule."""

    def test_per_gate_summary(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        cases = [
            EvalCase(
                id="c1", action="Read",
                assertions=[Assertion(kind=AssertionKind.OK_TRUE)],
                tags=["read"],
            ),
            EvalCase(
                id="c2", action="exec", args={"command": "rm -rf /"},
                assertions=[Assertion(kind=AssertionKind.OK_FALSE), Assertion(kind=AssertionKind.GATE_IS, expected="probity")],
                tags=["security"],
            ),
        ]
        result = run_pipeline(cases, k)
        gate_summary = result.per_gate_summary()
        # probity gate should have 1 entry (the rm -rf case)
        assert "probity" in gate_summary
        assert gate_summary["probity"]["total"] == 1
        assert gate_summary["probity"]["passed"] == 1

    def test_per_policy_summary(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        cases = [
            EvalCase(
                id="c1", action="Read",
                assertions=[Assertion(kind=AssertionKind.OK_TRUE)],
            ),
        ]
        result = run_pipeline(cases, k)
        policy_summary = result.per_policy_summary()
        # Read action matches "allow-read" rule
        assert "allow-read" in policy_summary

    def test_by_gate_filter(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        cases = [
            EvalCase(
                id="c1", action="exec", args={"command": "rm -rf /"},
                assertions=[Assertion(kind=AssertionKind.OK_FALSE), Assertion(kind=AssertionKind.GATE_IS, expected="probity")],
            ),
        ]
        result = run_pipeline(cases, k)
        probity_results = result.by_gate("probity")
        assert len(probity_results) == 1

    def test_to_dict_includes_breakdowns(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        cases = [
            EvalCase(id="c1", action="Read", assertions=[Assertion(kind=AssertionKind.OK_TRUE)]),
        ]
        result = run_pipeline(cases, k)
        d = result.to_dict()
        assert "per_gate" in d
        assert "per_policy" in d
