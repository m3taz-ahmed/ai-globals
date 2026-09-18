"""Tests for runtime/funnel_tracker.py — funnel drop-off analytics."""

from __future__ import annotations

import pytest

from runtime.funnel_tracker import Funnel
from runtime.schemas import ValidationError


def _funnel(*names: str) -> Funnel:
    f = Funnel("test")
    for n in names:
        f.add_step(n)
    return f


class TestAddStep:
    def test_adds_in_order(self):
        f = _funnel("visit", "signup", "pay")
        assert [s.name for s in f.steps] == ["visit", "signup", "pay"]

    def test_duplicate_rejected(self):
        f = _funnel("visit")
        with pytest.raises(ValidationError, match="duplicate"):
            f.add_step("visit")

    def test_default_name(self):
        assert Funnel().name == "funnel"


class TestRecord:
    def test_bare_step_index_prefix(self):
        f = _funnel("a", "b", "c")
        f.record({"step_index": 1})
        assert [s.reached for s in f.steps] == [1, 1, 0]

    def test_last_step_counts_all(self):
        f = _funnel("a", "b", "c")
        f.record({"step_index": 2})
        assert [s.reached for s in f.steps] == [1, 1, 1]

    def test_missing_step_index(self):
        f = _funnel("a")
        with pytest.raises(ValidationError, match="step_index"):
            f.record({})
        with pytest.raises(ValidationError):
            f.record("notadict")

    def test_negative_index(self):
        f = _funnel("a")
        with pytest.raises(ValidationError, match="non-negative"):
            f.record({"step_index": -1})

    def test_non_int_index(self):
        f = _funnel("a")
        with pytest.raises(ValidationError):
            f.record({"step_index": "0"})

    def test_out_of_range(self):
        f = _funnel("a")
        with pytest.raises(ValidationError, match="out of range"):
            f.record({"step_index": 5})

    def test_reached_list_contiguous(self):
        f = _funnel("a", "b", "c")
        # reached [0, 2] — gap at 1, so only step 0 counted (non-contiguous)
        f.record({"step_index": 2, "reached": [0, 2]})
        assert [s.reached for s in f.steps] == [1, 0, 0]

    def test_reached_list_full_prefix(self):
        f = _funnel("a", "b", "c")
        f.record({"step_index": 2, "reached": [0, 1, 2]})
        assert [s.reached for s in f.steps] == [1, 1, 1]

    def test_reached_by_name(self):
        f = _funnel("visit", "signup")
        f.record({"step_index": 1, "reached": ["visit", "signup"]})
        assert [s.reached for s in f.steps] == [1, 1]

    def test_reached_invalid_type(self):
        f = _funnel("a")
        with pytest.raises(ValidationError, match="reached"):
            f.record({"step_index": 0, "reached": "notalist"})

    def test_steps_alias(self):
        f = _funnel("a", "b")
        f.record({"step_index": 1, "steps": [0, 1]})
        assert [s.reached for s in f.steps] == [1, 1]

    def test_user_dedup(self):
        f = _funnel("a", "b")
        f.record({"step_index": 0, "user_id": "u1"})
        f.record({"step_index": 0, "user_id": "u1"})
        f.record({"step_index": 0, "user_id": "u2"})
        assert f.steps[0].reached == 2

    def test_user_key_variants(self):
        f = _funnel("a")
        f.record({"step_index": 0, "user": "u1"})
        f.record({"step_index": 0, "id": "u2"})
        assert f.steps[0].reached == 2

    def test_anonymous_counts_each(self):
        f = _funnel("a")
        f.record({"step_index": 0})
        f.record({"step_index": 0})
        assert f.steps[0].reached == 2


class TestDropoff:
    def test_empty_funnel(self):
        assert _funnel("a", "b").dropoff() == [
            {"step": "a", "reached": 0, "conversion_from_prev": 0.0, "dropoff_from_prev": 0.0},
            {"step": "b", "reached": 0, "conversion_from_prev": 0.0, "dropoff_from_prev": 1.0},
        ]

    def test_baseline_is_one(self):
        f = _funnel("a", "b")
        f.record({"step_index": 0})
        d = f.dropoff()
        assert d[0]["conversion_from_prev"] == 1.0
        assert d[1]["dropoff_from_prev"] == 1.0  # nobody reached b

    def test_typical_funnel(self):
        f = _funnel("visit", "signup", "pay")
        for _ in range(10):
            f.record({"step_index": 0})
        for _ in range(5):
            f.record({"step_index": 1})
        for _ in range(2):
            f.record({"step_index": 2})
        d = f.dropoff()
        assert d[0]["reached"] == 17  # every record counts the prefix
        assert d[1]["reached"] == 7
        assert d[1]["conversion_from_prev"] == round(7 / 17, 4)
        assert d[2]["reached"] == 2
        assert d[2]["dropoff_from_prev"] == round(1 - 2 / 7, 4)

    def test_single_step(self):
        f = _funnel("only")
        f.record({"step_index": 0})
        d = f.dropoff()
        assert len(d) == 1 and d[0]["conversion_from_prev"] == 1.0
