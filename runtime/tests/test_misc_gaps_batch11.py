"""Coverage gap tests - batch 11.

Targets: spec/models from_dict validators, skill_routing confidence branches,
rule_frontmatter matchers, prompt_gate residual branches,
agent_circuit_breaker state paths, tracing OTLP forwarding,
provider_registry env config, ci run_command/report edges.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from runtime.agent_circuit_breaker import (
    CbConfig,
    CbState,
    SemanticCircuitBreaker,
)
from runtime.prompt_gate import PromptGate, PromptRisk, _default_model_grader, guard
from runtime.rule_frontmatter import (
    RuleFrontmatter,
    _match_personas,
    _match_triggers,
    matches_context,
)
from runtime.schemas import GateDecision
from runtime.skill_routing import PersonaDetectorV2
from runtime.spec.models import Spec


class TestSpecModelValidators:
    def test_from_dict_not_mapping(self) -> None:
        with pytest.raises(ValueError, match="mapping"):
            Spec.from_dict(["not", "a", "dict"])  # type: ignore[arg-type]

    def test_from_dict_plan_not_mapping(self) -> None:
        with pytest.raises(ValueError, match="'plan'"):
            Spec.from_dict({"id": "s", "title": "t", "plan": "oops"})

    def test_from_dict_history_not_list(self) -> None:
        with pytest.raises(ValueError, match="state_history"):
            Spec.from_dict({"id": "s", "title": "t", "state_history": "oops"})

    def test_from_dict_requirements_not_list(self) -> None:
        with pytest.raises(ValueError, match="lists"):
            Spec.from_dict({"id": "s", "title": "t", "requirements": "oops"})


class _StubDetector:
    def __init__(self, raw: dict[str, Any]) -> None:
        self._raw = raw

    def detect_multiple(self, text: str, max_personas: int = 3) -> dict[str, Any]:
        return self._raw


class TestSkillRoutingDetect:
    def _detect(self, raw: dict[str, Any]) -> Any:
        det = PersonaDetectorV2(detector=_StubDetector(raw))  # type: ignore[arg-type]
        return det.detect("anything")

    def test_ambiguous_when_scores_close(self) -> None:
        out = self._detect({
            "persona": "dev", "personas": ["dev"],
            "scores": {"dev": 0.55, "ops": 0.50},
        })
        assert out.ambiguous is True
        assert "Ambiguous" in out.reason

    def test_single_score_not_ambiguous(self) -> None:
        out = self._detect({
            "persona": "dev", "personas": ["dev"],
            "scores": {"dev": 0.8},
        })
        assert out.ambiguous is False
        assert out.confidence == pytest.approx(0.8)
        assert "High confidence" in out.reason

    def test_no_scores_zero_confidence(self) -> None:
        out = self._detect({"persona": "dev", "personas": [], "scores": {}})
        assert out.confidence == 0.0
        assert out.ambiguous is False
        assert "Low confidence" in out.reason

    def test_moderate_confidence_reason(self) -> None:
        out = self._detect({
            "persona": "dev", "personas": ["dev"],
            "scores": {"dev": 0.4, "ops": 0.1},
        })
        assert out.ambiguous is False
        assert "Moderate confidence" in out.reason


class TestRuleFrontmatterMatchers:
    def test_match_personas_non_str_entry_skipped(self) -> None:
        assert _match_personas(["dev"], {"personas": ["dev", 42, None]}) is True

    def test_match_triggers_multi_key_text(self) -> None:
        ctx = {"task": "fix the", "query": "database", "prompt": 123}
        assert _match_triggers(["database"], ctx) is True

    def test_match_triggers_no_text(self) -> None:
        assert _match_triggers(["x"], {"task": 42}) is False

    def test_matches_context_tech_stack_str(self) -> None:
        fm = RuleFrontmatter(tech_stack=["laravel"])
        assert matches_context(fm, {"stack": "laravel"}) is True
        assert matches_context(fm, {"stack": "django"}) is False


class TestPromptGateResiduals:
    def test_suspicious_to_gate_verdict(self) -> None:
        gate = PromptGate()
        verdict = gate.evaluate("sudo make me a sandwich")
        assert verdict.risk is PromptRisk.SUSPICIOUS
        gv = verdict.to_gate_verdict()
        assert gv.decision is GateDecision.REQUIRE_APPROVAL
        assert gv.gate == "prompt_gate"

    def test_blocked_property_stateless(self) -> None:
        assert PromptGate().blocked is False

    def test_default_grader_empty_rubric(self) -> None:
        assert _default_model_grader("any output", "a b c") == "FAIL"

    def test_guard_suspicious_branch(self) -> None:
        res = guard("sudo make me a sandwich")
        assert res.pass_ is False
        assert res.score == 0.5
        assert "suspicious" in res.reason


class TestCircuitBreakerResiduals:
    def _breaker(self, **kw: Any) -> SemanticCircuitBreaker:
        return SemanticCircuitBreaker(CbConfig(**kw))

    def test_half_open_probe_limit(self) -> None:
        cb = self._breaker(
            failure_threshold=0.5, min_calls=1,
            open_timeout=0.001, half_open_max_calls=1,
        )
        cb.record_failure()
        assert cb.state() is CbState.OPEN
        cb._opened_at = 0.0  # force elapsed
        assert cb.can_execute() is True  # transitions to HALF_OPEN
        cb._half_open_calls = cb._config.half_open_max_calls
        assert cb.can_execute() is False  # probe budget exhausted

    def test_maybe_close_failure_reopens(self) -> None:
        cb = self._breaker(half_open_max_calls=1, success_threshold=0.9)
        cb._state = CbState.HALF_OPEN
        cb._half_open_calls = 1
        cb._half_open_successes = 0
        cb._maybe_close()
        assert cb.state() is CbState.OPEN

    def test_should_half_open_no_opened_at(self) -> None:
        cb = self._breaker()
        cb._opened_at = None
        assert cb._should_half_open() is False

    def test_transition_same_state_noop(self) -> None:
        cb = self._breaker()
        fired: list[tuple[CbState, CbState]] = []
        cb.on_state_change(lambda o, n: fired.append((o, n)))
        cb._transition(CbState.CLOSED)  # already CLOSED
        assert fired == []


class TestTracingOTLP:
    def test_span_forwarded_to_otlp(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import runtime.tracing as tr

        recorded: list[tuple[str, float | None]] = []

        class _Tracer:
            pass

        monkeypatch.setattr("runtime.tracing_otel.get_tracer", lambda: _Tracer())
        monkeypatch.setattr(
            "runtime.tracing_otel.record_span",
            lambda name, attributes=None, duration_s=None: recorded.append(
                (name, duration_s)
            ),
        )
        proc = tr.ConsoleSpanExporter(tmp_path / "spans.jsonl")
        span = tr.Span(trace_id="t", span_id="1", parent_id=None, name="s1", kind="internal", start_time=10.0, end_time=12.5)
        proc.on_end(span)
        assert recorded == [("s1", 2.5)]

    def test_span_no_end_time(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import runtime.tracing as tr

        recorded: list[tuple[str, float | None]] = []
        monkeypatch.setattr("runtime.tracing_otel.get_tracer", lambda: object())
        monkeypatch.setattr(
            "runtime.tracing_otel.record_span",
            lambda name, attributes=None, duration_s=None: recorded.append(
                (name, duration_s)
            ),
        )
        proc = tr.ConsoleSpanExporter(tmp_path / "spans.jsonl")
        span = tr.Span(trace_id="t", span_id="2", parent_id=None, name="s2", kind="internal", start_time=10.0, end_time=None)
        proc.on_end(span)
        assert recorded == [("s2", None)]


class TestProviderRegistryResiduals:
    def test_env_config_all_sections(self) -> None:
        from runtime.provider_registry import ProviderSpec

        spec = ProviderSpec(
            name="p", display_name="P", modalities=("language",), required_env=("A",), required_any_env=("B", "C"), optional_env=("D",),
        )
        cfg = spec.env_config()
        assert cfg == {"required": ["A"], "required_any": ["B", "C"],
                       "optional": ["D"]}

    def test_get_cheapest_no_candidates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import runtime.provider_registry as pr

        monkeypatch.setattr(pr, "get_configured_providers", lambda: [])
        assert pr.get_cheapest_provider("language") is None


class TestCIResiduals:
    def test_run_command_invalid_cwd(self, tmp_path: Path) -> None:
        from runtime.ci import run_command

        code, out = run_command(["echo", "hi"], tmp_path / "nope")
        assert code == 1
        assert "Invalid cwd" in out

    def test_run_command_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import subprocess

        from runtime.ci import run_command

        def boom(*a: object, **k: object) -> object:
            raise PermissionError("denied")

        monkeypatch.setattr(subprocess, "run", boom)
        code, out = run_command(["x"], tmp_path)
        assert code == 1
        assert "Command failed" in out

    def test_report_no_runs(self, tmp_path: Path) -> None:
        from runtime.ci import CIPipeline

        rep = CIPipeline(tmp_path).report()
        assert rep["ok"] is False
        assert rep["reason"] == "no runs recorded"

