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
