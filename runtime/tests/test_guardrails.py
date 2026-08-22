"""Tests for the Guardrail Tripwire pattern (from OpenAI Agents SDK).

Covers GuardrailResult, input_guardrail/output_guardrail decorators,
GuardrailRegistry run with pass/fail, tripwire halting, Guardian wiring,
and backward compatibility with PolicyManager/PolicyEngine.
"""

from __future__ import annotations

from pathlib import Path

from runtime.guardian import ActionRequest, DecisionStatus, Guardian
from runtime.policy import (
    GuardrailRegistry,
    GuardrailResult,
    PolicyEngine,
    default_guardrail_registry,
    input_guardrail,
    output_guardrail,
)

# ---------------------------------------------------------------------------
# GuardrailResult construction
# ---------------------------------------------------------------------------


class TestGuardrailResult:
    def test_default_construction(self) -> None:
        result = GuardrailResult(tripwire_triggered=False)
        assert result.tripwire_triggered is False
        assert result.output_info == {}
        assert result.decision == "allow"

    def test_triggered_with_info(self) -> None:
        result = GuardrailResult(
            tripwire_triggered=True,
            output_info={"reason": "destructive action"},
            decision="deny",
        )
        assert result.tripwire_triggered is True
        assert result.output_info["reason"] == "destructive action"
        assert result.decision == "deny"

    def test_output_info_is_independent_per_instance(self) -> None:
        r1 = GuardrailResult(tripwire_triggered=False)
        r2 = GuardrailResult(tripwire_triggered=False)
        r1.output_info["key"] = "value"
        assert "key" not in r2.output_info


# ---------------------------------------------------------------------------
# Decorator registration
# ---------------------------------------------------------------------------


class TestDecoratorRegistration:
    def test_input_guardrail_registers_by_name(self) -> None:
        registry = GuardrailRegistry()

        @input_guardrail("my_input", registry=registry)
        def check(context: dict[str, object]) -> GuardrailResult:
            return GuardrailResult(tripwire_triggered=False)

        assert "my_input" in registry.list_guardrails("input")
        assert "my_input" not in registry.list_guardrails("output")

    def test_output_guardrail_registers_by_name(self) -> None:
        registry = GuardrailRegistry()

        @output_guardrail("my_output", registry=registry)
        def check(context: dict[str, object]) -> GuardrailResult:
            return GuardrailResult(tripwire_triggered=False)

        assert "my_output" in registry.list_guardrails("output")
        assert "my_output" not in registry.list_guardrails("input")

    def test_decorator_defaults_to_function_name(self) -> None:
        registry = GuardrailRegistry()

        @input_guardrail(registry=registry)
        def my_guardrail_func(context: dict[str, object]) -> GuardrailResult:
            return GuardrailResult(tripwire_triggered=False)

        assert "my_guardrail_func" in registry.list_guardrails("input")

    def test_decorated_function_remains_callable(self) -> None:
        registry = GuardrailRegistry()

        @input_guardrail("callable_check", registry=registry)
        def check(context: dict[str, object]) -> GuardrailResult:
            return GuardrailResult(tripwire_triggered=True, output_info={"x": 1})

        result = check({})
        assert result.tripwire_triggered is True
        assert result.output_info == {"x": 1}


# ---------------------------------------------------------------------------
# GuardrailRegistry run with pass/fail
# ---------------------------------------------------------------------------


class TestGuardrailRegistryRun:
    def test_all_pass_returns_allow(self) -> None:
        registry = GuardrailRegistry()

        @input_guardrail("check_a", registry=registry)
        def check_a(context: dict[str, object]) -> GuardrailResult:
            return GuardrailResult(tripwire_triggered=False)

        @input_guardrail("check_b", registry=registry)
        def check_b(context: dict[str, object]) -> GuardrailResult:
            return GuardrailResult(tripwire_triggered=False)

        result = registry.run_guardrails("input", {})
        assert result.tripwire_triggered is False
        assert result.decision == "allow"

    def test_empty_registry_returns_allow(self) -> None:
        registry = GuardrailRegistry()
        result = registry.run_guardrails("input", {})
        assert result.tripwire_triggered is False

    def test_output_phase_runs_output_guardrails_only(self) -> None:
        registry = GuardrailRegistry()

        @input_guardrail("in_check", registry=registry)
        def in_check(context: dict[str, object]) -> GuardrailResult:
            return GuardrailResult(tripwire_triggered=True)

        @output_guardrail("out_check", registry=registry)
        def out_check(context: dict[str, object]) -> GuardrailResult:
            return GuardrailResult(tripwire_triggered=False)

        # Input phase trips, output phase does not.
        in_result = registry.run_guardrails("input", {})
        assert in_result.tripwire_triggered is True

        out_result = registry.run_guardrails("output", {})
        assert out_result.tripwire_triggered is False


# ---------------------------------------------------------------------------
# Tripwire triggering halts chain
# ---------------------------------------------------------------------------


class TestTripwireHaltsChain:
    def test_tripwire_halts_remaining_guardrails(self) -> None:
        registry = GuardrailRegistry()
        call_log: list[str] = []

        @input_guardrail("first", registry=registry)
        def first(context: dict[str, object]) -> GuardrailResult:
            call_log.append("first")
            return GuardrailResult(tripwire_triggered=True, output_info={"reason": "blocked"})

        @input_guardrail("second", registry=registry)
        def second(context: dict[str, object]) -> GuardrailResult:
            call_log.append("second")
            return GuardrailResult(tripwire_triggered=False)

        result = registry.run_guardrails("input", {})
        assert result.tripwire_triggered is True
        assert result.output_info["reason"] == "blocked"
        assert result.output_info["guardrail"] == "first"
        # Second guardrail must NOT have been called.
        assert call_log == ["first"]

    def test_tripwire_in_middle_halts_chain(self) -> None:
        registry = GuardrailRegistry()
        call_log: list[str] = []

        @input_guardrail("a", registry=registry)
        def a(context: dict[str, object]) -> GuardrailResult:
            call_log.append("a")
            return GuardrailResult(tripwire_triggered=False)

        @input_guardrail("b", registry=registry)
        def b(context: dict[str, object]) -> GuardrailResult:
            call_log.append("b")
            return GuardrailResult(tripwire_triggered=True)

        @input_guardrail("c", registry=registry)
        def c(context: dict[str, object]) -> GuardrailResult:
            call_log.append("c")
            return GuardrailResult(tripwire_triggered=False)

        result = registry.run_guardrails("input", {})
        assert result.tripwire_triggered is True
        assert result.output_info["guardrail"] == "b"
        assert call_log == ["a", "b"]

    def test_unregister_removes_guardrail(self) -> None:
        registry = GuardrailRegistry()

        @input_guardrail("temp", registry=registry)
        def temp(context: dict[str, object]) -> GuardrailResult:
            return GuardrailResult(tripwire_triggered=True)

        assert "temp" in registry.list_guardrails("input")
        registry.unregister("input", "temp")
        assert "temp" not in registry.list_guardrails("input")
        result = registry.run_guardrails("input", {})
        assert result.tripwire_triggered is False


# ---------------------------------------------------------------------------
# Guardian wiring (input + output guardrails)
# ---------------------------------------------------------------------------


class TestGuardianWiring:
    def test_input_guardrail_blocks_action(self) -> None:
        registry = GuardrailRegistry()

        @input_guardrail("block_delete", registry=registry)
        def block_delete(context: dict[str, object]) -> GuardrailResult:
            if context.get("tool") == "delete":
                return GuardrailResult(
                    tripwire_triggered=True,
                    output_info={"reason": "delete blocked by guardrail"},
                )
            return GuardrailResult(tripwire_triggered=False)

        g = Guardian([], guardrail_registry=registry)
        decision = g.authorize(ActionRequest(tool="delete"))
        assert decision.status == DecisionStatus.DENY
        assert "guardrail" in decision.rule_name

    def test_input_guardrail_allows_when_no_tripwire(self) -> None:
        registry = GuardrailRegistry()

        @input_guardrail("allow_reads", registry=registry)
        def allow_reads(context: dict[str, object]) -> GuardrailResult:
            return GuardrailResult(tripwire_triggered=False)

        g = Guardian([], guardrail_registry=registry)
        decision = g.authorize(ActionRequest(tool="read"))
        assert decision.status == DecisionStatus.ALLOW

    def test_output_guardrails_return_deny_on_tripwire(self) -> None:
        registry = GuardrailRegistry()

        @output_guardrail("no_secrets", registry=registry)
        def no_secrets(context: dict[str, object]) -> GuardrailResult:
            if "secret" in str(context.get("output", "")):
                return GuardrailResult(tripwire_triggered=True)
            return GuardrailResult(tripwire_triggered=False)

        g = Guardian([], guardrail_registry=registry)
        blocked = g.check_output_guardrails({"output": "contains secret data"})
        assert blocked.status == DecisionStatus.DENY

        ok = g.check_output_guardrails({"output": "clean data"})
        assert ok.status == DecisionStatus.ALLOW

    def test_guardian_without_guardrails_still_works(self) -> None:
        registry = GuardrailRegistry()
        g = Guardian([], guardrail_registry=registry)
        decision = g.authorize(ActionRequest(tool="anything"))
        assert decision.status == DecisionStatus.ALLOW


# ---------------------------------------------------------------------------
# Backward compatibility with PolicyManager / PolicyEngine
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    def test_policy_engine_still_evaluates(self, tmp_path: Path) -> None:
        policy_dir = tmp_path / "runtime" / "policies"
        policy_dir.mkdir(parents=True, exist_ok=True)
        (policy_dir / "default.yaml").write_text(
            "default_action: ask\nrules:\n"
            "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
        )
        engine = PolicyEngine(tmp_path)
        result = engine.can("Read")
        assert result["decision"] == "allow"

    def test_default_registry_is_a_guardrail_registry(self) -> None:
        assert isinstance(default_guardrail_registry, GuardrailRegistry)

    def test_guardian_default_uses_default_registry(self) -> None:
        g = Guardian([])
        assert g.guardrail_registry is default_guardrail_registry
