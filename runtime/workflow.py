#!/usr/bin/env python3
"""Workflow runner for AI Global OS."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

from .enums import ActionResultStatus, StepType
from .mcp_client import McpClient, parse_mcp_command
from .persona import PersonaDetector
from .repository import BaseRepository


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


class WorkflowRunner(BaseRepository):
    """Loads and runs markdown workflows with durable SQLite state."""

    _schema_sql: ClassVar[list[str]] = [
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
    ]

    def __init__(
        self,
        root: Path,
        os_root: Path | None = None,
        persona_detector: PersonaDetector | None = None,
    ) -> None:
        self.root = root
        self.os_root = os_root or root
        self.dir = root / "workflows"
        self.persona = persona_detector or PersonaDetector()
        super().__init__(root / "state" / "workflow.db")

    def list_workflows(self) -> list[str]:
        return [p.stem for p in self.dir.glob("*.md")]

    def get(self, workflow_id: str) -> Workflow | None:
        path = self.dir / f"{workflow_id}.md"
        if path.exists():
            return Workflow.load(path)
        return None

    def run(
        self,
        workflow_id: str,
        context: dict[str, Any],
        act: Callable[..., dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        context = dict(context)
        prompt = context.get("message") or context.get("request") or context.get("query")
        if "personas" not in context and "persona" not in context and isinstance(prompt, str) and prompt.strip():
            result = self.persona.detect_multiple(prompt)
            context["persona"] = result["persona"]
            context["skill"] = result["skill"]
            context["personas"] = result["personas"]
            context["skills"] = result["skills"]
            context["lords"] = result["lords"]
        wf = self.get(workflow_id)
        if not wf:
            return {"ok": False, "error": f"Workflow {workflow_id} not found"}
        run_id = self._start_run(workflow_id, context)
        steps = self._parse_steps(wf)
        results = []
        for i, step in enumerate(steps):
            result = self._execute_step(step, context, act=act)
            results.append(result)
            self._checkpoint(run_id, i, result)
        self._finish_run(run_id)
        return {"ok": True, "workflow": workflow_id, "run_id": run_id, "context": context, "steps": results}

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

    def _parse_mcp(self, text: str) -> tuple[str, str, dict[str, Any]] | None:
        parsed = parse_mcp_command(text)
        if parsed is None:
            return None
        return parsed

    def _parse_steps(self, wf: Workflow) -> list[dict[str, Any]]:
        steps = []
        for line in wf.rules:
            m = re.match(r"\d+\.\s*\[(REQ|CMD|PROHIBIT)\]\s*(.+)", line)
            if m:
                steps.append({"type": StepType(m.group(1)), "text": m.group(2)})
        return steps

    def _execute_step(
        self,
        step: dict[str, Any],
        context: dict[str, Any],
        act: Callable[..., dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        step_type = step["type"]
        text = step["text"]
        result: dict[str, Any] = {"type": step_type, "text": text, "status": ActionResultStatus.OK.value}

        if step_type == StepType.PROHIBIT:
            result["status"] = ActionResultStatus.PROHIBITED.value
            return result

        if step_type == StepType.REQ:
            return result

        if step_type == StepType.CMD and act:
            cmd = text.strip()
            if cmd.startswith("bash:"):
                shell_cmd = cmd[5:].strip()
                try:
                    act_result = act("Bash", command=shell_cmd, approved=True, dry_run=True)
                    result["status"] = (
                        ActionResultStatus.ALLOWED.value
                        if act_result["ok"]
                        else act_result.get("decision", {}).get("decision", ActionResultStatus.DENIED.value)
                    )
                    result["evaluation"] = act_result
                except Exception as exc:
                    result["status"] = ActionResultStatus.ERROR.value
                    result["evaluation"] = {"ok": False, "error": str(exc)}
            elif cmd.startswith("mcp:"):
                mcp_cmd = cmd[4:].strip()
                parsed = self._parse_mcp(mcp_cmd)
                if parsed is None:
                    result["status"] = ActionResultStatus.MCP_PARSE_ERROR.value
                else:
                    server, tool, args = parsed
                    client = McpClient(server, self.os_root)
                    if not client.is_configured():
                        result["status"] = ActionResultStatus.MCP_NOT_CONFIGURED.value
                    else:
                        try:
                            act_result = client.call_tool(tool, args)
                            result["status"] = (
                                ActionResultStatus.ALLOWED.value
                                if act_result["ok"]
                                else ActionResultStatus.MCP_CALL_FAILED.value
                            )
                            result["evaluation"] = act_result
                        except Exception as exc:
                            result["status"] = ActionResultStatus.ERROR.value
                            result["evaluation"] = {"ok": False, "error": str(exc)}
            else:
                result["status"] = ActionResultStatus.NOOP.value

        return result

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
