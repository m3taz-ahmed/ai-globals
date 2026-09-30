"""Tests for eval/release_gate.py — reliability-as-release-gate (P1.7)."""

from __future__ import annotations

import json
from pathlib import Path

from eval.release_gate import ReleaseGate, load_rollouts


def test_gate_skips_without_evidence(tmp_path: Path) -> None:
    v = ReleaseGate(tmp_path).evaluate()
    assert v.ok and v.skipped


def test_gate_fails_on_kill(tmp_path: Path) -> None:
    g = ReleaseGate(tmp_path)
    for i in range(5):
        g.record_rollout("task-1", "fail", rollout_id=i)
    v = g.evaluate(k_min=5, target=0.5)
    assert not v.ok
    assert v.task_verdicts["task-1"]["verdict"] == "kill"


def test_gate_fails_on_insufficient_power(tmp_path: Path) -> None:
    g = ReleaseGate(tmp_path)
    g.record_rollout("t", "pass")
    v = g.evaluate(k_min=5)
    assert not v.ok
    assert v.task_verdicts["t"]["reason_codes"] == ["LOW_POWER"]


def test_gate_passes_on_confirmed_reliability(tmp_path: Path) -> None:
    g = ReleaseGate(tmp_path)
    for i in range(10):
        g.record_rollout("t", "pass", rollout_id=i)
    v = g.evaluate(k_min=5, target=0.5)
    assert v.ok


def test_security_fail_counts_as_critical(tmp_path: Path) -> None:
    g = ReleaseGate(tmp_path)
    for i in range(9):
        g.record_rollout("t", "pass", rollout_id=i)
    g.record_rollout("t", "security_fail", rollout_id=9)
    v = g.evaluate(k_min=5, target=0.5)
    assert not v.ok  # security-critical event -> insufficient at best


def test_invalid_status_rejected(tmp_path: Path) -> None:
    import pytest

    g = ReleaseGate(tmp_path)
    with pytest.raises(Exception):
        g.record_rollout("t", "bogus")


def test_load_rollouts_skips_malformed(tmp_path: Path) -> None:
    f = tmp_path / "state" / "release_rollouts.jsonl"
    f.parent.mkdir(parents=True)
    f.write_text('{"task_id":"a","status":"pass"}\n\nnot json\n  \n{"task_id":"b"}\n')
    tasks = load_rollouts(f)
    assert list(tasks) == ["a"] and len(tasks["a"]) == 1


def test_main_cli(tmp_path: Path, capsys) -> None:
    from eval.release_gate import main

    assert main(["--project", str(tmp_path)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["skipped"] is True
