"""Tests for runtime/trajectory.py."""

from __future__ import annotations

import pytest

from runtime.trajectory import (
    RunStatus,
    StepStatus,
    TrajectoryTracker,
)


class TestTrajectoryTracker:
    def test_start_run_returns_id(self):
        t = TrajectoryTracker("add auth")
        rid = t.start_run(derived_intent="login form")
        assert rid in t.runs
        assert t.runs[rid].derived_intent == "login form"

    def test_explicit_run_id(self):
        t = TrajectoryTracker("x")
        t.start_run(run_id="r1")
        assert "r1" in t.runs

    def test_record_step(self):
        t = TrajectoryTracker("x")
        rid = t.start_run()
        step = t.record_step(rid, "write", StepStatus.OK, file="a.py")
        assert step.action == "write"
        run = t.get_run(rid)
        assert run is not None
        assert "a.py" in run.modified_files

    def test_unknown_run_raises(self):
        t = TrajectoryTracker("x")
        with pytest.raises(KeyError):
            t.record_step("nope", "write", StepStatus.OK)

    def test_stall_detection(self):
        t = TrajectoryTracker("x", stall_threshold=3)
        rid = t.start_run()
        t.record_step(rid, "write", StepStatus.FAILED)
        t.record_step(rid, "write", StepStatus.FAILED)
        assert not t.is_stalled(rid)
        t.record_step(rid, "write", StepStatus.FAILED)
        assert t.is_stalled(rid)
        stalled = t.get_run(rid)
        assert stalled is not None
        assert stalled.status is RunStatus.STALLED

    def test_ok_step_resets_contiguous_failures(self):
        t = TrajectoryTracker("x", stall_threshold=3)
        rid = t.start_run()
        t.record_step(rid, "write", StepStatus.FAILED)
        t.record_step(rid, "write", StepStatus.FAILED)
        t.record_step(rid, "write", StepStatus.OK)
        t.record_step(rid, "write", StepStatus.FAILED)
        assert not t.is_stalled(rid)
        run1 = t.get_run(rid)
        assert run1 is not None
        assert run1.contiguous_failures == 1

    def test_has_progress(self):
        t = TrajectoryTracker("x")
        rid = t.start_run()
        t.record_step(rid, "write", StepStatus.FAILED)
        run_a = t.get_run(rid)
        assert run_a is not None
        assert not run_a.has_progress
        t.record_step(rid, "write", StepStatus.OK)
        run_b = t.get_run(rid)
        assert run_b is not None
        assert run_b.has_progress

    def test_mark_converged(self):
        t = TrajectoryTracker("x")
        rid = t.start_run()
        t.mark_converged(rid, evidence="tests pass")
        converged = t.get_run(rid)
        assert converged is not None
        assert converged.status is RunStatus.CONVERGED
        assert converged.checks["convergence_evidence"] == "tests pass"

    def test_abort(self):
        t = TrajectoryTracker("x")
        rid = t.start_run()
        t.abort(rid, "user cancelled")
        aborted = t.get_run(rid)
        assert aborted is not None
        assert aborted.status is RunStatus.ABORTED

    def test_record_assumption(self):
        t = TrajectoryTracker("x")
        rid = t.start_run()
        t.record_assumption(rid, "user wants JWT")
        asum = t.get_run(rid)
        assert asum is not None
        assert len(asum.assumptions) == 1

    def test_status_summary(self):
        t = TrajectoryTracker("x")
        rid = t.start_run()
        t.record_step(rid, "write", StepStatus.OK, file="a.py", check="ruff")
        s = t.status(rid)
        assert s["steps"] == 1
        assert s["has_progress"] is True
        assert s["checks"] == {"ruff": "ok"}

    def test_inspected_vs_modified_files(self):
        t = TrajectoryTracker("x")
        rid = t.start_run()
        t.record_step(rid, "read", StepStatus.FAILED, file="b.py")
        t.record_step(rid, "write", StepStatus.OK, file="a.py")
        run = t.get_run(rid)
        assert run is not None
        assert "b.py" in run.inspected_files
        assert "a.py" in run.modified_files

    def test_invalid_threshold(self):
        with pytest.raises(ValueError):
            TrajectoryTracker("x", stall_threshold=0)
