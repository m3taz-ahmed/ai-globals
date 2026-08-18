"""Tests for saga orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.kernel import Kernel
from runtime.saga import Saga, SagaOrchestrator, SagaStep


@pytest.fixture
def saga_orc(tmp_path: Path) -> SagaOrchestrator:
    return SagaOrchestrator(tmp_path)


def test_saga_runs_all_steps(saga_orc: SagaOrchestrator) -> None:
    def act(action: str, **kwargs: object) -> dict[str, object]:
        return {"ok": True, "action": action}

    saga = Saga("demo", "Demo saga", [SagaStep("Read"), SagaStep("Write")])
    result = saga_orc.run(saga, {}, act=act)

    assert result["ok"] is True
    assert result["status"] == "completed"
    assert len(result["steps"]) == 2


def test_saga_compensates_on_failure(saga_orc: SagaOrchestrator) -> None:
    calls = []

    def act(action: str, **kwargs: object) -> dict[str, object]:
        calls.append(action)
        if action == "Fail":
            return {"ok": False, "error": "boom"}
        return {"ok": True, "action": action}

    saga = Saga(
        "demo",
        "Demo saga",
        [
            SagaStep("Reserve", args={"item": "A"}, compensation={"action": "Cancel", "args": {"item": "A"}}),
            SagaStep("Fail"),
        ],
    )
    result = saga_orc.run(saga, {}, act=act)

    assert result["ok"] is False
    assert result["status"] == "compensated"
    assert "Cancel" in calls
    assert result["compensations"][0]["status"] != "no_compensation"


def test_kernel_run_saga(tmp_path: Path) -> None:
    k = Kernel(tmp_path)
    steps = [{"action": "Read"}, {"action": "Write"}]
    result = k.run_saga("project-setup", steps, {"project": "demo"})
    assert result["ok"] is True
    assert "saga_id" in result


# ---------------------------------------------------------------------------
# SagaStep.from_dict — line 30
# ---------------------------------------------------------------------------

def test_saga_step_from_dict() -> None:
    """SagaStep.from_dict reconstructs a step from a dict."""
    data = {"action": "Read", "args": {"key": "val"}, "compensation": {"action": "Undo"}}
    step = SagaStep.from_dict(data)
    assert step.action == "Read"
    assert step.args == {"key": "val"}
    assert step.compensation == {"action": "Undo"}


def test_saga_step_from_dict_defaults() -> None:
    """SagaStep.from_dict uses defaults for missing args and compensation."""
    step = SagaStep.from_dict({"action": "Write"})
    assert step.action == "Write"
    assert step.args == {}
    assert step.compensation is None


def test_saga_step_to_dict_roundtrip() -> None:
    """SagaStep.to_dict and from_dict are inverses."""
    original = SagaStep("Read", args={"k": "v"}, compensation={"action": "Undo"})
    data = original.to_dict()
    restored = SagaStep.from_dict(data)
    assert restored.action == original.action
    assert restored.args == original.args
    assert restored.compensation == original.compensation


# ---------------------------------------------------------------------------
# _execute_step exception handling — lines 144-145
# ---------------------------------------------------------------------------

def test_saga_step_exception_returns_error(saga_orc: SagaOrchestrator) -> None:
    """When act() raises, _execute_step returns ok=False with error message."""
    saga = Saga("exc", "Exception saga", [SagaStep("Boom")])

    def act(action: str, **kwargs: object) -> dict[str, object]:
        raise RuntimeError("kaboom")

    result = saga_orc.run(saga, {}, act=act)
    assert result["ok"] is False
    assert result["status"] == "compensated"
    assert "Exception: kaboom" in result["failed"]["error"]


# ---------------------------------------------------------------------------
# _compensate_step no compensation — line 158
# ---------------------------------------------------------------------------

def test_saga_compensate_no_compensation(saga_orc: SagaOrchestrator) -> None:
    """When a completed step has no compensation, compensation returns ok with 'no_compensation'."""
    saga = Saga(
        "nocomp",
        "No compensation saga",
        [
            SagaStep("Reserve"),  # no compensation
            SagaStep("Fail"),
        ],
    )

    def act(action: str, **kwargs: object) -> dict[str, object]:
        if action == "Fail":
            return {"ok": False, "error": "boom"}
        return {"ok": True}

    result = saga_orc.run(saga, {}, act=act)
    assert result["ok"] is False
    assert result["compensations"][0]["status"] == "no_compensation"
    assert result["compensations"][0]["ok"] is True


# ---------------------------------------------------------------------------
# _compensate_step exception — lines 164-165
# ---------------------------------------------------------------------------

def test_saga_compensate_exception(saga_orc: SagaOrchestrator) -> None:
    """When compensation act() raises, _compensate_step returns ok=False with error."""
    saga = Saga(
        "comp-exc",
        "Compensation exception saga",
        [
            SagaStep("Reserve", compensation={"action": "Cancel"}),
            SagaStep("Fail"),
        ],
    )

    def act(action: str, **kwargs: object) -> dict[str, object]:
        if action == "Fail":
            return {"ok": False, "error": "boom"}
        if action == "Cancel":
            raise RuntimeError("cancel failed")
        return {"ok": True}

    result = saga_orc.run(saga, {}, act=act)
    assert result["ok"] is False
    assert "Compensation exception: cancel failed" in result["compensations"][0]["error"]
    assert result["compensations"][0]["ok"] is False
    assert result["compensations"][0]["status"] == "compensation_failed"


# ---------------------------------------------------------------------------
# get_saga returns None for missing — line 172
# ---------------------------------------------------------------------------

def test_get_saga_returns_none_for_missing(saga_orc: SagaOrchestrator) -> None:
    """get_saga returns None when saga_id doesn't exist."""
    assert saga_orc.get_saga("nonexistent-saga-id") is None


# ---------------------------------------------------------------------------
# get_saga returns data for existing — lines 173-182
# ---------------------------------------------------------------------------

def test_get_saga_returns_data_for_existing(saga_orc: SagaOrchestrator) -> None:
    """get_saga returns the saga state dict for an existing saga."""
    saga = Saga("gettest", "Get test saga", [SagaStep("Read")])
    result = saga_orc.run(saga, {"project": "demo"}, act=lambda action, **kw: {"ok": True})
    saga_id = result["saga_id"]
    data = saga_orc.get_saga(saga_id)
    assert data is not None
    assert data["saga_id"] == "gettest"
    assert data["status"] == "completed"
    assert data["context"] == {"project": "demo"}
    assert len(data["steps"]) == 1
