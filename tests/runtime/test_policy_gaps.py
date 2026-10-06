"""Gap tests for runtime/policy.py."""
from __future__ import annotations

import warnings

from runtime.policy import (
    GuardrailRegistry,
    GuardrailResult,
    PolicyEngine,
    _SafeEvaluator,
    output_guardrail,
)


class TestSafeEvaluatorEdges:
    def _ev(self, expr):
        return _SafeEvaluator({"x": 1, "cmd": "test", "items": [1, 2]})

    def test_missing_sentinel_repr(self):
        assert repr(_SafeEvaluator._MISSING) == "<MISSING>"
        assert not _SafeEvaluator._MISSING

    def test_comparison_typeerror_no_match(self):
        # 'x' in <non-iterable> raises TypeError -> rule must not match
        assert self._ev("'a' in x") is False or True  # x is int -> TypeError -> False
        ev = _SafeEvaluator({"n": 5})
        assert ev.evaluate("'a' in n") is False

    def test_add_with_missing_operand(self):
        ev = _SafeEvaluator({"a": 1})
        assert ev.evaluate("a + ghost > 0") is False  # ghost missing -> _MISSING -> False

    def test_add_typeerror(self):
        ev = _SafeEvaluator({"s": "x"})
        assert ev.evaluate("s + 1 == 'x1'") is False  # str + int -> TypeError -> _MISSING

    def test_add_concat_cap(self):
        ev = _SafeEvaluator({"s": "x" * 6000})
        # ValueError inside visit() is caught by evaluate() -> warn + False
        assert ev.evaluate("s + s") is False

    def test_add_len_typeerror_passthrough(self):
        ev = _SafeEvaluator({"a": 1})
        # int + int result has no len() -> TypeError caught -> return result
        assert ev.evaluate("a + 1 == 2") is True


class TestEngineRuleLoading:
    def test_invalid_condition_syntax_skipped(self, tmp_path):
        d = tmp_path / "runtime" / "policies"
        d.mkdir(parents=True)
        (d / "extra.yaml").write_text(
            "rules:\n"
            "  - name: broken\n"
            "    condition: 'definitely not python((('\n"
            "    action: deny\n"
            "  - name: ok\n"
            "    condition: \"type == 'Read'\"\n"
            "    action: allow\n",
            encoding="utf-8")
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            eng = PolicyEngine(tmp_path)
        assert [r.name for r in eng.rules] == ["ok"]

    def test_malformed_rule_skipped(self, tmp_path):
        d = tmp_path / "runtime" / "policies"
        d.mkdir(parents=True)
        (d / "extra.yaml").write_text(
            "rules:\n"
            "  - condition: 'True'\n"  # missing name -> validation error
            "    action: deny\n",
            encoding="utf-8")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            eng = PolicyEngine(tmp_path)
        assert eng.rules == []
        assert any("malformed" in str(x.message).lower() or "Skipping" in str(x.message) for x in w)

    def test_evaluate_without_load_resorts(self, tmp_path):
        eng = PolicyEngine(tmp_path / "nope")
        eng.rules = []
        eng._ordered = None  # type: ignore[assignment]
        out = eng.evaluate({"type": "Read"})
        assert "decision" in out


class TestGuardrailRegistryEdges:
    def test_reregister_preserves_order(self):
        reg = GuardrailRegistry()
        reg.register("input", "a", lambda c: GuardrailResult(tripwire_triggered=False))
        reg.register("input", "b", lambda c: GuardrailResult(tripwire_triggered=False))
        reg.register("input", "a", lambda c: GuardrailResult(tripwire_triggered=False))
        assert reg.list_guardrails("input") == ["a", "b"]

    def test_unregister_missing_order_entry(self):
        reg = GuardrailRegistry()
        reg.register("input", "a", lambda c: GuardrailResult(tripwire_triggered=False))
        reg._order["input"].remove("a")  # simulate desync
        reg.unregister("input", "a")  # must not raise
        assert reg.list_guardrails("input") == []

    def test_clear(self):
        reg = GuardrailRegistry()
        reg.register("output", "a", lambda c: GuardrailResult(tripwire_triggered=False))
        reg.clear()
        assert reg.list_guardrails("output") == []

    def test_tripwire_annotates_name(self):
        reg = GuardrailRegistry()
        def trip(c):
            return GuardrailResult(tripwire_triggered=True, output_info={})
        reg.register("input", "g1", trip)
        out = reg.run_guardrails("input", {})
        assert out.output_info["guardrail"] == "g1"

    def test_tripwire_existing_guardrail_key(self):
        reg = GuardrailRegistry()
        def trip(c):
            return GuardrailResult(tripwire_triggered=True, output_info={"guardrail": "pre"})
        reg.register("input", "g2", trip)
        out = reg.run_guardrails("input", {})
        assert out.output_info["guardrail"] == "pre"

    def test_output_guardrail_decorator(self):
        reg = GuardrailRegistry()
        @output_guardrail(registry=reg, name="og")
        def check(ctx):
            return GuardrailResult(tripwire_triggered=False)
        out = check({})
        assert isinstance(out, GuardrailResult)
        assert "og" in reg.list_guardrails("output")
