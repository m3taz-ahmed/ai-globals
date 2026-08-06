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
