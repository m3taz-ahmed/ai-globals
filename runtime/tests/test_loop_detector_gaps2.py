"""Second gap pass for runtime/loop_detector.py."""
from __future__ import annotations

from runtime.loop_detector import (
    LoopAction,
    LoopDetector,
    _args_similarity,
    _edit_distance,
    _jaccard_similarity,
)


class TestHelpers:
    def test_jaccard_both_empty(self):
        assert _jaccard_similarity(set(), set()) == 1.0

    def test_jaccard_normal(self):
        assert _jaccard_similarity({"a", "b"}, {"a"}) == 0.5

    def test_edit_distance(self):
        assert _edit_distance("abc", "") == 3
        assert _edit_distance("", "xy") == 2
        assert _edit_distance("kitten", "sitting") == 3
        assert _edit_distance("a", "a") == 0

    def test_args_similarity_huge_payload_uses_jaccard(self):
        big = {"blob": "x" * 25_000}
        # len(s1) > 20_000 -> returns jaccard only (identical dicts -> 1.0)
        assert _args_similarity(big, dict(big)) == 1.0
        other = {"blob": "y" * 25_000}
        sim = _args_similarity(big, other)
        assert 0.0 <= sim <= 1.0


class TestFuzzyAndCycle:
    def _det(self, **kw):
        defaults = {"threshold": 3, "fuzzy_enabled": True, "cycle_enabled": True}
        defaults.update(kw)
        return LoopDetector(**defaults)

    def test_fuzzy_disabled(self):
        d = self._det(fuzzy_enabled=False)
        d.record("t", {"a": 1})
        assert d._detect_fuzzy("t", {"a": 1}) is None

    def test_fuzzy_history_cap(self):
        d = self._det()
        for i in range(210):
            d._tool_history.append(("t", {"i": i}))
        assert d._detect_fuzzy("t", {"i": 0}) is None

    def test_fuzzy_best_sim_keeps_higher(self):
        d = self._det(fuzzy_threshold=0.3)
        d.record("t", {"a": "xxxx"})
        d.record("t", {"a": "x"})  # less similar than first
        res = d._detect_fuzzy("t", {"a": "xxxxx"})
        assert res is not None and res[0] > 0

    def test_cycle_disabled(self):
        d = self._det(cycle_enabled=False)
        assert d._detect_cycle("t", {}) is False

    def test_cycle_too_few_repeats_skipped(self):
        d = self._det(cycle_min_repeats=3)
        # only 2 repeats of a 2-cycle -> repeats < min -> continue path
        d.record("a", {})
        d.record("b", {})
        d.record("a", {})
        d.record("b", {})
        assert d._detect_cycle("a", {}) is False

    def test_cycle_detected(self):
        d = self._det(cycle_min_repeats=3)
        for _ in range(3):
            d.record("a", {})
            d.record("b", {})
        assert d._detect_cycle("a", {}) is True

    def test_is_looping_fuzzy(self):
        d = self._det(threshold=5, fuzzy_threshold=0.5)
        d.record("t", {"a": "same-ish-1"})
        assert d.is_looping("t", {"a": "same-ish-1"}) is True

    def test_is_looping_cycle(self):
        d = self._det(threshold=99, fuzzy_enabled=False, cycle_min_repeats=3)
        for _ in range(3):
            d.record("a", {})
            d.record("b", {})
        assert d.is_looping("a", {}) is True

    def test_record_and_escalate(self):
        d = self._det(threshold=2)
        d.record("t", {})
        # escalate: many consecutive hits
        hit = None
        for _ in range(10):
            hit = d.check_and_record("t", {})
        assert hit is not None and hit.action == LoopAction.ESCALATE

    def test_record_api(self):
        d = self._det()
        d.record("t", {"x": 1})
        assert len(d._tool_history) == 1
