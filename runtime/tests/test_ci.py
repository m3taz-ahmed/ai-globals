"""Tests for CI pipeline runner."""

from __future__ import annotations

from pathlib import Path

from runtime.ci import CIPipeline, run_command


def test_ci_pipeline_reports(tmp_path: Path) -> None:
    # Simulate a project with a passing gate by monkeypatching run_command
    import runtime.ci as ci

    original = ci.run_command
    def fake_run(cmd, cwd):
        return (0, "ok")
    ci.run_command = fake_run
    try:
        pipeline = CIPipeline(tmp_path)
        rc = pipeline.run()
        assert rc == 0
        assert all(r["ok"] for r in pipeline.results)
    finally:
        ci.run_command = original


def test_run_command_file_not_found(tmp_path: Path) -> None:
    """Cover lines 11-21: run_command returns (1, error) when command not found."""
    code, output = run_command(["nonexistent-binary-xyz"], tmp_path)
    assert code == 1
    assert "Command not found" in output


def test_run_command_success(tmp_path: Path) -> None:
    """Cover line 19: run_command returns (returncode, output) on success."""
    import sys

    code, output = run_command([sys.executable, "-c", "print('hello')"], tmp_path)
    assert code == 0
    assert "hello" in output


def test_ci_pipeline_failure_returns_nonzero(tmp_path: Path) -> None:
    """Cover line 48: a failing check sets all_ok=False and returns 1."""
    import runtime.ci as ci

    original = ci.run_command

    call_count = [0]

    def fake_run(cmd, cwd):
        call_count[0] += 1
        # First check fails, rest pass
        if call_count[0] == 1:
            return (1, "lint error")
        return (0, "ok")

    ci.run_command = fake_run
    try:
        pipeline = CIPipeline(tmp_path)
        rc = pipeline.run()
        assert rc == 1
        assert any(not r["ok"] for r in pipeline.results)
    finally:
        ci.run_command = original


def test_ci_pipeline_report(tmp_path: Path) -> None:
    """Cover line 53: report() returns ok status and results list."""
    import runtime.ci as ci

    original = ci.run_command

    def fake_run(cmd, cwd):
        return (0, "ok")

    ci.run_command = fake_run
    try:
        pipeline = CIPipeline(tmp_path)
        pipeline.run()
        report = pipeline.report()
        assert report["ok"] is True
        assert isinstance(report["results"], list)
        assert len(report["results"]) > 0
    finally:
        ci.run_command = original
