#!/usr/bin/env python3
"""Workflow runner for AI Global OS."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Workflow:
    id: str
    path: Path
    title: str
    rules: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> Workflow:
        content = path.read_text(encoding="utf-8")
        title = ""
        for tag in ("[FILE]", "[WORKFLOW]", "[SAGA]"):
            m = re.search(rf"^{re.escape(tag)}\s*(.+)$", content, re.MULTILINE)
            if m:
                title = m.group(1).strip()
                break
        return cls(id=path.stem, path=path, title=title or path.stem, rules=content.splitlines())


class WorkflowRunner:
    """Loads and runs markdown workflows with durable SQLite state."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.dir = root / "workflows"
        self.db_path = root / "state" / "workflow.db"
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
                CREATE TABLE IF NOT EXISTS workflow_state (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    context TEXT NOT NULL,
                    steps TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def list_workflows(self) -> list[str]:
        return [p.stem for p in self.dir.glob("*.md")]

    def get(self, workflow_id: str) -> Workflow | None:
        path = self.dir / f"{workflow_id}.md"
        if path.exists():
            return Workflow.load(path)
        return None

    def run(self, workflow_id: str, context: dict[str, Any]) -> dict[str, Any]:
        wf = self.get(workflow_id)
        if not wf:
            return {"ok": False, "error": f"Workflow {workflow_id} not found"}
        run_id = self._start_run(workflow_id, context)
        steps = self._parse_steps(wf)
        results = []
        for i, step in enumerate(steps):
            result = self._execute_step(step, context)
            results.append(result)
            self._checkpoint(run_id, i, result)
        self._finish_run(run_id)
        return {"ok": True, "workflow": workflow_id, "run_id": run_id, "steps": results}

    def _start_run(self, workflow_id: str, context: dict[str, Any]) -> str:
        run_id = f"{workflow_id}-{datetime.now(timezone.utc).isoformat()}"
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO workflow_state (id, workflow_id, context, steps, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, workflow_id, json.dumps(context), "[]", now, now),
            )
        return run_id

    def _checkpoint(self, run_id: str, step: int, result: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            row = conn.execute("SELECT steps FROM workflow_state WHERE id = ?", (run_id,)).fetchone()
            steps = json.loads(row["steps"]) if row else []
            steps.append({"step": step, **result})
            conn.execute(
                "UPDATE workflow_state SET steps = ?, updated_at = ? WHERE id = ?",
                (json.dumps(steps), now, run_id),
            )

    def _finish_run(self, run_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute("UPDATE workflow_state SET updated_at = ? WHERE id = ?", (now, run_id))

    def _parse_steps(self, wf: Workflow) -> list[dict[str, Any]]:
        steps = []
        for line in wf.rules:
            m = re.match(r"\d+\.\s*\[(REQ|CMD|PROHIBIT)\]\s*(.+)", line)
            if m:
                steps.append({"type": m.group(1), "text": m.group(2)})
        return steps

    def _execute_step(self, step: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {"type": step["type"], "text": step["text"], "status": "ok"}

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM workflow_state WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "workflow_id": row["workflow_id"],
            "context": json.loads(row["context"]),
            "steps": json.loads(row["steps"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
