#!/usr/bin/env python3
"""Saga orchestration with durable SQLite state and compensations."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


class SagaOrchestrator:
    """Durable saga orchestrator with execute and compensate semantics."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.db_path = root / "state" / "saga.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS saga_state (
                    id TEXT PRIMARY KEY,
                    saga_id TEXT NOT NULL,
                    context TEXT NOT NULL,
                    steps TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

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
            if result["ok"]:
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
            self._finish_saga(saga_id, "compensated")
            return {
                "ok": False,
                "saga_id": saga_id,
                "status": "compensated",
                "failed": failed_result,
                "compensations": compensations,
            }

        self._finish_saga(saga_id, "completed")
        return {"ok": True, "saga_id": saga_id, "status": "completed", "steps": completed}

    def _start_saga(self, saga: Saga, context: dict[str, Any]) -> str:
        saga_id = f"{saga.id}-{datetime.now(timezone.utc).isoformat()}"
        now = datetime.now(timezone.utc).isoformat()
        steps_json = json.dumps([s.to_dict() for s in saga.steps])
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO saga_state (id, saga_id, context, steps, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (saga_id, saga.id, json.dumps(context), steps_json, "running", now, now),
            )
        return saga_id

    def _checkpoint(self, saga_id: str, step: int, result: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE saga_state SET updated_at = ? WHERE id = ?",
                (now, saga_id),
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
            result = {"ok": False, "error": f"Exception: {exc!s}"}
        result.setdefault("status", "allowed" if result.get("ok") else "denied")
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
            result = {"ok": False, "error": f"Compensation exception: {exc!s}"}
        result.setdefault("status", "compensated" if result.get("ok") else "compensation_failed")
        return result

    def get_saga(self, saga_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM saga_state WHERE id = ?", (saga_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "saga_id": row["saga_id"],
            "context": json.loads(row["context"]),
            "steps": json.loads(row["steps"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
