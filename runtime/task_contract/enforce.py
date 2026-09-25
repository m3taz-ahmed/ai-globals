#!/usr/bin/env python3
"""Enforcement mixin — scope checks and IDE-hook surfaces.

L2 enforcement: ``hook_inject_block()`` adds contract status to
``aizee hook inject`` (beforeSubmitPrompt); ``hook_observe_edit()`` flags
edits outside the active task's declared scope (afterFileEdit).

L3 enforcement: ``AIZEE_TASK_STRICT=1`` turns scope violations into
:class:`TaskContractError` raises for callers that gate on it.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from runtime.schemas import ErrorSeverity
from runtime.task_contract.models import (
    STRICT_ENV,
    PlanStatus,
    TaskContractError,
    TaskStatus,
)

_logger = logging.getLogger(__name__)


def strict_mode() -> bool:
    return os.environ.get(STRICT_ENV) == "1"


class EnforceMixin:
    """Scope enforcement + hook surfaces for :class:`TaskContractManager`.

    Host methods are provided by the manager via MRO; the declaration below
    exists so type checkers can verify attribute access.
    """

    def load(self) -> Any:  # pragma: no cover - host impl
        raise NotImplementedError

    def scope_check(self, path: str) -> dict[str, Any]:
        """Is ``path`` inside the active task's declared file scope?

        Returns ``{"allowed", "task", "declared"}``. No active plan or no
        declared scope means advisory-only (allowed). With
        ``AIZEE_TASK_STRICT=1`` violations also raise.
        """
        plan = self.load()
        result: dict[str, Any] = {"allowed": True, "task": None, "declared": []}
        if plan is None or plan.status != PlanStatus.ACTIVE or not plan.active_task_id:
            return result
        task = plan.task(plan.active_task_id)
        result["task"] = task.id
        if not task.files:
            return result
        allowed = _path_in_scope(path, task.files)
        result["allowed"] = allowed
        result["declared"] = [f.replace("\\", "/").lstrip("./") for f in task.files]
        if not allowed:
            _logger.warning(
                "task-scope violation: %s outside declared scope of '%s' %s",
                path,
                task.id,
                result["declared"],
            )
            if strict_mode():
                raise TaskContractError(
                    "SCOPE_VIOLATION",
                    f"'{path}' outside declared scope of active task '{task.id}': "
                    f"{result['declared']}",
                    {"path": path, "task": task.id},
                    severity=ErrorSeverity.HIGH,
                )
        return result

    def hook_inject_block(self) -> str:
        """Markdown appended to ``aizee hook inject`` output (beforeSubmitPrompt).

        Surfaces the active contract: progress, current task, declared scope,
        next pending task. Returns "" when no plan is active.
        """
        try:
            plan = self.load()
        except TaskContractError:
            return ""
        if plan is None or plan.status != PlanStatus.ACTIVE:
            return ""
        done = sum(1 for t in plan.tasks if t.status == TaskStatus.DONE)
        lines = [
            f"### Task contract: `{plan.id}` — {plan.title}",
            f"- Progress: {done}/{len(plan.tasks)} done",
        ]
        if plan.active_task_id:
            lines.extend(self._active_lines(plan))
        else:
            nxt = plan.next_pending()
            if nxt is not None:
                lines.append(
                    f"- Next pending: `{nxt.id}` — start it with `aizee task start {nxt.id}`"
                )
        return "\n".join(lines)

    def _active_lines(self, plan: Any) -> list[str]:
        task = plan.task(plan.active_task_id)
        lines = [f"- Active: `{task.id}` — {task.title}"]
        if task.files:
            lines.append(f"- Declared scope: {', '.join(task.files[:6])}")
        lines.append("- Verify with evidence, then `aizee task complete` before moving on")
        return lines

    def hook_observe_edit(self, path: str) -> str:
        """Check an edited path against the active task scope (afterFileEdit).

        Returns a warning string on violation, "" when clean. Never raises —
        hook entry points must not block the editor.
        """
        try:
            result = self.scope_check(path)
        except TaskContractError:
            result = {"allowed": False, "task": "", "declared": []}
        if result["allowed"] or not result["task"]:
            return ""
        return (
            f"Task-contract scope warning: '{path}' is outside the declared scope "
            f"of active task '{result['task']}' {result['declared']}. "
            "Amend the plan (`aizee task amend`) or move the edit into its task."
        )

    def status(self) -> dict[str, Any]:
        """Compact plan status for CLI ``aizee task status``."""
        plan = self.load()
        if plan is None:
            return {"plan": None}
        nxt = plan.next_pending()
        return {
            "plan": plan.id,
            "title": plan.title,
            "status": plan.status.value,
            "classification": plan.classification,
            "active_task": plan.active_task_id or None,
            "tasks": [
                {
                    "id": t.id,
                    "status": t.status.value,
                    "depends_on": t.depends_on,
                    "verified": bool(t.evidence),
                }
                for t in plan.tasks
            ],
            "next_pending": nxt.id if nxt else None,
            "amendments": len(plan.amendments),
            "strict": strict_mode(),
        }


def _path_in_scope(path: str, declared: list[str]) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    for raw in declared:
        d = raw.replace("\\", "/").lstrip("./")
        if normalized == d or normalized.startswith(d.rstrip("/") + "/") or d in normalized:
            return True
    return False
