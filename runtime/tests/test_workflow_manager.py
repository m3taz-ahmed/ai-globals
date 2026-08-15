"""Tests for runtime/managers/workflow_manager.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from runtime.managers.workflow_manager import WorkflowManager
from runtime.persona import PersonaDetector


def _setup_roots(tmp_path: Path) -> tuple[Path, Path]:
    """Create project root and OS root with workflow and policy dirs."""
    os_root = tmp_path / "os"
    project_root = tmp_path / "project"
    for sub in ("runtime/policies", "workflows", "state"):
        (os_root / sub).mkdir(parents=True, exist_ok=True)
        (project_root / sub).mkdir(parents=True, exist_ok=True)
    (os_root / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    (project_root / "workflows/test.md").write_text(
        "[WORKFLOW] test\n[RULES]\n1. [REQ] Step one.\n2. [CMD] Step two.\n"
    )
    return project_root, os_root


def _make_manager(tmp_path: Path) -> WorkflowManager:
    project_root, os_root = _setup_roots(tmp_path)
    persona = PersonaDetector()
    sagas_total = MagicMock()
    return WorkflowManager(project_root, os_root, persona, sagas_total)


class TestRunWorkflow:
    def test_run_workflow_success(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        act_fn = MagicMock(return_value={"ok": True, "decision": {"decision": "allow"}})
        result = mgr.run_workflow("test", {"message": "hello"}, act_fn)
        assert result["ok"] is True

    def test_run_workflow_with_telemetry(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        act_fn = MagicMock(return_value={"ok": True, "decision": {"decision": "allow"}})
        telemetry = MagicMock()
        result = mgr.run_workflow("test", {"message": "hello"}, act_fn, telemetry=telemetry)
        assert result["ok"] is True
        telemetry.record.assert_called_once()

    def test_run_workflow_fresh_context(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        act_fn = MagicMock(return_value={"ok": True, "decision": {"decision": "allow"}})
        context = {"message": "test", "persona": "ARCH", "skills": ["x"]}
        result = mgr.run_workflow("test", context, act_fn, fresh_context=True)
        assert result["ok"] is True
        assert "session_id" in result
        # Original context should not be mutated
        assert context["persona"] == "ARCH"

    def test_run_workflow_validation_error(self, tmp_path: Path) -> None:
        """Cover lines 86-87: ValidationError in context returns error."""
        mgr = _make_manager(tmp_path)
        act_fn = MagicMock()
        # Monkeypatch WorkflowContextSchema.validate to raise ValidationError
        from pydantic import ValidationError
        from runtime.managers import workflow_manager as wm_mod

        original_validate = wm_mod.WorkflowContextSchema.validate

        def raising_validate(ctx):
            raise ValidationError.from_exception_data("test", [])

        wm_mod.WorkflowContextSchema.validate = staticmethod(raising_validate)
        try:
            result = mgr.run_workflow("test", {"message": "hello"}, act_fn)
            assert result["ok"] is False
            assert "Invalid workflow context" in result["error"]
        finally:
            wm_mod.WorkflowContextSchema.validate = staticmethod(original_validate)


class TestRunSaga:
    def test_run_saga_success(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        act_fn = MagicMock(return_value={"ok": True, "decision": {"decision": "allow"}})
        steps = [{"action": "Read"}]
        result = mgr.run_saga("test-saga", steps, {"message": "test"}, act_fn)
        assert "status" in result or "ok" in result

    def test_run_saga_fresh_context(self, tmp_path: Path) -> None:
        """Cover lines 112-114, 127, 129, 132: fresh context in saga."""
        mgr = _make_manager(tmp_path)
        act_fn = MagicMock(return_value={"ok": True, "decision": {"decision": "allow"}})
        context = {"message": "test", "persona": "ARCH"}
        steps = [{"action": "Read"}]
        result = mgr.run_saga("test-saga", steps, context, act_fn, fresh_context=True)
        assert "session_id" in result
        # Original context not mutated
        assert context["persona"] == "ARCH"

    def test_run_saga_invalid_steps(self, tmp_path: Path) -> None:
        """Cover lines 123-124: invalid saga definition returns error."""
        from pydantic import ValidationError

        mgr = _make_manager(tmp_path)
        act_fn = MagicMock()
        # Monkeypatch SagaStep to raise ValidationError
        from runtime.managers import workflow_manager as wm_mod

        original_saga_step = wm_mod.SagaStep

        class RaisingSagaStep:
            def __init__(self, **kwargs):
                raise ValidationError.from_exception_data("test", [])

        wm_mod.SagaStep = RaisingSagaStep
        try:
            result = mgr.run_saga("bad-saga", [{"action": "Read"}], {}, act_fn)
            assert result["ok"] is False
            assert "Invalid saga definition" in result["error"]
        finally:
            wm_mod.SagaStep = original_saga_step

    def test_run_saga_with_telemetry(self, tmp_path: Path) -> None:
        """Cover telemetry recording in run_saga."""
        mgr = _make_manager(tmp_path)
        act_fn = MagicMock(return_value={"ok": True, "status": "completed"})
        telemetry = MagicMock()
        steps = [{"action": "Read"}]
        result = mgr.run_saga("test-saga", steps, {"message": "test"}, act_fn, telemetry=telemetry)
        telemetry.record.assert_called_once()
