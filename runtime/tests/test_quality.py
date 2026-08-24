"""Tests for WS-J: Misc quality utilities (W1, W3, W5-W9)."""

from __future__ import annotations

import pytest

from runtime.quality import (
    Bounder,
    FixedRateCostProvider,
    LazyImport,
    OutputEnvelope,
    ReflexionLog,
    Witness,
    WitnessRecorder,
    assert_denied,
    assert_gate,
    assert_has_key,
    assert_ok,
)

# ---------------------------------------------------------------------------
# WS-J W1: Budget providers
# ---------------------------------------------------------------------------


class TestCostProviders:
    """Pluggable cost provider interface."""

    def test_fixed_rate_per_token(self) -> None:
        provider = FixedRateCostProvider()
        cost = provider.cost_per_token("gpt-4", input_tokens=1000, output_tokens=500)
        assert cost > 0
        # gpt-4: 1000 * 0.00003 + 500 * 0.00006 = 0.03 + 0.03 = 0.06
        assert abs(cost - 0.06) < 0.001

    def test_default_rate_for_unknown_model(self) -> None:
        provider = FixedRateCostProvider()
        cost = provider.cost_per_token("unknown-model", 100, 100)
        assert cost > 0  # Uses default rate

    def test_custom_rates(self) -> None:
        provider = FixedRateCostProvider(rates={
            "my-model": {"input": 0.001, "output": 0.002},
            "default": {"input": 0.00001, "output": 0.00002},
        })
        cost = provider.cost_per_token("my-model", 100, 200)
        assert abs(cost - (100 * 0.001 + 200 * 0.002)) < 0.001


# ---------------------------------------------------------------------------
# WS-J W5: Output schemas
# ---------------------------------------------------------------------------


class TestOutputEnvelope:
    """Standardized output envelope."""

    def test_success(self) -> None:
        env = OutputEnvelope.success({"result": "ok"}, tokens=100)
        assert env.ok is True
        assert env.data["result"] == "ok"
        assert env.metadata["tokens"] == 100

    def test_failure(self) -> None:
        env = OutputEnvelope.failure("denied", gate="probity")
        assert env.ok is False
        assert env.error == "denied"
        assert env.gate == "probity"

    def test_to_dict(self) -> None:
        env = OutputEnvelope(ok=True, data={"x": 1}, gate="policy")
        d = env.to_dict()
        assert d["ok"] is True
        assert d["data"]["x"] == 1
        assert d["gate"] == "policy"

    def test_frozen(self) -> None:
        env = OutputEnvelope.success()
        with pytest.raises(AttributeError):
            env.ok = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# WS-J W6: Bounder
# ---------------------------------------------------------------------------


class TestBounder:
    """Output bounding/limiting."""

    def test_bound_text_short(self) -> None:
        b = Bounder(max_chars=100)
        assert b.bound_text("short") == "short"

    def test_bound_text_long(self) -> None:
        b = Bounder(max_chars=10)
        result = b.bound_text("a" * 100)
        assert len(result) <= 25  # 10 chars + truncation marker
        assert "truncated" in result

    def test_bound_list_short(self) -> None:
        b = Bounder(max_items=10)
        assert b.bound_list([1, 2, 3]) == [1, 2, 3]

    def test_bound_list_long(self) -> None:
        b = Bounder(max_items=3)
        result = b.bound_list(list(range(10)))
        assert len(result) == 3

    def test_bound_dict_short(self) -> None:
        b = Bounder(max_items=10)
        d = {"a": 1, "b": 2}
        assert b.bound_dict(d) == d

    def test_bound_dict_long(self) -> None:
        b = Bounder(max_items=2)
        d = {f"key{i}": i for i in range(10)}
        result = b.bound_dict(d)
        assert len(result) <= 3  # 2 items + _truncated marker
        assert "_truncated" in result

    def test_bound_dict_max_depth(self) -> None:
        b = Bounder(max_depth=2)
        d = {"a": {"b": {"c": {"d": 1}}}}
        result = b.bound_dict(d)
        # At depth 2, should be truncated
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# WS-J W7: Witness
# ---------------------------------------------------------------------------


class TestWitness:
    """Execution witness tracking."""

    def test_witness_to_dict(self) -> None:
        w = Witness(
            operation="exec",
            inputs={"command": "ls"},
            outputs={"ok": True},
            success=True,
        )
        d = w.to_dict()
        assert d["operation"] == "exec"
        assert d["success"] is True
        assert d["inputs"]["command"] == "ls"

    def test_witness_recorder(self) -> None:
        recorder = WitnessRecorder()
        recorder.record(Witness(operation="exec", success=True))
        recorder.record(Witness(operation="exec", success=False))
        assert len(recorder.all()) == 2

    def test_witness_by_operation(self) -> None:
        recorder = WitnessRecorder()
        recorder.record(Witness(operation="exec", success=True))
        recorder.record(Witness(operation="Read", success=True))
        assert len(recorder.by_operation("exec")) == 1

    def test_witness_failures(self) -> None:
        recorder = WitnessRecorder()
        recorder.record(Witness(operation="exec", success=True))
        recorder.record(Witness(operation="exec", success=False))
        assert len(recorder.failures()) == 1

    def test_witness_max_limit(self) -> None:
        recorder = WitnessRecorder(max_witnesses=3)
        for i in range(5):
            recorder.record(Witness(operation=f"op{i}", success=True))
        assert len(recorder.all()) == 3  # Only last 3


# ---------------------------------------------------------------------------
# WS-J W8: Lazy imports
# ---------------------------------------------------------------------------


class TestLazyImport:
    """Lazy import helper."""

    def test_lazy_import_defers(self) -> None:
        lazy: LazyImport[Bounder] = LazyImport("runtime.quality.Bounder")
        assert not lazy.is_loaded
        obj = lazy(max_chars=50)
        assert lazy.is_loaded
        assert isinstance(obj, Bounder)

    def test_lazy_import_caches(self) -> None:
        lazy: LazyImport[Bounder] = LazyImport("runtime.quality.Bounder")
        obj1 = lazy(max_chars=50)
        obj2 = lazy(max_chars=100)
        # Both should work (the class is cached, but instances are new)
        assert isinstance(obj1, Bounder)
        assert isinstance(obj2, Bounder)

    def test_lazy_import_invalid_path_raises(self) -> None:
        lazy: LazyImport[Bounder] = LazyImport("nonexistent.module.Class")
        with pytest.raises(ImportError, match="Failed to lazy import"):
            lazy()

    def test_lazy_import_missing_attr_raises(self) -> None:
        lazy: LazyImport[Bounder] = LazyImport("runtime.quality.NonexistentClass")
        with pytest.raises(ImportError, match="Failed to lazy import"):
            lazy()

    def test_lazy_import_too_short_path_raises(self) -> None:
        lazy: LazyImport[Bounder] = LazyImport("singleword")
        with pytest.raises(ImportError, match="Invalid lazy import path"):
            lazy()


# ---------------------------------------------------------------------------
# WS-J W9: Reflexion
# ---------------------------------------------------------------------------


class TestReflexion:
    """Self-reflection helper for learning from failures."""

    def test_add_entry(self) -> None:
        log = ReflexionLog()
        entry = log.add("write tests", "failure", "forgot edge case", "always test edge cases")
        assert entry.task == "write tests"
        assert entry.outcome == "failure"
        assert entry.lesson == "always test edge cases"

    def test_failures(self) -> None:
        log = ReflexionLog()
        log.add("task1", "success", "went well", "nothing")
        log.add("task2", "failure", "missed something", "check more carefully")
        assert len(log.failures()) == 1
        assert len(log.successes()) == 1

    def test_lessons(self) -> None:
        log = ReflexionLog()
        log.add("task1", "failure", "r1", "lesson1")
        log.add("task2", "failure", "r2", "lesson2")
        log.add("task3", "success", "r3", "lesson3")
        lessons = log.lessons()
        assert len(lessons) == 2
        assert "lesson1" in lessons
        assert "lesson2" in lessons

    def test_summary(self) -> None:
        log = ReflexionLog()
        log.add("t1", "success", "", "")
        log.add("t2", "failure", "", "")
        log.add("t3", "failure", "", "")
        s = log.summary()
        assert s["total"] == 3
        assert s["failures"] == 2
        assert s["successes"] == 1
        assert abs(s["failure_rate"] - 2 / 3) < 0.01

    def test_max_entries(self) -> None:
        log = ReflexionLog(max_entries=3)
        for i in range(5):
            log.add(f"task{i}", "success", "", "")
        assert len(log.all()) == 3


# ---------------------------------------------------------------------------
# WS-J W3: Assertion helpers
# ---------------------------------------------------------------------------


class TestAssertionHelpers:
    """Test assertion helpers."""

    def test_assert_ok_passes(self) -> None:
        assert_ok({"ok": True})

    def test_assert_ok_fails(self) -> None:
        with pytest.raises(AssertionError):
            assert_ok({"ok": False})

    def test_assert_denied_passes(self) -> None:
        assert_denied({"ok": False})

    def test_assert_denied_fails(self) -> None:
        with pytest.raises(AssertionError):
            assert_denied({"ok": True})

    def test_assert_gate_passes(self) -> None:
        assert_gate({"gate": "probity"}, "probity")

    def test_assert_gate_fails(self) -> None:
        with pytest.raises(AssertionError):
            assert_gate({"gate": "policy"}, "probity")

    def test_assert_has_key_passes(self) -> None:
        assert_has_key({"data": 1}, "data")

    def test_assert_has_key_fails(self) -> None:
        with pytest.raises(AssertionError):
            assert_has_key({"data": 1}, "missing")
