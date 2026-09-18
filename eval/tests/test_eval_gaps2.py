"""Gap coverage for eval/: prompt_injection_suite, redteam, reliability, rubric, vibe."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import eval.vibe as vibe
from eval.prompt_injection_suite import EvalReport, PromptInjectionEvalSuite
from eval.redteam import (
    FindingSeverity,
    FindingStatus,
    RedTeamFinding,
    RedTeamRunner,
    SarifReporter,
)
from eval.redteam import (
    main as redteam_main,
)
from eval.reliability import (
    ReliabilityError,
    k_needed_estimate,
    pass_hat_k,
)
from eval.rubric import (
    EvalResult,
    EvalScore,
    ReleaseGateResult,
    blind_conditions,
)


class TestInjectionSuiteGaps:
    def test_empty_report_rates(self):
        r = EvalReport()
        assert r.detection_rate == 0.0
        assert r.false_positive_rate == 0.0
        assert r.containment_rate == 0.0

    def test_run_containment_and_misses(self):
        detector = MagicMock()
        injector = MagicMock()

        class V:
            def __init__(self, inj):
                self.is_injection = inj

        class D:
            hardened_prompt = "safe"
            from runtime.defensive_injection import DefenseStrategy
            strategy = DefenseStrategy.REDIRECT

        # detect all attacks; flag one benign too (false positive)

        def detect(text):
            return V(True)

        detector.detect.side_effect = detect
        injector.inject.return_value = D()
        suite = PromptInjectionEvalSuite(detector=detector, injector=injector)
        report = suite.run()
        assert report.contained_attacks > 0
        assert report.false_positives > 0

    def test_run_missed_attacks(self):
        detector = MagicMock()
        injector = MagicMock()
        verdict = MagicMock()
        verdict.is_injection = False
        detector.detect.return_value = verdict
        suite = PromptInjectionEvalSuite(detector=detector, injector=injector)
        report = suite.run()
        assert report.missed_attacks  # should_detect cases recorded


class TestRedTeamGaps:
    def _runner(self):
        k = MagicMock()
        runner = RedTeamRunner(k)
        return runner

    def _attack(self):
        return {"rule_id": "rt-1", "attack": "a", "action": "Read",
                "expected_gate": "guardian", "description": "d", "severity": "high"}

    def test_run_attack_error(self):
        runner = self._runner()
        res = MagicMock()
        res.error = "boom"
        res.passed = False
        runner.pipeline = MagicMock()
        runner.pipeline.run_case.return_value = res
        f = runner.run_attack(self._attack())
        assert f.status is FindingStatus.ERROR
        assert f.severity is FindingSeverity.WARNING

    def test_run_attack_not_blocked(self):
        runner = self._runner()
        res = MagicMock()
        res.error = None
        res.passed = False
        runner.pipeline = MagicMock()
        runner.pipeline.run_case.return_value = res
        f = runner.run_attack(self._attack())
        assert f.status is FindingStatus.PASSED
        assert f.severity is FindingSeverity.ERROR

    def test_sarif_dedup_rules(self):
        f1 = RedTeamFinding(rule_id="r1", attack="a", action="x",
                            status=FindingStatus.BLOCKED,
                            severity=FindingSeverity.NONE, description="d1",
                            latency_ms=1.0)
        f2 = RedTeamFinding(rule_id="r1", attack="b", action="y",
                            status=FindingStatus.BLOCKED,
                            severity=FindingSeverity.NONE, description="d2",
                            latency_ms=1.0)
        sarif = SarifReporter().to_sarif([f1, f2])
        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        assert len(rules) == 1

    def test_main_clean_and_vuln(self, capsys):
        with (
            patch("runtime.kernel.Kernel", return_value=MagicMock()),
            patch("eval.redteam.RedTeamRunner") as rt,
        ):
            rt.return_value.run_all.return_value = []
            assert redteam_main() == 0
            f = RedTeamFinding(rule_id="r1", attack="a", action="x",
                               status=FindingStatus.PASSED,
                               severity=FindingSeverity.ERROR, description="d",
                               latency_ms=1.0)
            rt.return_value.run_all.return_value = [f]
            assert redteam_main() == 1


class TestReliabilityGaps:
    def test_reliability_error(self):
        with pytest.raises(ReliabilityError):
            raise ReliabilityError("x", {"k": 1})

    def test_k_needed_zero(self):
        assert k_needed_estimate(0, 0, 0.9, 5) is None

    def test_pass_hat_empty(self):
        assert pass_hat_k([]) == 0.0


class TestRubricGaps:
    def test_eval_score_to_dict(self):
        s = EvalScore(case_id="c", trial=1, condition="A",
                      scores={"a": 3}, blocker=False, notes="n")
        d = s.to_dict()
        assert d["case_id"] == "c" and "weighted_score" in d

    def test_eval_result_empty_means(self):
        r = EvalResult()
        assert r.mean_weighted("x") == 0.0
        assert r.mean_dimension("x", "dim") == 0.0
        d = r.to_dict()
        assert "summary" in d

    def test_release_gate_to_dict(self):
        g = ReleaseGateResult(passed=True, reasons=["ok"])
        assert g.to_dict()["passed"] is True

    def test_blind_conditions_dedup(self):
        s1 = EvalScore(case_id="c", trial=1, condition="same", scores={})
        s2 = EvalScore(case_id="c", trial=2, condition="same", scores={})
        out = blind_conditions([s1, s2])
        assert out[0].condition == "A" and out[1].condition == "A"


class TestVibeGaps:
    def test_main_no_scenarios(self, tmp_path, capsys):
        with patch.object(vibe, "load_scenarios", return_value=[]):
            assert vibe.main() == 0
