"""Tests for trajectory failure taxonomy + NDJSON export (from AgentRx + agent-trace)."""

from __future__ import annotations

import json
from pathlib import Path

from runtime.trajectory import (
    FailureCategory,
    StepStatus,
    TrajectoryTracker,
)


def test_failure_category_enum_values() -> None:
    assert FailureCategory.INSTRUCTION_ADHERENCE.value == "instruction_adherence"
    assert FailureCategory.INVENTION.value == "invention"
    assert FailureCategory.SYSTEM_FAILURE.value == "system_failure"
    assert FailureCategory.INCONCLUSIVE.value == "inconclusive"


def test_record_step_with_failure_category() -> None:
    tracker = TrajectoryTracker(original_intent="test")
    rid = tracker.start_run("run-1")
    step = tracker.record_step(
        rid,
        action="exec_tool",
        status=StepStatus.FAILED,
        failure_category=FailureCategory.INVALID_INVOCATION,
        tool_name="search",
        tool_input={"query": "test"},
        tool_output="error: invalid args",
    )
    assert step.failure_category is FailureCategory.INVALID_INVOCATION
    assert step.tool_name == "search"
    assert step.tool_input == {"query": "test"}
    assert step.tool_output == "error: invalid args"


def test_failure_summary() -> None:
    tracker = TrajectoryTracker(original_intent="test")
    rid = tracker.start_run("run-1")
    tracker.record_step(rid, "a", StepStatus.OK)
    tracker.record_step(rid, "b", StepStatus.FAILED, failure_category=FailureCategory.INVALID_INVOCATION)
    tracker.record_step(rid, "c", StepStatus.FAILED, failure_category=FailureCategory.INVENTION)
    tracker.record_step(rid, "d", StepStatus.FAILED)  # No category → INCONCLUSIVE
    summary = tracker.failure_summary(rid)
    assert summary["invalid_invocation"] == 1
    assert summary["invention"] == 1
    assert summary["inconclusive"] == 1


def test_failure_summary_empty_run() -> None:
    tracker = TrajectoryTracker(original_intent="test")
    assert tracker.failure_summary("nonexistent") == {}


def test_export_ndjson(tmp_path: Path) -> None:
    tracker = TrajectoryTracker(original_intent="test feature")
    rid = tracker.start_run("run-1", derived_intent="add login")
    tracker.record_step(rid, "write", StepStatus.OK, file="auth.py",
                        tool_name="write_file", tool_input={"path": "auth.py"})
    tracker.record_step(rid, "test", StepStatus.FAILED, check="pytest",
                        failure_category=FailureCategory.SYSTEM_FAILURE)
    output = tmp_path / "trace.ndjson"
    count = tracker.export_ndjson(rid, output)
    assert count >= 4  # run_start + 2 steps + run_end
    # Verify NDJSON format
    lines = output.read_text(encoding="utf-8").strip().split("\n")
    for line in lines:
        event = json.loads(line)
        assert "type" in event
        assert "ts" in event
    # First event is run_start
    assert json.loads(lines[0])["type"] == "run_start"
    # Last event is run_end
    assert json.loads(lines[-1])["type"] == "run_end"
    # Step events have tool info
    step_events = [json.loads(line) for line in lines if json.loads(line)["type"] == "step"]
    assert any(e.get("tool") == "write_file" for e in step_events)
    assert any(e.get("failure_category") == "system_failure" for e in step_events)


def test_export_ndjson_nonexistent_run(tmp_path: Path) -> None:
    tracker = TrajectoryTracker()
    try:
        tracker.export_ndjson("nonexistent", tmp_path / "trace.ndjson")
        raise AssertionError("Should have raised KeyError")
    except KeyError:
        pass
