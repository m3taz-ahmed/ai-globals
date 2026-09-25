#!/usr/bin/env python3
"""Evidence mixin — verification artifacts that defeat review theater.

A task is never "done" on a claim. ``verify()`` requires recorded evidence
(test output, diff summary) and can execute the task's ``verify_cmd`` —
exit code 0 or the task stays unverified. Every verification leaves a
``.task/reviews/<id>.md`` artifact for the final review.
"""

from __future__ import annotations

import json
import logging
import shlex
import subprocess
from pathlib import Path
from typing import Any

from runtime.task_contract.models import (
    ContractTask,
    TaskContractError,
    TaskPlan,
    TaskStatus,
    now_stamp,
)

_logger = logging.getLogger(__name__)

VERIFY_CMD_TIMEOUT_S = 120
_MAX_EVIDENCE_TAIL = 800


class EvidenceMixin:
    """Verification + evidence artifacts for :class:`TaskContractManager`.

    Host attributes/methods are provided by the manager via MRO; the
    declarations below exist so type checkers can verify attribute access.
    """

    project_root: Path
    review_dir: Path

    def require_plan(self) -> TaskPlan:  # pragma: no cover - host impl
        raise NotImplementedError

    def _save(self, plan: TaskPlan) -> None:  # pragma: no cover - host impl
        raise NotImplementedError

    def verify(self, task_id: str, evidence: str, run_cmd: bool = False) -> dict[str, Any]:
        """Record verification evidence for an in-progress task.

        Evidence is required — a bare "looks good" does not verify. When the
        task declares ``verify_cmd`` and ``run_cmd`` is set, the command runs
        (shell=False, cwd=project_root, 120s timeout) and must exit 0; its
        output merges into the evidence record.
        """
        plan = self.require_plan()
        task = plan.task(task_id)
        if task.status not in (TaskStatus.IN_PROGRESS, TaskStatus.VERIFIED):
            raise TaskContractError(
                "TASK_NOT_IN_PROGRESS",
                f"task '{task_id}' is {task.status.value}; start it first",
                {"task_id": task_id, "status": task.status.value},
            )
        cmd_result = self._maybe_run_verify(task, run_cmd, plan)
        if not evidence.strip() and cmd_result is None:
            raise TaskContractError(
                "EVIDENCE_REQUIRED",
                "verification needs evidence — test output, command result, or diff summary",
            )
        task.evidence = self._merge_evidence(evidence, cmd_result)
        task.status = TaskStatus.VERIFIED
        self._write_review_artifact(plan, task)
        plan.record("task_verified", {"task": task.id, "evidence_len": len(task.evidence)})
        self._save(plan)
        return {"task": task.id, "verified": True, "cmd": cmd_result}

    def _maybe_run_verify(
        self, task: ContractTask, run_cmd: bool, plan: TaskPlan
    ) -> dict[str, Any] | None:
        if not (run_cmd and task.verify_cmd):
            return None
        result = _run_cmd(task.verify_cmd, str(self.project_root))
        if result["exit_code"] != 0:
            plan.record(
                "verify_failed", {"task": task.id, "exit_code": result["exit_code"]}
            )
            self._save(plan)
            raise TaskContractError(
                "VERIFY_CMD_FAILED",
                f"verify_cmd exited {result['exit_code']}: {result['output'][-400:]}",
                {"task_id": task.id, "exit_code": result["exit_code"]},
            )
        return result

    @staticmethod
    def _merge_evidence(evidence: str, cmd_result: dict[str, Any] | None) -> str:
        combined = evidence.strip()
        if cmd_result is not None:
            tail = cmd_result["output"][-_MAX_EVIDENCE_TAIL:]
            combined = f"{combined}\n[verify_cmd] {tail}".strip()
        return combined

    def _write_review_artifact(self, plan: TaskPlan, task: ContractTask) -> None:
        """Persist per-task verification evidence — review leaves artifacts."""
        try:
            self.review_dir.mkdir(parents=True, exist_ok=True)
            content = (
                f"# Review: {task.id} — {task.title}\n\n"
                f"- Plan: {plan.id}\n- Verified at: {now_stamp()}\n- Risk: {task.risk.value}\n"
                f"- Declared scope: {', '.join(task.files) or '(none declared)'}\n"
                f"- Produces: {task.produces or '(none)'}\n\n"
                "## Acceptance\n\n"
                + "\n".join(f"- {a}" for a in task.acceptance)
                + f"\n\n## Evidence\n\n```\n{task.evidence}\n```\n"
            )
            (self.review_dir / f"{task.id}.md").write_text(content, encoding="utf-8")
        except OSError as exc:
            _logger.warning("review artifact write failed for %s: %s", task.id, exc)

    def write_final_report(self, plan: TaskPlan, report: dict[str, Any]) -> None:
        try:
            self.review_dir.mkdir(parents=True, exist_ok=True)
            (self.review_dir / f"{plan.id}-final.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except OSError as exc:
            _logger.warning("final report write failed for %s: %s", plan.id, exc)


def _run_cmd(cmd: str, cwd: str) -> dict[str, Any]:
    """Execute a verify_cmd without a shell — command lists only."""
    try:
        proc = subprocess.run(
            shlex.split(cmd),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=VERIFY_CMD_TIMEOUT_S,
            shell=False,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return {"exit_code": proc.returncode, "output": output.strip()}
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        return {"exit_code": 127, "output": f"verify_cmd error: {exc}"}
