#!/usr/bin/env python3
"""Task Contract MCP tools — classify/decompose/start/verify/complete/finish."""

from __future__ import annotations

import json
import logging
from typing import Any

from aizee_mcp._compat import FastMCP
from runtime.task_contract.classifier import classify_prompt

from .common import kernel

logger = logging.getLogger(__name__)


def _mgr() -> Any:
    return kernel().task_contract


def _ser(obj: Any) -> dict[str, Any]:
    return obj.to_dict() if hasattr(obj, "to_dict") else dict(obj)


def _ok(payload: Any) -> str:
    return json.dumps({"ok": True, "result": _ser(payload)}, ensure_ascii=False, default=str)


def _err(exc: Exception) -> str:
    return json.dumps(
        {"ok": False, "error": str(exc), "code": getattr(exc, "error_code", "ERROR")},
        ensure_ascii=False,
    )


def register_task_tools(mcp: FastMCP) -> None:
    """Register task-contract lifecycle tools."""

    @mcp.tool()
    def task_classify(prompt: str, level: str = "", reason: str = "") -> str:
        """Classify a work prompt as trivial|standard|complex — recorded, with reason.

        Every prompt MUST be classified before work starts. Pass `level` to
        record the agent's own classification; omit for the heuristic opinion.
        Non-trivial prompts require task_decompose before edits.
        """
        try:
            if level:
                return _ok(_mgr().record_classification(prompt, level, reason))
            return _ok({"heuristic": classify_prompt(prompt)})
        except Exception as exc:
            return _err(exc)

    @mcp.tool()
    def task_decompose(
        title: str,
        prompt: str,
        tasks: list[dict[str, Any]],
        classification: str = "standard",
        reason: str = "",
    ) -> str:
        """Create the active plan. Each task: {id, title, deps[], files[], produces[], acceptance, risk}."""
        try:
            plan = _mgr().decompose(title, prompt, tasks, classification, reason)
            return _ok({"plan": plan.to_dict(), "next": getattr(plan.next_pending(), "id", None)})
        except Exception as exc:
            return _err(exc)

    @mcp.tool()
    def task_status() -> str:
        """Show the active plan: status, active task, next pending, per-task state."""
        try:
            return _ok(_mgr().status())
        except Exception as exc:
            return _err(exc)

    @mcp.tool()
    def task_start(task_id: str) -> str:
        """Start a pending task — its dependencies must all be done first."""
        try:
            return _ok(_mgr().start(task_id))
        except Exception as exc:
            return _err(exc)

    @mcp.tool()
    def task_verify(task_id: str, evidence: str, run_cmd: bool = False) -> str:
        """Record verification evidence for the active task (required before complete)."""
        try:
            return _ok(_mgr().verify(task_id, evidence, run_cmd=run_cmd))
        except Exception as exc:
            return _err(exc)

    @mcp.tool()
    def task_complete(task_id: str, note: str = "") -> str:
        """Mark a verified task done — fails without recorded evidence."""
        try:
            return _ok(_mgr().complete(task_id, note))
        except Exception as exc:
            return _err(exc)

    @mcp.tool()
    def task_block(task_id: str, reason: str) -> str:
        """Mark the task blocked with a reason; clears the active slot."""
        try:
            return _ok(_mgr().block(task_id, reason))
        except Exception as exc:
            return _err(exc)

    @mcp.tool()
    def task_finish(note: str = "") -> str:
        """Close the plan and emit the final-review report (all tasks must be done)."""
        try:
            return _ok(_mgr().finish(note))
        except Exception as exc:
            return _err(exc)

    @mcp.tool()
    def task_abandon(reason: str) -> str:
        """Abandon the active plan with a recorded reason."""
        try:
            return _ok(_mgr().abandon(reason))
        except Exception as exc:
            return _err(exc)

    @mcp.tool()
    def task_scope(path: str) -> str:
        """Check whether a path is inside the active task's declared scope."""
        try:
            return _ok(_mgr().scope_check(path))
        except Exception as exc:
            return _err(exc)


register = register_task_tools
