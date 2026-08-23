#!/usr/bin/env python3
"""Workflow and saga orchestration management for the kernel."""

from __future__ import annotations

import copy
import functools
import uuid
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from runtime.enums import ActionResultStatus
from runtime.persona import inject_persona_context
from runtime.saga import Saga, SagaOrchestrator, SagaStep
from runtime.workflow import WorkflowRunner

# Context keys that are auto-derived and should be recomputed for a fresh context.
_FRESH_CONTEXT_DERIVED_KEYS = {"persona", "personas", "skill", "skills", "lords"}


class WorkflowContextSchema:
    """Lightweight schema placeholder for workflow context validation.

    Uses pydantic BaseModel with extra='allow' for forward compatibility.
    """

    @staticmethod
    def validate(context: dict[str, Any]) -> dict[str, Any]:
        """Validate and return the context dict. Currently passthrough."""
        return dict(context)


class WorkflowManager:
    """Encapsulates workflow and saga orchestration."""

    def __init__(
        self,
        project_root: Path,
        os_root: Path,
        persona_detector: Any,
        sagas_total: Any,
    ) -> None:
        self.project_root = project_root
        self.os_root = os_root
        self.workflows = WorkflowRunner(project_root, os_root, persona_detector=persona_detector)
        self.saga = SagaOrchestrator(project_root)
        self._sagas_total = sagas_total

    def list_workflows(self) -> list[str]:
        return self.workflows.list_workflows()

    def run_workflow(
        self,
        workflow_id: str,
        context: dict[str, Any],
        act: Any,
        fresh_context: bool = False,
        persona_detector: Any = None,
        telemetry: Any = None,
    ) -> dict[str, Any]:
        if fresh_context:
            context = copy.deepcopy(context)
            for key in _FRESH_CONTEXT_DERIVED_KEYS:
                context.pop(key, None)
        else:
            context = dict(context)
        session_id: str | None = None
        if fresh_context:
            session_id = uuid.uuid4().hex
        prompt = context.get("message") or context.get("request") or context.get("query") or workflow_id
        if persona_detector:
            inject_persona_context(
                persona_detector,
                context,
                text_keys=("message", "request", "query"),
                fallback_text=prompt if isinstance(prompt, str) else None,
            )
        try:
            valid_context = WorkflowContextSchema.validate(context)
        except ValidationError as e:
            return {"ok": False, "error": f"Invalid workflow context: {e!s}"}
        if session_id is not None:
            act = functools.partial(act, session_id=session_id)
        result = self.workflows.run(workflow_id, valid_context, act=act)
        if session_id is not None:
            result["session_id"] = session_id
        if telemetry:
            telemetry.record(
                event_type="workflow",
                action=workflow_id,
                status=ActionResultStatus.OK.value if result.get("ok") else ActionResultStatus.ERROR.value,
                metadata={"context": valid_context, "result": result},
            )
        return result

    def run_saga(
        self,
        saga_id: str,
        steps: list[dict[str, Any]],
        context: dict[str, Any],
        act: Any,
        fresh_context: bool = False,
        telemetry: Any = None,
    ) -> dict[str, Any]:
        if fresh_context:
            context = copy.deepcopy(context)
            for key in _FRESH_CONTEXT_DERIVED_KEYS:
                context.pop(key, None)
        else:
            context = dict(context)
        try:
            saga = Saga(
                id=saga_id,
                title=saga_id,
                steps=[SagaStep(**s) for s in steps],
            )
        except ValidationError as e:
            return {"ok": False, "error": f"Invalid saga definition: {e!s}"}
        session_id: str | None = None
        if fresh_context:
            session_id = uuid.uuid4().hex
        if session_id is not None:
            act = functools.partial(act, session_id=session_id)
        result = self.saga.run(saga, context, act=act)
        if session_id is not None:
            result["session_id"] = session_id
        if telemetry:
            telemetry.record(
                event_type="saga",
                action=saga_id,
                status=result.get("status", "unknown"),
                metadata={"context": context, "result": result},
            )
        return result
