"""Tests for eval/chaos.py - fault suite + error budgets (P1.3)."""
from __future__ import annotations

import pytest

from eval.chaos import (
    FAULT_TEMPLATES,
    ChaosRunner,
    ErrorBudget,
    FaultKind,
)


def test_nine_templates_present():
    assert len(FAULT_TEMPLATES) == 9
    kinds = {t.kind for t in FAULT_TEMPLATES}
    assert len(kinds) == 9  # one per kind


def test_runner_baseline_and_report():
    runner = ChaosRunner()
    report = runner.run(lambda p: {"ok": True, "echo": p})
    assert report.baseline_ok
    assert len(report.results) == 9
    d = report.to_dict()
    assert "resilience_score" in d and d["total"] == 9


def test_runner_counts_crash_as_unhandled():
    def target(p: str):
        # Unhandled inside the call surface (graceful handling absent).
        raise ValueError("internal crash")

    runner = ChaosRunner(templates=(FAULT_TEMPLATES[7],))  # partial-data
    report = runner.run(target)
    assert not report.baseline_ok
    # partial-data calls target -> target raises ValueError -> unhandled
    assert report.results[0].handled is False


def test_error_budget_basic():
    b = ErrorBudget(limit=0.1, window=10)
    for _ in range(9):
        b.record(True)
    b.record(False)
    assert b.failure_rate == pytest.approx(0.1)
    assert not b.exhausted
    b.record(False)
    assert b.exhausted
    assert b.burn_rate > 1


def test_error_budget_window_rolls():
    b = ErrorBudget(limit=0.01, window=5)
    for _ in range(4):
        b.record(False)
    for _ in range(5):
        b.record(True)
    assert b.total == 5 and b.failures == 0


def test_injection_fault_marks_result():
    runner = ChaosRunner(
        templates=tuple(t for t in FAULT_TEMPLATES if t.kind is FaultKind.INJECTION)
    )
    report = runner.run(lambda p: "safe result")
    r = report.results[0]
    assert r.kind == "injection" and r.handled


def test_empty_runner_resilience_is_perfect():
    report = ChaosRunner(templates=()).run(lambda p: "ok")
    assert report.results == [] and report.resilience_score == 1.0


def test_partial_data_on_string_target():
    runner = ChaosRunner(
        templates=tuple(t for t in FAULT_TEMPLATES if t.kind is FaultKind.PARTIAL_DATA)
    )
    report = runner.run(lambda p: "a-long-string-result")
    assert report.results[0].detail


def test_error_budget_to_dict():
    b = ErrorBudget(limit=0.05)
    b.record(True)
    d = b.to_dict()
    assert d["limit"] == 0.05 and d["total"] == 1 and d["exhausted"] is False


def test_chaos_main_smoke(capsys):
    from eval.chaos import main

    assert main() in (0, 1)
    out = capsys.readouterr().out
    assert "resilience_score" in out


def test_budget_zero_limit_edge():
    b = ErrorBudget(limit=0.0)
    b.record(True)
    assert b.burn_rate == 0.0
    b.record(False)
    assert b.burn_rate == float("inf")
