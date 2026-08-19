"""Tests for runtime/loop_detector.py."""

from __future__ import annotations

import threading

import pytest

from runtime.loop_detector import LoopDetector, _action_hash


class TestActionHash:
    def test_stable(self):
        h1 = _action_hash("exec", {"cmd": "ls"})
        h2 = _action_hash("exec", {"cmd": "ls"})
        assert h1 == h2

    def test_different_tools_different_hash(self):
        assert _action_hash("exec", {"cmd": "ls"}) != _action_hash("read", {"cmd": "ls"})

    def test_arg_order_independent(self):
        h1 = _action_hash("exec", {"a": 1, "b": 2})
        h2 = _action_hash("exec", {"b": 2, "a": 1})
        assert h1 == h2


class TestLoopDetector:
    def test_first_action_not_loop(self):
        d = LoopDetector()
        assert d.check_and_record("exec", {"cmd": "ls"}) is None

    def test_second_identical_action_blocked(self):
        d = LoopDetector(threshold=2)
        assert d.check_and_record("exec", {"cmd": "ls"}) is None
        hit = d.check_and_record("exec", {"cmd": "ls"})
        assert hit is not None
        assert hit.repeat_count == 2
        assert hit.tool == "exec"

    def test_different_args_not_loop(self):
        d = LoopDetector(threshold=2)
        assert d.check_and_record("exec", {"cmd": "ls"}) is None
        assert d.check_and_record("exec", {"cmd": "pwd"}) is None

    def test_window_eviction(self):
        # window=2, threshold=2: a,b fill the window. Adding c evicts a.
        # Then a again is not a loop because a is no longer in the window.
        d = LoopDetector(window=2, threshold=2)
        d.check_and_record("a", {})
        d.check_and_record("b", {})
        d.check_and_record("c", {})  # evicts a, window now [b, c]
        assert d.check_and_record("a", {}) is None  # a not in window anymore

    def test_is_looping_does_not_record(self):
        d = LoopDetector(threshold=2)
        d.check_and_record("exec", {"cmd": "ls"})
        assert d.is_looping("exec", {"cmd": "ls"}) is True
        # is_looping didn't record, so check_and_record still sees threshold-1=1.
        assert d.size == 1

    def test_reset(self):
        d = LoopDetector(threshold=2)
        d.check_and_record("exec", {"cmd": "ls"})
        d.reset()
        assert d.size == 0
        assert d.check_and_record("exec", {"cmd": "ls"}) is None

    def test_blocks_counter(self):
        d = LoopDetector(threshold=2)
        d.check_and_record("exec", {"cmd": "ls"})
        d.check_and_record("exec", {"cmd": "ls"})  # blocked
        d.check_and_record("exec", {"cmd": "ls"})  # blocked
        assert d.blocks == 2

    def test_stats(self):
        d = LoopDetector(window=5, threshold=3)
        d.check_and_record("a", {})
        d.check_and_record("b", {})
        s = d.stats()
        assert s["window"] == 5
        assert s["threshold"] == 3
        assert s["size"] == 2
        assert s["unique_hashes"] == 2

    def test_invalid_window(self):
        with pytest.raises(ValueError):
            LoopDetector(window=0)

    def test_invalid_threshold(self):
        with pytest.raises(ValueError):
            LoopDetector(threshold=1)

    def test_thread_safety(self):
        d = LoopDetector(threshold=100)
        def worker():
            for i in range(50):
                d.check_and_record("exec", {"i": i})
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # No crash, all 200 unique actions recorded.
        assert d.size <= 10  # window default
