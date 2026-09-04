#!/usr/bin/env python3
"""Saga orchestration with durable SQLite state and compensations."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

from .enums import ActionResultStatus, SagaStatus
from .repository import BaseRepository

_logger = logging.getLogger(__name__)


@dataclass
class SagaStep:
    """A single saga step with optional compensation."""

    action: str
    args: dict[str, Any] = field(default_factory=dict)
    compensation: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.action, "args": self.args, "compensation": self.compensation}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SagaStep:
        return cls(
            action=data["action"],
            args=data.get("args", {}),
            compensation=data.get("compensation"),
        )


@dataclass
class Saga:
    """A saga definition: ordered steps with boundary metadata."""

    id: str
    title: str
    steps: list[SagaStep]
    boundary: dict[str, Any] = field(default_factory=dict)


class SagaOrchestrator(BaseRepository):
    """Durable saga orchestrator with execute and compensate semantics."""

    _schema_sql: ClassVar[list[str]] = [
        """
        CREATE TABLE IF NOT EXISTS saga_state (
            id TEXT PRIMARY KEY,
            saga_id TEXT NOT NULL,
            context TEXT NOT NULL,
            steps TEXT NOT NULL,
            completed TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    ]

    def __init__(self, root: Path) -> None:
        self.root = root
        super().__init__(root / "state" / "saga.db")
        self._ensure_progress_column()

    def run(
        self,
        saga: Saga,
        context: dict[str, Any],
        act: Callable[..., dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Execute saga steps; compensate on failure."""
        act = act or (lambda **_: {"ok": True})
        saga_id = self._start_saga(saga, context)
        completed: list[dict[str, Any]] = []

        for index, step in enumerate(saga.steps):
            result = self._execute_step(saga_id, index, step, context, act)
            if not isinstance(result, dict):
                result = {"ok": False, "error": "saga step returned invalid result"}
            if result.get("ok"):
                completed.append({"step": index, **result})
                self._checkpoint(saga_id, index, result)
                continue

            # failure: compensate completed steps in reverse
            failed_result = {"step": index, **result}
            compensations = []
            for completed_step in reversed(completed):
                step_index = completed_step["step"]
                comp = self._compensate_step(saga_id, step_index, saga.steps[step_index], context, act)
                compensations.append({"step": step_index, **comp})
            self._finish_saga(saga_id, SagaStatus.COMPENSATED.value)
            return {
                "ok": False,
                "saga_id": saga_id,
                "status": SagaStatus.COMPENSATED.value,
                "failed": failed_result,
                "compensations": compensations,
            }

        self._finish_saga(saga_id, SagaStatus.COMPLETED.value)
        return {"ok": True, "saga_id": saga_id, "status": SagaStatus.COMPLETED.value, "steps": completed}

    def _ensure_progress_column(self) -> None:
        """Add the durable-progress column to pre-existing saga.db files."""
        with self._conn() as conn:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(saga_state)").fetchall()}
            if "completed" not in cols:
                conn.execute("ALTER TABLE saga_state ADD COLUMN completed TEXT NOT NULL DEFAULT '[]'")

    def _start_saga(self, saga: Saga, context: dict[str, Any]) -> str:
        # Filesystem/URL-safe unique id (isoformat contains ':' and can collide).
        saga_id = f"{saga.id}-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        steps_json = json.dumps([s.to_dict() for s in saga.steps])
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO saga_state (id, saga_id, context, steps, completed, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (saga_id, saga.id, json.dumps(context), steps_json, "[]", SagaStatus.RUNNING.value, now, now),
            )
        return saga_id

    def _checkpoint(self, saga_id: str, step: int, result: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            row = conn.execute("SELECT completed FROM saga_state WHERE id = ?", (saga_id,)).fetchone()
            try:
                completed = json.loads(row["completed"]) if row else []
            except (ValueError, TypeError, KeyError):
                completed = []
            if not isinstance(completed, list):
                completed = []
            completed.append({"step": step, "ok": result.get("ok", False), "at": now})
            conn.execute(
                "UPDATE saga_state SET completed = ?, updated_at = ? WHERE id = ?",
                (json.dumps(completed), now, saga_id),
            )

    def _finish_saga(self, saga_id: str, status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE saga_state SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, saga_id),
            )

    def _execute_step(
        self,
        saga_id: str,
        index: int,
        step: SagaStep,
        context: dict[str, Any],
        act: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        merged = {**context, **step.args, "saga_id": saga_id, "step": index}
        merged.setdefault("approved", True)
        try:
            result = act(step.action, **merged)
        except Exception as exc:
            _logger.debug("saga step execution failed: %s", exc, exc_info=True)
            result = {"ok": False, "error": f"Exception: {exc!s}"}
        result.setdefault("status", ActionResultStatus.ALLOWED.value if result.get("ok") else ActionResultStatus.DENIED.value)
        return result

    def _compensate_step(
        self,
        saga_id: str,
        index: int,
        step: SagaStep,
        context: dict[str, Any],
        act: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        if not step.compensation:
            return {"ok": True, "status": "no_compensation"}
        comp_action = step.compensation.get("action", step.action)
        comp_args = {**context, **step.compensation.get("args", {}), "saga_id": saga_id, "step": index}
        comp_args.setdefault("approved", True)
        try:
            result = act(comp_action, **comp_args)
        except Exception as exc:
            _logger.debug("saga compensation failed: %s", exc, exc_info=True)
            result = {"ok": False, "error": f"Compensation exception: {exc!s}"}
        result.setdefault("status", SagaStatus.COMPENSATED.value if result.get("ok") else "compensation_failed")
        return result

    def get_saga(self, saga_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM saga_state WHERE id = ?", (saga_id,)).fetchone()
        if not row:
            return None
        try:
            completed = json.loads(row["completed"]) if "completed" in row.keys() else []  # noqa: SIM118 — sqlite3.Row has no __contains__; .keys() required
        except (ValueError, TypeError):
            completed = []
        return {
            "id": row["id"],
            "saga_id": row["saga_id"],
            "context": json.loads(row["context"]),
            "steps": json.loads(row["steps"]),
            "completed": completed,
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
