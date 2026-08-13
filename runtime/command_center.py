#!/usr/bin/env python3
"""Agent Command Center — fleet management dashboard for AI Global OS.

Provides a Kanban-style task board and agent fleet tracking layer that
complements the existing ``AgentManager``.  All state is persisted to
``state/command_center.json`` as plain JSON (dashboard data is not
sensitive, unlike budget usage which is encrypted).
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

AgentState = Literal["idle", "running", "blocked", "done"]
TaskColumn = Literal["todo", "in_progress", "done", "blocked"]
Priority = Literal["low", "medium", "high", "critical"]

VALID_STATES: set[str] = {"idle", "running", "blocked", "done"}
VALID_COLUMNS: set[str] = {"todo", "in_progress", "done", "blocked"}
VALID_PRIORITIES: set[str] = {"low", "medium", "high", "critical"}


@dataclass
class AgentStatus:
    """Snapshot of a single agent in the fleet."""

    agent_id: str
    persona: str
    status: AgentState = "idle"
    current_task: str | None = None
    started_at: str | None = None
    progress: int = 0
    worktree_path: str | None = None

    def __post_init__(self) -> None:
        if self.status not in VALID_STATES:
            self.status = "idle"
        self.progress = max(0, min(100, self.progress))


@dataclass
class TaskCard:
    """A single work item on the Kanban board."""

    id: str
    title: str
    assignee: str | None = None
    status: TaskColumn = "todo"
    priority: Priority = "medium"
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in VALID_COLUMNS:
            self.status = "todo"
        if self.priority not in VALID_PRIORITIES:
            self.priority = "medium"


@dataclass
class TaskBoard:
    """Kanban board with four standard columns."""

    columns: dict[str, list[TaskCard]] = field(
        default_factory=lambda: {
            "todo": [],
            "in_progress": [],
            "done": [],
            "blocked": [],
        }
    )


class CommandCenter:
    """Fleet management dashboard for tracking agents and tasks."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_file = root / "state" / "command_center.json"
        self.agents: dict[str, AgentStatus] = {}
        self.board = TaskBoard()
        self._lock = threading.RLock()
        self._load()

    # --- persistence -----------------------------------------------------

    def _load(self) -> None:
        if not self.state_file.exists():
            return
        data = json.loads(self.state_file.read_text(encoding="utf-8"))
        self._load_agents(data.get("agents", []))
        self._load_board(data.get("board", {}))

    def _load_agents(self, agents_data: list[dict[str, Any]]) -> None:
        for entry in agents_data:
            agent = AgentStatus(**entry)
            self.agents[agent.agent_id] = agent

    def _load_board(self, board_data: dict[str, Any]) -> None:
        columns: dict[str, list[TaskCard]] = {col: [] for col in VALID_COLUMNS}
        for col, cards in board_data.get("columns", {}).items():
            if col in VALID_COLUMNS:
                columns[col] = [TaskCard(**c) for c in cards]
        self.board = TaskBoard(columns=columns)

    def _save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.export_state(), indent=2, default=str)
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=self.state_file.parent, suffix=".json.tmp"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp_path, self.state_file)
        except Exception:
            os.remove(tmp_path)
            raise

    # --- agent lifecycle -------------------------------------------------

    def register_agent(self, agent_id: str, persona: str) -> dict[str, Any]:
        """Register a new agent in the fleet."""
        with self._lock:
            if agent_id in self.agents:
                return {"ok": False, "error": f"Agent '{agent_id}' already registered"}
            self.agents[agent_id] = AgentStatus(
                agent_id=agent_id,
                persona=persona,
                started_at=datetime.now(timezone.utc).isoformat(),
            )
            self._save()
            return {"ok": True, "agent_id": agent_id}

    def update_agent_status(
        self,
        agent_id: str,
        status: str,
        task: str | None = None,
        progress: int | None = None,
    ) -> dict[str, Any]:
        """Update an agent's status, current task, and progress."""
        with self._lock:
            agent = self.agents.get(agent_id)
            if agent is None:
                return {"ok": False, "error": f"Agent '{agent_id}' not found"}
            if status not in VALID_STATES:
                return {"ok": False, "error": f"Invalid status '{status}'"}
            agent.status = status  # type: ignore[assignment]
            if task is not None:
                agent.current_task = task
            if progress is not None:
                agent.progress = max(0, min(100, progress))
            self._save()
            return {"ok": True, "agent_id": agent_id, "status": status}

    def unregister_agent(self, agent_id: str) -> dict[str, Any]:
        """Remove an agent from the fleet."""
        with self._lock:
            if agent_id not in self.agents:
                return {"ok": False, "error": f"Agent '{agent_id}' not found"}
            del self.agents[agent_id]
            self._save()
            return {"ok": True, "agent_id": agent_id}

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents."""
        with self._lock:
            return [asdict(a) for a in self.agents.values()]

    def list_active_agents(self) -> list[dict[str, Any]]:
        """List only agents whose status is ``running``."""
        with self._lock:
            return [asdict(a) for a in self.agents.values() if a.status == "running"]

    def get_agent_details(self, agent_id: str) -> dict[str, Any]:
        """Return detailed info for a single agent including assigned tasks."""
        with self._lock:
            agent = self.agents.get(agent_id)
            if agent is None:
                return {"ok": False, "error": f"Agent '{agent_id}' not found"}
            return {"ok": True, "agent": asdict(agent), "tasks": self._agent_tasks(agent_id)}

    def _agent_tasks(self, agent_id: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for col, cards in self.board.columns.items():
            for card in cards:
                if card.assignee == agent_id:
                    entry = asdict(card)
                    entry["column"] = col
                    result.append(entry)
        return result

    # --- task board ------------------------------------------------------

    def add_task(self, card: TaskCard) -> dict[str, Any]:
        """Add a task card to the board."""
        with self._lock:
            if not card.id:
                card.id = uuid.uuid4().hex
            if card.status not in VALID_COLUMNS:
                card.status = "todo"
            self.board.columns[card.status].append(card)
            self._save()
            return {"ok": True, "task_id": card.id}

    def move_task(self, task_id: str, column: str) -> dict[str, Any]:
        """Move a task card to a different column."""
        with self._lock:
            if column not in VALID_COLUMNS:
                return {"ok": False, "error": f"Invalid column '{column}'"}
            card, source = self._find_task(task_id)
            if card is None:
                return {"ok": False, "error": f"Task '{task_id}' not found"}
            if source == column:
                return {"ok": True, "task_id": task_id, "column": column, "moved": False}
            self.board.columns[source].remove(card)  # type: ignore[index]
            card.status = column  # type: ignore[assignment]
            self.board.columns[column].append(card)
            self._save()
            return {"ok": True, "task_id": task_id, "column": column, "moved": True}

    def _find_task(self, task_id: str) -> tuple[TaskCard | None, str | None]:
        for col, cards in self.board.columns.items():
            for card in cards:
                if card.id == task_id:
                    return card, col
        return None, None

    def get_board(self) -> dict[str, Any]:
        """Return the full Kanban board state."""
        with self._lock:
            return {
                col: [asdict(c) for c in cards]
                for col, cards in self.board.columns.items()
            }

    # --- summary & export ------------------------------------------------

    def get_fleet_summary(self) -> dict[str, Any]:
        """Return summary stats for the fleet."""
        with self._lock:
            counts: dict[str, int] = dict.fromkeys(VALID_STATES, 0)
            for agent in self.agents.values():
                counts[agent.status] += 1
            return {
                "total": len(self.agents),
                "active": counts["running"],
                "idle": counts["idle"],
                "blocked": counts["blocked"],
                "done": counts["done"],
            }

    def export_state(self) -> dict[str, Any]:
        """Serialize the entire command center state."""
        with self._lock:
            return {
                "agents": [asdict(a) for a in self.agents.values()],
                "board": {
                    "columns": {
                        col: [asdict(c) for c in cards]
                        for col, cards in self.board.columns.items()
                    }
                },
            }

    def import_state(self, data: dict[str, Any]) -> dict[str, Any]:
        """Replace the current state with the provided data."""
        with self._lock:
            self.agents.clear()
            self._load_agents(data.get("agents", []))
            self._load_board(data.get("board", {}))
            self._save()
            return {"ok": True, "agents": len(self.agents)}
