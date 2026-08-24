"""Tests for WS-G: Learning loop (LEARN-01 + LEARN-02)."""

from __future__ import annotations

from pathlib import Path

from runtime.hook_lifecycle import HookContext, HookPhase, HookRegistry
from runtime.learning_loop import LearningLoop

# ---------------------------------------------------------------------------
# LEARN-01: Hook bindings
# ---------------------------------------------------------------------------


class TestHookBindings:
    """Learning loop auto-records outcomes via hook bindings."""

    def test_bind_to_hooks_auto_records(self) -> None:
        loop = LearningLoop()
        registry = HookRegistry()
        loop.bind_to_hooks(registry)
        # Simulate a response via run_lifecycle
        ctx = HookContext(action="exec", attributes={})
        ctx.add_result("response", {"ok": True, "gate": "probity"})
        registry.run_phase(HookPhase.POST_RESPONSE, ctx)
        assert loop.outcome_count == 1

    def test_bind_to_hooks_records_error(self) -> None:
        loop = LearningLoop()
        registry = HookRegistry()
        loop.bind_to_hooks(registry)
        ctx = HookContext(action="exec", attributes={})
        ctx.add_error("some error")
        registry.run_phase(HookPhase.ON_ERROR, ctx)
        assert loop.outcome_count == 1
        assert not loop._outcomes[0].success
        assert loop._outcomes[0].gate == "error"

    def test_bind_does_not_crash_on_non_dict_response(self) -> None:
        loop = LearningLoop()
        registry = HookRegistry()
        loop.bind_to_hooks(registry)
        ctx = HookContext(action="exec", attributes={})
        ctx.add_result("response", "not a dict")
        registry.run_phase(HookPhase.POST_RESPONSE, ctx)
        assert loop.outcome_count == 0  # skipped non-dict


# ---------------------------------------------------------------------------
# LEARN-02: Record-consolidate-rank-inject
# ---------------------------------------------------------------------------


class TestRecord:
    """Stage 1: Record action outcomes."""

    def test_record_basic(self) -> None:
        loop = LearningLoop()
        o = loop.record("exec", {"ok": True}, success=True, gate="probity")
        assert o.action == "exec"
        assert o.success is True
        assert o.gate == "probity"
        assert loop.outcome_count == 1

    def test_record_multiple(self) -> None:
        loop = LearningLoop()
        for _ in range(5):
            loop.record("exec", {"ok": True}, success=True, gate="probity")
        assert loop.outcome_count == 5


class TestConsolidate:
    """Stage 2: Consolidate outcomes into patterns."""

    def test_consolidate_groups_by_action_gate(self) -> None:
        loop = LearningLoop()
        loop.record("exec", {"ok": True}, success=True, gate="probity")
        loop.record("exec", {"ok": True}, success=True, gate="probity")
        loop.record("exec", {"ok": False}, success=False, gate="probity")
        loop.record("Read", {"ok": True}, success=True, gate="policy")
        patterns = loop.consolidate()
        assert len(patterns) == 2
        exec_pattern = next(p for p in patterns if p.action == "exec")
        assert exec_pattern.total == 3
        assert exec_pattern.successes == 2
        assert exec_pattern.failures == 1
        assert exec_pattern.success_rate > 0.6

    def test_consolidate_empty(self) -> None:
        loop = LearningLoop()
        patterns = loop.consolidate()
        assert len(patterns) == 0

    def test_consolidate_separate_gates(self) -> None:
        loop = LearningLoop()
        loop.record("exec", {"ok": True}, success=True, gate="probity")
        loop.record("exec", {"ok": True}, success=True, gate="guardian")
        patterns = loop.consolidate()
        assert len(patterns) == 2  # different gates = different patterns


class TestRank:
    """Stage 3: Rank patterns by significance."""

    def test_rank_orders_by_frequency(self) -> None:
        loop = LearningLoop()
        # Pattern A: 5 outcomes, 80% success
        for _ in range(4):
            loop.record("A", {"ok": True}, success=True, gate="g")
        loop.record("A", {"ok": False}, success=False, gate="g")
        # Pattern B: 2 outcomes, 100% success
        for _ in range(2):
            loop.record("B", {"ok": True}, success=True, gate="g")
        ranked = loop.rank()
        # A should rank higher (more total outcomes)
        assert ranked[0].action == "A"

    def test_rank_empty(self) -> None:
        loop = LearningLoop()
        ranked = loop.rank()
        assert len(ranked) == 0


class TestInject:
    """Stage 4: Inject patterns as prompt context."""

    def test_inject_returns_string(self) -> None:
        loop = LearningLoop()
        for _ in range(3):
            loop.record("exec", {"ok": True}, success=True, gate="probity")
        context = loop.inject()
        assert isinstance(context, str)
        assert "Learned Patterns" in context
        assert "exec" in context

    def test_inject_filters_low_frequency(self) -> None:
        loop = LearningLoop()
        loop.record("exec", {"ok": True}, success=True, gate="probity")
        context = loop.inject()
        # Only 1 outcome — should be filtered out (min 2)
        assert context == ""

    def test_inject_top_k_limit(self) -> None:
        loop = LearningLoop()
        for i in range(10):
            for _ in range(3):
                loop.record(f"action_{i}", {"ok": True}, success=True, gate="g")
        context = loop.inject(top_k=3)
        # Should only include 3 patterns
        assert context.count("- ") <= 3

    def test_inject_marks_reliable_vs_unreliable(self) -> None:
        loop = LearningLoop()
        # High success rate
        for _ in range(5):
            loop.record("reliable", {"ok": True}, success=True, gate="g")
        # Low success rate
        for _ in range(5):
            loop.record("unreliable", {"ok": False}, success=False, gate="g")
        context = loop.inject()
        assert "reliable" in context
        assert "unreliable" in context

    def test_inject_empty(self) -> None:
        loop = LearningLoop()
        context = loop.inject()
        assert context == ""


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    """Outcomes persist to disk and load on init."""

    def test_persist_and_load(self, tmp_path: Path) -> None:
        path = tmp_path / "learning.json"
        loop1 = LearningLoop(persist_path=path)
        loop1.record("exec", {"ok": True}, success=True, gate="probity")
        loop1.record("Read", {"ok": True}, success=True, gate="policy")
        # Create new loop with same path
        loop2 = LearningLoop(persist_path=path)
        assert loop2.outcome_count == 2

    def test_no_persist_without_path(self) -> None:
        loop = LearningLoop()
        loop.record("exec", {"ok": True}, success=True, gate="probity")
        # Should not crash — just in-memory
        assert loop.outcome_count == 1

    def test_clear_persists(self, tmp_path: Path) -> None:
        path = tmp_path / "learning.json"
        loop = LearningLoop(persist_path=path)
        loop.record("exec", {"ok": True}, success=True, gate="probity")
        loop.clear()
        # Reload — should be empty
        loop2 = LearningLoop(persist_path=path)
        assert loop2.outcome_count == 0
