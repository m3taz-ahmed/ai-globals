"""Tests for eval/agent_benchmark.py — agent benchmark engine."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.agent_benchmark import (
    BenchmarkEngine,
    BenchmarkReport,
    BenchmarkTask,
    TaskResult,
    _score_combined,
    _score_contains,
    _score_decision,
    _score_exact_field,
    default_tasks,
)


class TestScoringFunctions:
    """Tests for scoring functions."""

    def test_score_contains_all_match(self) -> None:
        result = _score_contains({"text": "hello world foo"}, {"keywords": ["hello", "world"]})
        assert result == 1.0

    def test_score_contains_partial(self) -> None:
        result = _score_contains({"text": "hello"}, {"keywords": ["hello", "world"]})
        assert result == 0.5

    def test_score_contains_no_keywords(self) -> None:
        result = _score_contains({"text": "hello"}, {})
        assert result == 1.0

    def test_score_exact_field_match(self) -> None:
        result = _score_exact_field({"ok": True, "n": 1}, {"fields": {"ok": True, "n": 1}})
        assert result == 1.0

    def test_score_exact_field_partial(self) -> None:
        result = _score_exact_field({"ok": True, "n": 2}, {"fields": {"ok": True, "n": 1}})
        assert result == 0.5

    def test_score_exact_field_no_fields(self) -> None:
        result = _score_exact_field({}, {})
        assert result == 1.0

    def test_score_decision_match(self) -> None:
        result = _score_decision({"decision": "deny"}, {"decision": "deny"})
        assert result == 1.0

    def test_score_decision_mismatch(self) -> None:
        result = _score_decision({"decision": "allow"}, {"decision": "deny"})
        assert result == 0.0

    def test_score_decision_no_expected(self) -> None:
        result = _score_decision({"decision": "allow"}, {})
        assert result == 1.0

    def test_score_combined_average(self) -> None:
        result = _score_combined(
            {"text": "hello", "ok": True, "decision": "allow"},
            {"keywords": ["hello"], "fields": {"ok": True}, "decision": "allow"},
        )
        assert result == 1.0


class TestBenchmarkTask:
    """Tests for BenchmarkTask dataclass."""

    def test_default_values(self) -> None:
        task = BenchmarkTask(id="test", prompt="hello")
        assert task.persona is None
        assert task.expected == {}
        assert task.action_type == "chat"
        assert task.timeout == 30.0
        assert task.tags == []

    def test_custom_values(self) -> None:
        task = BenchmarkTask(
            id="test",
            prompt="hello",
            persona="ARCH",
            expected={"keywords": ["test"]},
            action_type="act",
            tags=["security"],
        )
        assert task.persona == "ARCH"
        assert task.action_type == "act"
        assert "security" in task.tags


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_passed_high_score(self) -> None:
        r = TaskResult(task_id="t1", score=0.9, duration_ms=10.0, response={})
        assert r.passed is True

    def test_passed_low_score(self) -> None:
        r = TaskResult(task_id="t1", score=0.5, duration_ms=10.0, response={})
        assert r.passed is False

    def test_passed_with_error(self) -> None:
        r = TaskResult(task_id="t1", score=1.0, duration_ms=10.0, response={}, error="oops")
        assert r.passed is False

    def test_passed_boundary(self) -> None:
        r = TaskResult(task_id="t1", score=0.7, duration_ms=10.0, response={})
        assert r.passed is True


class TestBenchmarkReport:
    """Tests for BenchmarkReport."""

    def test_empty_report(self) -> None:
        report = BenchmarkReport()
        summary = report.summary()
        assert summary["total"] == 0
        assert summary["passed"] == 0

    def test_summary_with_results(self) -> None:
        results = [
            TaskResult("t1", 0.9, 10.0, {}),
            TaskResult("t2", 0.5, 20.0, {}),
            TaskResult("t3", 1.0, 15.0, {}),
        ]
        report = BenchmarkReport(results=results, total_duration_ms=45.0)
        summary = report.summary()
        assert summary["total"] == 3
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["avg_score"] == pytest.approx(0.8, abs=0.01)


class TestBenchmarkEngine:
    """Tests for BenchmarkEngine with mocked kernel."""

    def _mock_kernel(self, response: dict) -> MagicMock:
        kernel = MagicMock()
        kernel.act.return_value = response
        kernel.chat_message.return_value = response
        return kernel

    def test_run_task_chat(self) -> None:
        kernel = self._mock_kernel({"ok": True, "text": "hello world"})
        engine = BenchmarkEngine(kernel=kernel)
        task = BenchmarkTask(
            id="test-chat",
            prompt="say hello",
            action_type="chat",
            expected={"keywords": ["hello", "world"]},
        )
        result = engine.run_task(task)
        assert result.task_id == "test-chat"
        assert result.score > 0
        assert result.error is None

    def test_run_task_act(self) -> None:
        kernel = self._mock_kernel({"ok": True, "decision": "allow"})
        engine = BenchmarkEngine(kernel=kernel)
        task = BenchmarkTask(
            id="test-act",
            prompt="read file",
            action_type="act",
            action_kwargs={"type": "Read", "path": "/tmp/x"},
            expected={"decision": "allow"},
        )
        result = engine.run_task(task)
        assert result.score == 1.0

    def test_run_task_error(self) -> None:
        kernel = MagicMock()
        kernel.act.side_effect = RuntimeError("boom")
        engine = BenchmarkEngine(kernel=kernel)
        task = BenchmarkTask(
            id="test-err",
            prompt="fail",
            action_type="act",
            action_kwargs={"type": "Fail"},
        )
        result = engine.run_task(task)
        assert result.score == 0.0
        assert result.error is not None
        assert "boom" in result.error

    def test_run_all(self) -> None:
        kernel = self._mock_kernel({"ok": True, "decision": "allow", "text": "hello"})
        tasks = [
            BenchmarkTask(id="t1", prompt="p1", expected={"keywords": ["hello"]}),
            BenchmarkTask(id="t2", prompt="p2", expected={"keywords": ["world"]}),
        ]
        engine = BenchmarkEngine(kernel=kernel, tasks=tasks)
        report = engine.run_all()
        assert len(report.results) == 2
        assert report.total_duration_ms > 0

    def test_run_all_with_tags(self) -> None:
        kernel = self._mock_kernel({"ok": True})
        tasks = [
            BenchmarkTask(id="t1", prompt="p1", tags=["security"]),
            BenchmarkTask(id="t2", prompt="p2", tags=["performance"]),
            BenchmarkTask(id="t3", prompt="p3", tags=["security", "fast"]),
        ]
        engine = BenchmarkEngine(kernel=kernel, tasks=tasks)
        report = engine.run_all(tags=["security"])
        assert len(report.results) == 2  # t1 and t3

    def test_run_by_id_found(self) -> None:
        kernel = self._mock_kernel({"ok": True})
        engine = BenchmarkEngine(kernel=kernel, tasks=[
            BenchmarkTask(id="target", prompt="p"),
        ])
        result = engine.run_by_id("target")
        assert result.task_id == "target"

    def test_run_by_id_not_found(self) -> None:
        kernel = self._mock_kernel({"ok": True})
        engine = BenchmarkEngine(kernel=kernel)
        result = engine.run_by_id("nonexistent")
        assert result.score == 0.0
        assert "not found" in (result.error or "")

    def test_default_tasks_not_empty(self) -> None:
        tasks = default_tasks()
        assert len(tasks) > 0
        assert all(isinstance(t, BenchmarkTask) for t in tasks)

    def test_unknown_action_type(self) -> None:
        kernel = self._mock_kernel({"ok": True})
        engine = BenchmarkEngine(kernel=kernel)
        task = BenchmarkTask(id="t", prompt="p", action_type="unknown")
        result = engine.run_task(task)
        # Unknown action type returns an error in the response, not as exception
        assert "Unknown action type" in result.response.get("error", "")

    def test_get_kernel_lazy_init(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Lines 202-204: _get_kernel lazily creates a Kernel when none provided."""
        engine = BenchmarkEngine(kernel=None, tasks=[])
        # Mock Kernel to avoid real initialization
        mock_kernel = MagicMock()
        mock_kernel.act.return_value = {"ok": True}
        mock_kernel.chat_message.return_value = {"ok": True}
        monkeypatch.setattr("runtime.kernel.Kernel", lambda: mock_kernel)
        kernel = engine._get_kernel()
        assert kernel is mock_kernel
        # Second call should return cached kernel
        assert engine._get_kernel() is mock_kernel

    def test_run_task_with_lazy_kernel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Lines 202-204: run_task uses lazy kernel init."""
        mock_kernel = MagicMock()
        mock_kernel.chat_message.return_value = {"ok": True, "text": "hello"}
        monkeypatch.setattr("runtime.kernel.Kernel", lambda: mock_kernel)
        engine = BenchmarkEngine(kernel=None)
        task = BenchmarkTask(id="t", prompt="hello", expected={"keywords": ["hello"]})
        result = engine.run_task(task)
        assert result.score > 0
        assert result.error is None


class TestBenchmarkMainBlock:
    """Tests for the __main__ block (lines 266-268)."""

    def test_main_block_runs(self) -> None:
        """Lines 266-268: __main__ block executes run_all and prints summary."""
        import os as _os
        import subprocess
        import sys
        env = dict(_os.environ)
        env.update({
            "AGENT_OS_ROOT": str(Path(__file__).resolve().parent.parent),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONHASHSEED": "0",
            "PYTHONPATH": str(Path(__file__).resolve().parent.parent),
        })
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent.parent / "eval" / "agent_benchmark.py")],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if result.returncode != 0 and "HashRandomization" in result.stderr:  # pragma: no cover
            pytest.skip("Windows subprocess hash randomization issue")
        # The __main__ block should produce JSON output
        assert result.stdout.strip().startswith("{")

    def test_main_block_in_process(self, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
        """Lines 266-268: __main__ block via runpy for in-process coverage."""
        import runpy

        os_root = str(Path(__file__).resolve().parent.parent)
        monkeypatch.setenv("AGENT_OS_ROOT", os_root)
        runpy.run_module("eval.agent_benchmark", run_name="__main__")
        captured = capsys.readouterr()
        assert captured.out.strip().startswith("{")
