#!/usr/bin/env python3
"""Tests for runtime.preloop."""

from __future__ import annotations

from runtime.preloop import FeedbackLoop, Outcome


def test_score_and_best_action():
    fb = FeedbackLoop()
    for _ in range(3):
        fb.record(Outcome("edit", True, 1.0))
    fb.record(Outcome("edit", False, 0.0))
    fb.record(Outcome("write", True, 0.5))
    assert fb.score("edit") == 0.75
    assert fb.best_action(["edit", "write"]) == "edit"


def test_reflect():
    fb = FeedbackLoop()
    for _ in range(5):
        fb.record(Outcome("read", True, 1.0))
    reflection = fb.reflect("read")
    assert reflection["samples"] == 5
    assert reflection["advice"] == "keep"


def test_capacity_evicts_oldest():
    """Cover line 35: outcomes beyond capacity are popped from the front."""
    fb = FeedbackLoop(capacity=3)
    fb.record(Outcome("a", True, 1.0))
    fb.record(Outcome("b", True, 1.0))
    fb.record(Outcome("c", True, 1.0))
    fb.record(Outcome("d", True, 1.0))
    # "a" should have been evicted
    assert fb.score("a") == 0.5
    assert fb.score("d") == 1.0


def test_score_returns_default_for_no_matches():
    """Cover line 41: score returns 0.5 when no matching outcomes."""
    fb = FeedbackLoop()
    assert fb.score("nonexistent") == 0.5


def test_best_action_empty_list_returns_none():
    """Cover line 48: best_action returns None for empty action list."""
    fb = FeedbackLoop()
    assert fb.best_action([]) is None


def test_reflect_insufficient_samples():
    """Cover line 56: reflect returns 'collect more data' when samples < min_samples."""
    fb = FeedbackLoop()
    fb.record(Outcome("edit", True, 1.0))
    fb.record(Outcome("edit", True, 1.0))
    reflection = fb.reflect("edit", min_samples=3)
    assert reflection["samples"] == 2
    assert reflection["advice"] == "collect more data"
