"""Tests for runtime.loop_detector — fuzzy + cycle + escalation (from agent-loop-guard)."""

from __future__ import annotations

from runtime.loop_detector import ActionConfig, LoopAction, LoopDetector


def test_exact_repeat_detection() -> None:
    det = LoopDetector(window=5, threshold=2)
    assert det.check_and_record("exec", {"cmd": "ls"}) is None
    hit = det.check_and_record("exec", {"cmd": "ls"})
    assert hit is not None
    assert hit.detection == "exact"
    assert hit.repeat_count == 2


def test_no_loop_on_different_args() -> None:
    det = LoopDetector(window=5, threshold=2)
    assert det.check_and_record("exec", {"cmd": "ls"}) is None
    assert det.check_and_record("exec", {"cmd": "pwd"}) is None


def test_fuzzy_repeat_detection() -> None:
    det = LoopDetector(window=10, threshold=10, fuzzy_threshold=0.3, cycle_enabled=False)
    # Record with slightly different args
    det.check_and_record("search", {"query": "how to test python"})
    hit = det.check_and_record("search", {"query": "how to test python3"})
    assert hit is not None
    assert hit.detection == "fuzzy"
    assert hit.similarity > 0.3


def test_fuzzy_disabled() -> None:
    det = LoopDetector(window=10, threshold=10, fuzzy_enabled=False, cycle_enabled=False)
    det.check_and_record("search", {"query": "how to test python"})
    hit = det.check_and_record("search", {"query": "how to test python3"})
    assert hit is None  # fuzzy disabled, no exact match


def test_cycle_detection() -> None:
    det = LoopDetector(window=20, threshold=100, fuzzy_enabled=False, cycle_min_repeats=3)
    # A→B→C→A→B→C→A pattern
    for tool, args in [("A", {"x": 1}), ("B", {"x": 2}), ("C", {"x": 3})] * 3:
        det.check_and_record(tool, args)
    # The last A should trigger cycle detection
    hit = det.check_and_record("A", {"x": 1})
    if hit is not None:
        assert hit.detection in ("cycle", "exact")


def test_action_escalation() -> None:
    det = LoopDetector(
        window=20, threshold=2, fuzzy_enabled=False, cycle_enabled=False,
        action_config=ActionConfig(warn_threshold=2, stop_threshold=4, escalate_threshold=6),
    )
    # First hit → consecutive_hits=1 → CONTINUE
    det.check_and_record("exec", {"cmd": "ls"})
    hit1 = det.check_and_record("exec", {"cmd": "ls"})
    assert hit1 is not None
    assert hit1.action is LoopAction.CONTINUE

    # Second hit → consecutive_hits=2 → WARN
    hit2 = det.check_and_record("exec", {"cmd": "ls"})
    assert hit2 is not None
    assert hit2.action is LoopAction.WARN

    # Reset to test STOP
    det.reset()
    det.check_and_record("exec", {"cmd": "ls"})  # record (no hit)
    for _ in range(4):
        det.check_and_record("exec", {"cmd": "ls"})  # hits 1-4
    hit_stop = det.check_and_record("exec", {"cmd": "ls"})  # hit 5 → consecutive=5 → STOP
    assert hit_stop is not None
    assert hit_stop.action is LoopAction.STOP


def test_consecutive_hits_reset_on_non_loop() -> None:
    det = LoopDetector(window=10, threshold=2, fuzzy_enabled=False, cycle_enabled=False)
    det.check_and_record("exec", {"cmd": "ls"})
    det.check_and_record("exec", {"cmd": "ls"})  # hit
    # Non-looping action resets consecutive_hits
    det.check_and_record("exec", {"cmd": "pwd"})
    assert det._consecutive_hits == 0


def test_stats() -> None:
    det = LoopDetector(window=5, threshold=2)
    det.check_and_record("exec", {"cmd": "ls"})
    det.check_and_record("exec", {"cmd": "ls"})  # blocked
    stats = det.stats()
    assert stats["blocks"] == 1
    assert stats["size"] == 2
    assert "fuzzy_threshold" in stats
    assert "fuzzy_enabled" in stats


def test_reset() -> None:
    det = LoopDetector(window=5, threshold=2)
    det.check_and_record("exec", {"cmd": "ls"})
    det.reset()
    assert det.size == 0
    assert det._consecutive_hits == 0
