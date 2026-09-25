#!/usr/bin/env python3
"""TaskContractManager — owns the ``.task/`` contract state for a project.

Lifecycle: ``record_classification`` → ``decompose`` → per task
``start`` → ``verify`` → ``complete`` → ``finish``. ``amend`` for logged
mid-flight changes; ``abandon`` for cancellation.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.schemas import ErrorSeverity
from runtime.task_contract.classifier import classify_prompt
from runtime.task_contract.enforce import EnforceMixin
from runtime.task_contract.evidence import EvidenceMixin
from runtime.task_contract.models import (
    CLASSIFICATIONS_FILE,
    PLAN_FILE,
    REVIEW_DIR,
    TASK_DIR,
    Classification,
    ContractTask,
    PlanStatus,
    TaskContractError,
    TaskPlan,
    TaskStatus,
    now_stamp,
)
from runtime.task_contract.validation import validate_tasks

_logger = logging.getLogger(__name__)


class TaskContractManager(EnforceMixin, EvidenceMixin):
    """Decompose → execute → verify → review contract for project work."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.task_dir = self.project_root / TASK_DIR
        self.plan_path = self.task_dir / PLAN_FILE
        self.review_dir = self.task_dir / REVIEW_DIR
        self.classifications_path = self.task_dir / CLASSIFICATIONS_FILE

    # -- classification -------------------------------------------------------

    def record_classification(
        self, prompt: str, level: str, reason: str, classified_by: str = "agent"
    ) -> dict[str, Any]:
        """Append a classification record — every prompt leaves a trace.

        ``reason`` is required: the AI must justify the call, not silently
        skip decomposition. The deterministic heuristic is recorded alongside
        and ``disagreement`` is flagged when they differ.
        """
        try:
            level_value = Classification(level).value
        except ValueError as exc:
            raise TaskContractError(
                "INVALID_CLASSIFICATION",
                f"classification must be one of {[c.value for c in Classification]}",
                {"level": level},
            ) from exc
        if not reason.strip():
            raise TaskContractError(
                "CLASSIFICATION_REASON_REQUIRED",
                "a classification without a reason is not a classification",
            )
        heuristic = classify_prompt(prompt)
        record = {
            "at": now_stamp(),
            "level": level_value,
            "reason": reason.strip(),
            "classified_by": classified_by,
            "prompt_summary": prompt.strip()[:160],
            "heuristic": heuristic,
            "disagreement": heuristic["level"] != level_value,
        }
        self.task_dir.mkdir(parents=True, exist_ok=True)
        with self.classifications_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        _logger.info("task-classification: %s (%s)", level_value, reason[:80])
        return record

    # -- plan lifecycle -------------------------------------------------------

    def load(self) -> TaskPlan | None:
        if not self.plan_path.exists():
            return None
        try:
            data = json.loads(self.plan_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TaskContractError(
                "PLAN_CORRUPT",
                f"cannot parse {self.plan_path}: {exc}",
                severity=ErrorSeverity.HIGH,
            ) from exc
        return TaskPlan.from_dict(data)

    def require_plan(self) -> TaskPlan:
        plan = self.load()
        if plan is None or plan.status != PlanStatus.ACTIVE:
            raise TaskContractError("NO_ACTIVE_PLAN", "no active task plan in .task/plan.json")
        return plan

    def decompose(
        self,
        title: str,
        prompt: str,
        tasks: list[dict[str, Any]],
        classification: str,
        classification_reason: str,
    ) -> TaskPlan:
        """Create the active plan. Validates ids, deps, acceptance, scope."""
        if not title.strip():
            raise TaskContractError("INVALID_PLAN", "plan title required")
        existing = self.load()
        if existing is not None and existing.status == PlanStatus.ACTIVE:
            raise TaskContractError(
                "PLAN_EXISTS",
                f"active plan '{existing.id}' exists — finish or abandon it first",
                {"plan_id": existing.id},
            )
        try:
            classification_value = Classification(classification).value
        except ValueError as exc:
            raise TaskContractError(
                "INVALID_PLAN",
                f"classification must be one of {[c.value for c in Classification]}",
            ) from exc
        parsed = [ContractTask.from_dict(t) for t in tasks]
        validate_tasks(parsed)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        plan = TaskPlan(
            id=f"plan-{stamp}",
            title=title.strip(),
            prompt_summary=prompt.strip()[:240],
            classification=classification_value,
            classification_reason=classification_reason.strip(),
            tasks=parsed,
            created_at=now_stamp(),
            updated_at=now_stamp(),
        )
        plan.record("decomposed", {"tasks": len(parsed), "classification": plan.classification})
        self._save(plan)
        return plan

    def start(self, task_id: str) -> ContractTask:
        plan = self.require_plan()
        if plan.active_task_id:
            raise TaskContractError(
                "ALREADY_ACTIVE",
                f"task '{plan.active_task_id}' is active — complete or block it first",
                {"active": plan.active_task_id, "requested": task_id},
            )
        task = plan.task(task_id)
        if task.status != TaskStatus.PENDING:
            raise TaskContractError(
                "TASK_NOT_PENDING", f"task '{task_id}' is {task.status.value}, expected pending"
            )
        done = {t.id for t in plan.tasks if t.status == TaskStatus.DONE}
        missing = [d for d in task.depends_on if d not in done]
        if missing:
            raise TaskContractError(
                "DEP_BLOCKED",
                f"task '{task_id}' waits on unfinished deps: {missing}",
                {"missing": missing},
            )
        task.status = TaskStatus.IN_PROGRESS
        plan.active_task_id = task.id
        plan.record("task_started", {"task": task.id})
        self._save(plan)
        return task

    def complete(self, task_id: str, review_note: str = "") -> ContractTask:
        plan = self.require_plan()
        task = plan.task(task_id)
        if task.status != TaskStatus.VERIFIED:
            raise TaskContractError(
                "NOT_VERIFIED",
                f"task '{task_id}' must be verified with evidence before completion",
                {"status": task.status.value},
            )
        task.status = TaskStatus.DONE
        task.review_note = review_note.strip()
        if plan.active_task_id == task.id:
            plan.active_task_id = ""
        plan.record("task_completed", {"task": task.id})
        self._save(plan)
        return task

    def block(self, task_id: str, reason: str) -> ContractTask:
        plan = self.require_plan()
        task = plan.task(task_id)
        task.status = TaskStatus.BLOCKED
        if plan.active_task_id == task.id:
            plan.active_task_id = ""
        plan.record("task_blocked", {"task": task.id, "reason": reason.strip()})
        self._save(plan)
        return task

    # -- amendments ------------------------------------------------------------

    def amend(self, operations: list[dict[str, Any]], reason: str) -> TaskPlan:
        """Logged plan amendment — drift is allowed, silent drift is not.

        Operations: ``{"op": "add"|"update"|"remove", "task": {...}}`` or
        ``{"op": "update"|"remove", "id": ..., "task": {...patch}}``.
        """
        if not reason.strip():
            raise TaskContractError(
                "AMEND_REASON_REQUIRED", "amendments require a reason — no silent drift"
            )
        plan = self.require_plan()
        applied = [self._apply_amend(plan, op) for op in operations]
        validate_tasks(plan.tasks)
        amendment = {"at": now_stamp(), "reason": reason.strip(), "applied": applied}
        plan.amendments.append(amendment)
        plan.record("amended", amendment)
        self._save(plan)
        return plan

    @staticmethod
    def _apply_amend(plan: TaskPlan, op: dict[str, Any]) -> str:
        kind = str(op.get("op", ""))
        if kind == "add":
            new_task = ContractTask.from_dict(op.get("task", {}))
            plan.tasks.append(new_task)
            return f"add:{new_task.id}"
        tid = str(op.get("id", ""))
        task = plan.task(tid)
        if task.status == TaskStatus.DONE:
            raise TaskContractError("AMEND_INVALID", f"cannot amend completed task '{tid}'")
        if kind == "update":
            patch = ContractTask.from_dict({**task.to_dict(), **op.get("task", {}), "id": tid})
            plan.tasks[plan.tasks.index(task)] = patch
            return f"update:{tid}"
        if kind == "remove":
            dependents = [t.id for t in plan.tasks if tid in t.depends_on]
            if dependents:
                raise TaskContractError(
                    "AMEND_INVALID", f"task '{tid}' has dependents: {dependents}"
                )
            plan.tasks.remove(task)
            return f"remove:{tid}"
        raise TaskContractError("AMEND_INVALID", f"unknown amend op '{kind}'")

    # -- closure ---------------------------------------------------------------

    def finish(self, final_note: str = "") -> dict[str, Any]:
        """Close the plan and emit the final-review report.

        Plan closing is *not* the work being done — the report carries the
        mandatory FULL-tier checklist plus declared-scope and evidence gaps.
        """
        plan = self.require_plan()
        unfinished = [
            t.id for t in plan.tasks if t.status not in (TaskStatus.DONE, TaskStatus.BLOCKED)
        ]
        if unfinished:
            raise TaskContractError(
                "NOT_FINISHED",
                f"tasks not done: {unfinished} — complete, block, or amend them",
                {"unfinished": unfinished},
            )
        report = {
            "plan_id": plan.id,
            "title": plan.title,
            "tasks_done": sum(1 for t in plan.tasks if t.status == TaskStatus.DONE),
            "tasks_blocked": sum(1 for t in plan.tasks if t.status == TaskStatus.BLOCKED),
            "amendments": len(plan.amendments),
            "scope_gaps": [
                t.id for t in plan.tasks if not t.files and t.status == TaskStatus.DONE
            ],
            "evidence_gaps": [
                t.id for t in plan.tasks if t.status == TaskStatus.DONE and not t.evidence
            ],
            "final_checklist": [
                "Run FULL test tier (project suite + coverage) — not just targeted tests",
                "Diff-review: files touched within declared scope plus amendments",
                "Spec/requirements conformance: every acceptance check evidenced",
                "Linters/typecheck green on touched files",
                "No leftover temp/scratch files (cleanup gate)",
            ],
            "final_note": final_note.strip(),
        }
        plan.status = PlanStatus.DONE
        plan.record(
            "finished", {"done": report["tasks_done"], "blocked": report["tasks_blocked"]}
        )
        self._save(plan)
        self.write_final_report(plan, report)
        return report

    def abandon(self, reason: str) -> TaskPlan:
        plan = self.require_plan()
        plan.status = PlanStatus.ABANDONED
        plan.active_task_id = ""
        plan.record("abandoned", {"reason": reason.strip()})
        self._save(plan)
        return plan

    # -- persistence ------------------------------------------------------------

    def _save(self, plan: TaskPlan) -> None:
        """Atomic plan persistence (tempfile + os.replace, same as settings)."""
        self.task_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(plan.to_dict(), indent=2, ensure_ascii=False)
        fd, tmp = tempfile.mkstemp(dir=str(self.task_dir), suffix=".tmp", prefix="plan-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp, self.plan_path)
        except OSError as exc:
            with contextlib.suppress(OSError):
                os.remove(tmp)
            raise TaskContractError(
                "PLAN_SAVE_FAILED",
                f"cannot persist plan: {exc}",
                severity=ErrorSeverity.HIGH,
            ) from exc
