"""Tests for runtime/durable.py — durable execution with deterministic replay."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from runtime.durable import (
    DurableError,
    DurableExecutor,
    DurableStep,
    DurableWorkflow,
    StepStatus,
)


@pytest.fixture()
def state_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture()
def executor(state_dir):
    return DurableExecutor(state_dir)


def _steps(n: int = 2):
    return [{"step_id": f"s{i}", "name": f"step{i}", "args": {"i": i}} for i in range(n)]


class TestExecution:
    def test_happy_path(self, executor):
        wf = executor.execute("wf1", _steps(2), lambda s: {"ok": s.step_id})
        assert wf.status == "completed"
        assert all(s.status is StepStatus.COMPLETED for s in wf.steps)
        assert wf.steps[0].result == {"ok": "s0"}
        assert wf.completed_at is not None

    def test_step_args_passed(self, executor):
        seen = []
        executor.execute("wf2", _steps(2), lambda s: seen.append(s.args["i"]))
        assert seen == [0, 1]

    def test_default_step_ids(self, executor):
        wf = executor.execute("wf3", [{"args": {}}, {}], lambda s: 1)
        assert wf.steps[0].step_id == "step-0"
        assert wf.steps[1].step_id == "step-1"

    def test_failure_marks_workflow(self, executor):
        def handler(step):
            if step.step_id == "s1":
                raise RuntimeError("boom")
            return "ok"
        wf = executor.execute("wf4", _steps(3), handler)
        assert wf.status == "failed"
        assert wf.steps[1].status is StepStatus.FAILED
        assert wf.steps[1].error == "boom"
        assert wf.steps[2].status is StepStatus.PENDING  # never ran

    def test_compensation_runs_reverse(self, executor):
        order = []
        def handler(step):
            if step.step_id == "s2":
                raise RuntimeError("fail")
            return "ok"
        def comp(step):
            order.append(step.step_id)
        wf = executor.execute("wf5", _steps(3), handler, compensate=comp)
        assert order == ["s1", "s0"]  # reverse order
        assert wf.steps[0].status is StepStatus.COMPENSATED
        assert wf.steps[1].status is StepStatus.COMPENSATED

    def test_compensation_error_swallowed(self, executor):
        def handler(step):
            raise RuntimeError("fail at first")
        def comp(step):
            raise RuntimeError("comp fail")
        wf = executor.execute("wf6", _steps(1), handler, compensate=comp)
        assert wf.status == "failed"

    def test_no_compensate_still_fails(self, executor):
        def handler(step):
            raise RuntimeError("x")
        wf = executor.execute("wf7", _steps(1), handler)
        assert wf.status == "failed"
        assert wf.steps[0].status is StepStatus.FAILED


class TestPersistence:
    def test_persisted_json(self, executor, state_dir):
        executor.execute("wf8", _steps(1), lambda s: "done")
        data = json.loads((state_dir / "wf8.json").read_text())
        assert data["status"] == "completed"
        assert data["steps"][0]["result"] == "done"

    def test_workflow_id_sanitized(self, executor, state_dir):
        executor.execute("a/b\\c", _steps(1), lambda s: 1)
        assert (state_dir / "a_b_c.json").exists()

    def test_resume_completed_returns_existing(self, executor):
        calls = []
        executor.execute("wf9", _steps(1), lambda s: calls.append(1))
        wf2 = executor.execute("wf9", _steps(1), lambda s: calls.append(2))
        assert calls == [1]  # not re-executed
        assert wf2.status == "completed"

    def test_resume_failed_workflow(self, executor, state_dir):
        """A failed workflow is returned as-is (not running)."""
        def handler(step):
            raise RuntimeError("x")
        executor.execute("wf10", _steps(1), handler)
        wf2 = executor.execute("wf10", _steps(1), lambda s: "new")
        assert wf2.status == "failed"
        assert wf2.steps[0].error == "x"

    def test_recover_running_workflow(self, executor, state_dir):
        # Simulate crash: write a running workflow with a completed step
        wf = DurableWorkflow(
            workflow_id="wf11", name="wf11",
            steps=[DurableStep("s0", "s0", status=StepStatus.COMPLETED, result="r"),
                   DurableStep("s1", "s1")],
            current_step=1,
        )
        executor._persist(wf)
        recovered = executor.recover("wf11")
        assert recovered is not None and recovered.status == "running"
        assert recovered.current_step == 1

    def test_recover_missing(self, executor):
        assert executor.recover("ghost") is None

    def test_recover_finished_returns_workflow(self, executor):
        executor.execute("wf12", _steps(1), lambda s: 1)
        wf = executor.recover("wf12")
        assert wf is not None and wf.status == "completed"

    def test_resume_from_checkpoint(self, executor, state_dir):
        """Execute() resumes a 'running' persisted workflow from current_step."""
        wf = DurableWorkflow(
            workflow_id="wf13", name="wf13",
            steps=[DurableStep("s0", "s0", status=StepStatus.COMPLETED, result="old"),
                   DurableStep("s1", "s1")],
            current_step=1,
        )
        executor._persist(wf)
        ran = []
        out = executor.execute("wf13", _steps(2), lambda s: ran.append(s.step_id))
        assert ran == ["s1"]  # s0 skipped (already completed)
        assert out.status == "completed"
        assert out.steps[0].result == "old"

    def test_corrupt_file_raises(self, executor, state_dir):
        (state_dir / "wf14.json").write_text("{bad json")
        with pytest.raises(DurableError):
            executor.get_workflow("wf14")

    def test_list_workflows(self, executor):
        executor.execute("wfb", _steps(1), lambda s: 1)
        executor.execute("wfa", _steps(1), lambda s: 1)
        assert executor.list_workflows() == ["wfa", "wfb"]

    def test_get_workflow_missing(self, executor):
        assert executor.get_workflow("nope") is None


class TestCancel:
    def test_cancel_running(self, executor, state_dir):
        wf = DurableWorkflow(
            workflow_id="wfc1", name="wfc1",
            steps=[DurableStep("s0", "s0")], current_step=0,
        )
        executor._persist(wf)
        assert executor.cancel("wfc1") is True
        assert executor.get_workflow("wfc1").status == "cancelled"

    def test_cancel_missing(self, executor):
        assert executor.cancel("ghost") is False

    def test_cancel_completed(self, executor):
        executor.execute("wfc2", _steps(1), lambda s: 1)
        assert executor.cancel("wfc2") is False

    def test_cancelled_not_resumed(self, executor, state_dir):
        wf = DurableWorkflow(
            workflow_id="wfc3", name="wfc3",
            steps=[DurableStep("s0", "s0")], current_step=0,
        )
        executor._persist(wf)
        executor.cancel("wfc3")
        out = executor.execute("wfc3", _steps(1), lambda s: "x")
        assert out.status == "cancelled"  # returned as-is


class TestSerialization:
    def test_step_roundtrip(self):
        s = DurableStep("a", "n", StepStatus.COMPLETED, {"k": 1}, "res", None, 1.0, 2.0)
        s2 = DurableStep.from_dict(s.to_dict())
        assert s2.step_id == "a" and s2.status is StepStatus.COMPLETED
        assert s2.result == "res" and s2.started_at == 1.0

    def test_workflow_roundtrip(self):
        wf = DurableWorkflow("w", "n", [DurableStep("s", "s")], 0, "running", 1.5, None)
        wf2 = DurableWorkflow.from_dict(json.loads(json.dumps(wf.to_dict())))
        assert wf2.workflow_id == "w" and len(wf2.steps) == 1

    def test_durable_error(self):
        err = DurableError("x", {"a": 1})
        assert err.error_code == "DURABLE_ERROR"
