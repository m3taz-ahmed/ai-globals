"""Tests for CI pipeline runner."""

from __future__ import annotations

from pathlib import Path

from runtime.ci import CIPipeline


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
