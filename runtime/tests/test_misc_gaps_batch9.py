"""Gap coverage batch 9: spec/models, skill_routing, rule_frontmatter, prompt_gate,
agent_circuit_breaker, tracing, ci."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import runtime.tracing_otel as otel
from runtime.agent_circuit_breaker import CbConfig, CbState, SemanticCircuitBreaker
from runtime.ci import CIPipeline, run_command
from runtime.prompt_gate import PromptGate, PromptRisk, PromptVerdict, _default_model_grader, guard
from runtime.rule_frontmatter import (
    RuleFrontmatter,
    _match_personas,
    _match_triggers,
    matches_context,
)
from runtime.skill_routing import PersonaDetectorV2
from runtime.spec.models import Spec
from runtime.tracing import ConsoleSpanExporter, Span


class TestSpecFromDict:
    def test_non_dict(self) -> None:
        with pytest.raises(ValueError, match="mapping"):
            Spec.from_dict("x")  # type: ignore[arg-type]

    def test_bad_plan(self) -> None:
        with pytest.raises(ValueError, match="plan"):
            Spec.from_dict({"id": "s", "title": "t", "plan": "x"})

    def test_bad_history(self) -> None:
        with pytest.raises(ValueError, match="state_history"):
            Spec.from_dict({"id": "s", "title": "t", "state_history": "x"})

    def test_bad_lists(self) -> None:
        with pytest.raises(ValueError, match="lists"):
            Spec.from_dict({"id": "s", "title": "t", "requirements": "x"})
        with pytest.raises(ValueError, match="lists"):
            Spec.from_dict({"id": "s", "title": "t", "tasks": {}})
        with pytest.raises(ValueError, match="lists"):
            Spec.from_dict({"id": "s", "title": "t", "deltas": "x"})


class TestSkillRouting:
    def test_single_score_confidence(self) -> None:
        det = PersonaDetectorV2()
        result = det.detect("review my laravel code")
        assert result.confidence >= 0.0

    def test_empty_scores(self) -> None:
        det = PersonaDetectorV2(detector=MagicMock())
        det.detector.detect_multiple.return_value = {"scores": {}, "persona": None}
        result = det.detect("zzz nothing matches at all qqq")
        assert result.confidence == 0.0 and result.ambiguous is False

    def test_single_score_branch(self) -> None:
        det = PersonaDetectorV2(detector=MagicMock())
        det.detector.detect_multiple.return_value = {
            "scores": {"DEV": 0.9}, "persona": "DEV",
        }
        result = det.detect("x")
        assert result.confidence == 0.9 and result.ambiguous is False


class TestRuleFrontmatter:
    def test_personas_non_str_skipped(self) -> None:
        fm = RuleFrontmatter(personas=["dev"])
        assert not _match_personas(fm.personas, {"personas": [123]})
        assert _match_personas(fm.personas, {"personas": [123, "dev"]})

    def test_triggers_text_keys(self) -> None:
        assert _match_triggers(["deploy"], {"task": "please deploy now"})
        assert _match_triggers(["deploy"], {"query": "nothing"}) is False
        assert _match_triggers(["x"], {}) is False

    def test_stack_str_wrapped(self) -> None:
        fm = RuleFrontmatter(tech_stack=["laravel"])
        assert matches_context(fm, {"stack": "laravel"})
        fm2 = RuleFrontmatter(tech_stack=["laravel"])
        assert not matches_context(fm2, {"stack": "rails"})


class TestPromptGate:
    def test_suspicious_verdict(self) -> None:
        v = PromptVerdict(risk=PromptRisk.SUSPICIOUS, reason="r", score=5)
        gv = v.to_gate_verdict()
        assert gv.decision.value == "require_approval"

    def test_blocked_property(self) -> None:
        assert PromptGate().blocked is False

    def test_rubric_empty_words(self) -> None:
        assert _default_model_grader("anything", "a an is") == "FAIL"

    def test_guard_suspicious(self) -> None:
        gate = PromptGate()
        # find a prompt that lands SUSPICIOUS (score between thresholds)
        for probe in [
            "sudo make me a sandwich",
            "please access credentials",
            "steal the token now",
        ]:
            v = gate.evaluate(probe)
            if v.risk is PromptRisk.SUSPICIOUS:
                res = guard(probe)
                assert res.pass_ is False and res.score == 0.5
                return
        pytest.skip("no suspicious prompt found among probes")


class TestCircuitBreaker:
    def test_can_execute_half_open(self) -> None:
        cb = SemanticCircuitBreaker(CbConfig(half_open_max_calls=2))
        cb._state = CbState.HALF_OPEN
        cb._half_open_calls = 0
        assert cb.can_execute()
        cb._half_open_calls = 2
        assert not cb.can_execute()

    def test_maybe_close_fails_trips_open(self) -> None:
        cb = SemanticCircuitBreaker(CbConfig(half_open_max_calls=1, success_threshold=0.9))
        cb._state = CbState.HALF_OPEN
        cb._half_open_calls = 1
        cb._half_open_successes = 0
        cb._maybe_close()
        assert cb.state() is CbState.OPEN

    def test_should_half_open_no_timestamp(self) -> None:
        cb = SemanticCircuitBreaker()
        cb._opened_at = None
        assert cb._should_half_open() is False

    def test_transition_same_state_noop(self) -> None:
        cb = SemanticCircuitBreaker()
        fired: list[str] = []
        cb.on_state_change(lambda old, new: fired.append(new.value))
        cb._transition(CbState.CLOSED)
        assert fired == []


class TestTracing:
    def test_console_exporter_otlp(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        recorded: list[tuple[str, float | None]] = []
        monkeypatch.setattr(otel, "get_tracer", lambda: object())
        monkeypatch.setattr(
            otel, "record_span",
            lambda name, attributes=None, duration_s=None: recorded.append((name, duration_s)),
        )
        exp = ConsoleSpanExporter(tmp_path / "spans.jsonl")
        span = Span(name="s1", trace_id="t", span_id="i", parent_id=None,
                    kind="internal", start_time=1.0, attributes={})
        span.end_time = 2.5
        exp.on_end(span)
        span2 = Span(name="s2", trace_id="t", span_id="i2", parent_id=None,
                     kind="internal", start_time=0.0, attributes={})
        exp.on_end(span2)
        assert recorded[0] == ("s1", 1.5) and recorded[1] == ("s2", None)


class TestCI:
    def test_run_command_bad_cwd(self, tmp_path: Path) -> None:
        code, out = run_command(["python", "-V"], tmp_path / "nope")
        assert code == 1 and "Invalid cwd" in out

    def test_run_command_oserror(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import subprocess

        def boom(*a: object, **k: object) -> None:
            raise OSError("denied")

        monkeypatch.setattr(subprocess, "run", boom)
        code, out = run_command(["x"], tmp_path)
        assert code == 1 and "Command failed" in out

    def test_report_empty(self, tmp_path: Path) -> None:
        assert CIPipeline(tmp_path).report()["ok"] is False

    def test_run_skip_pytest(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import runtime.ci as ci_mod

        calls: list[str] = []
        monkeypatch.setattr(
            ci_mod, "run_command",
            lambda cmd, cwd: (calls.append(cmd[2] if len(cmd) > 2 else ""), (0, "ok"))[1],
        )
        rc = CIPipeline(tmp_path).run(skip_pytest=True)
        assert rc == 0
        assert "pytest" not in calls
