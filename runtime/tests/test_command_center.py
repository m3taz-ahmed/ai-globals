"""Tests for runtime/command_center.py — Agent Command Center dashboard."""

from __future__ import annotations

import json
from pathlib import Path

from runtime.command_center import (
    VALID_COLUMNS,
    AgentStatus,
    CommandCenter,
    TaskBoard,
    TaskCard,
)

# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------

def make_card(
    title: str = "Sample task",
    card_id: str = "",
    assignee: str | None = None,
    status: str = "todo",
    priority: str = "medium",
    tags: list[str] | None = None,
) -> TaskCard:
    return TaskCard(
        id=card_id,
        title=title,
        assignee=assignee,
        status=status,  # type: ignore[arg-type]
        priority=priority,  # type: ignore[arg-type]
        tags=tags or [],
    )


# ---------------------------------------------------------------------------
# AgentStatus dataclass
# ---------------------------------------------------------------------------

class TestAgentStatusDataclass:
    def test_defaults(self) -> None:
        agent = AgentStatus(agent_id="a1", persona="backend")
        assert agent.status == "idle"
        assert agent.progress == 0
        assert agent.current_task is None
        assert agent.worktree_path is None

    def test_invalid_status_defaults_to_idle(self) -> None:
        agent = AgentStatus(agent_id="a1", persona="backend", status="flying")  # type: ignore[arg-type]
        assert agent.status == "idle"

    def test_progress_clamped_to_range(self) -> None:
        low = AgentStatus(agent_id="a1", persona="p", progress=-10)
        high = AgentStatus(agent_id="a2", persona="p", progress=150)
        assert low.progress == 0
        assert high.progress == 100


# ---------------------------------------------------------------------------
# TaskCard & TaskBoard dataclasses
# ---------------------------------------------------------------------------

class TestTaskCardDataclass:
    def test_defaults(self) -> None:
        card = TaskCard(id="t1", title="Do thing")
        assert card.status == "todo"
        assert card.priority == "medium"
        assert card.tags == []

    def test_invalid_status_defaults_to_todo(self) -> None:
        card = TaskCard(id="t1", title="x", status="archived")  # type: ignore[arg-type]
        assert card.status == "todo"

    def test_invalid_priority_defaults_to_medium(self) -> None:
        card = TaskCard(id="t1", title="x", priority="urgent")  # type: ignore[arg-type]
        assert card.priority == "medium"


class TestTaskBoardDataclass:
    def test_default_columns_present(self) -> None:
        board = TaskBoard()
        for col in VALID_COLUMNS:
            assert col in board.columns
            assert board.columns[col] == []


# ---------------------------------------------------------------------------
# Agent registration and lifecycle
# ---------------------------------------------------------------------------

class TestAgentRegistration:
    def test_register_agent_success(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        result = cc.register_agent("a1", "backend")
        assert result["ok"] is True
        assert result["agent_id"] == "a1"

    def test_register_agent_sets_started_at(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "backend")
        details = cc.get_agent_details("a1")
        assert details["ok"] is True
        assert details["agent"]["started_at"] is not None

    def test_duplicate_registration_fails(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "backend")
        result = cc.register_agent("a1", "frontend")
        assert result["ok"] is False
        assert "already registered" in result["error"]

    def test_unregister_agent_success(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "backend")
        result = cc.unregister_agent("a1")
        assert result["ok"] is True
        assert cc.list_agents() == []

    def test_unregister_nonexistent_agent_fails(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        result = cc.unregister_agent("ghost")
        assert result["ok"] is False
        assert "not found" in result["error"]


# ---------------------------------------------------------------------------
# Agent status updates
# ---------------------------------------------------------------------------

class TestAgentStatusUpdate:
    def test_update_status_success(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "backend")
        result = cc.update_agent_status("a1", "running", task="build", progress=50)
        assert result["ok"] is True
        agent = cc.get_agent_details("a1")["agent"]
        assert agent["status"] == "running"
        assert agent["current_task"] == "build"
        assert agent["progress"] == 50

    def test_update_status_nonexistent_agent(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        result = cc.update_agent_status("ghost", "running")
        assert result["ok"] is False
        assert "not found" in result["error"]

    def test_update_status_invalid_status(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "backend")
        result = cc.update_agent_status("a1", "flying")
        assert result["ok"] is False
        assert "Invalid status" in result["error"]

    def test_update_progress_clamped(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "backend")
        cc.update_agent_status("a1", "running", progress=200)
        agent = cc.get_agent_details("a1")["agent"]
        assert agent["progress"] == 100


# ---------------------------------------------------------------------------
# Agent listing
# ---------------------------------------------------------------------------

class TestAgentListing:
    def test_list_agents_empty(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        assert cc.list_agents() == []

    def test_list_agents_returns_all(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "backend")
        cc.register_agent("a2", "frontend")
        ids = {a["agent_id"] for a in cc.list_agents()}
        assert ids == {"a1", "a2"}

    def test_list_active_agents_filters_running(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "backend")
        cc.register_agent("a2", "frontend")
        cc.update_agent_status("a1", "running")
        active = cc.list_active_agents()
        assert len(active) == 1
        assert active[0]["agent_id"] == "a1"


# ---------------------------------------------------------------------------
# Task board operations
# ---------------------------------------------------------------------------

class TestTaskBoardOperations:
    def test_add_task_to_todo(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        result = cc.add_task(make_card("Build API"))
        assert result["ok"] is True
        board = cc.get_board()
        assert len(board["todo"]) == 1
        assert board["todo"][0]["title"] == "Build API"

    def test_add_task_generates_id_when_empty(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        result = cc.add_task(make_card("Task"))
        assert result["task_id"] != ""

    def test_add_task_with_explicit_id(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.add_task(make_card("Task", card_id="T-100"))
        board = cc.get_board()
        assert board["todo"][0]["id"] == "T-100"

    def test_move_task_to_in_progress(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.add_task(make_card("Task", card_id="t1"))
        result = cc.move_task("t1", "in_progress")
        assert result["ok"] is True
        assert result["moved"] is True
        board = cc.get_board()
        assert len(board["todo"]) == 0
        assert len(board["in_progress"]) == 1

    def test_move_task_to_same_column_no_op(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.add_task(make_card("Task", card_id="t1"))
        result = cc.move_task("t1", "todo")
        assert result["ok"] is True
        assert result["moved"] is False

    def test_move_nonexistent_task_fails(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        result = cc.move_task("ghost", "done")
        assert result["ok"] is False
        assert "not found" in result["error"]

    def test_move_task_invalid_column_fails(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.add_task(make_card("Task", card_id="t1"))
        result = cc.move_task("t1", "archived")
        assert result["ok"] is False
        assert "Invalid column" in result["error"]

    def test_get_board_returns_all_columns(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        board = cc.get_board()
        for col in VALID_COLUMNS:
            assert col in board


# ---------------------------------------------------------------------------
# Fleet summary calculations
# ---------------------------------------------------------------------------

class TestFleetSummary:
    def test_empty_fleet_summary(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        summary = cc.get_fleet_summary()
        assert summary == {"total": 0, "active": 0, "idle": 0, "blocked": 0, "done": 0}

    def test_summary_counts_by_status(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "p")
        cc.register_agent("a2", "p")
        cc.register_agent("a3", "p")
        cc.register_agent("a4", "p")
        cc.update_agent_status("a1", "running")
        cc.update_agent_status("a2", "running")
        cc.update_agent_status("a3", "blocked")
        cc.update_agent_status("a4", "done")
        summary = cc.get_fleet_summary()
        assert summary["total"] == 4
        assert summary["active"] == 2
        assert summary["idle"] == 0
        assert summary["blocked"] == 1
        assert summary["done"] == 1


# ---------------------------------------------------------------------------
# Agent details with tasks
# ---------------------------------------------------------------------------

class TestAgentDetails:
    def test_details_includes_assigned_tasks(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "backend")
        cc.add_task(make_card("Task A", card_id="t1", assignee="a1"))
        cc.add_task(make_card("Task B", card_id="t2", assignee="a2"))
        details = cc.get_agent_details("a1")
        assert details["ok"] is True
        task_ids = {t["id"] for t in details["tasks"]}
        assert task_ids == {"t1"}

    def test_details_nonexistent_agent(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        details = cc.get_agent_details("ghost")
        assert details["ok"] is False
        assert "not found" in details["error"]


# ---------------------------------------------------------------------------
# State export / import
# ---------------------------------------------------------------------------

class TestStateExportImport:
    def test_export_returns_agents_and_board(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "backend")
        cc.add_task(make_card("Task", card_id="t1"))
        state = cc.export_state()
        assert len(state["agents"]) == 1
        assert "columns" in state["board"]

    def test_import_replaces_state(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "backend")
        cc.add_task(make_card("Old task", card_id="t1"))

        new_state = {
            "agents": [{"agent_id": "z1", "persona": "devops", "status": "running"}],
            "board": {"columns": {"todo": [], "in_progress": [], "done": [], "blocked": []}},
        }
        result = cc.import_state(new_state)
        assert result["ok"] is True
        assert result["agents"] == 1
        agents = cc.list_agents()
        assert len(agents) == 1
        assert agents[0]["agent_id"] == "z1"

    def test_export_import_roundtrip(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "backend")
        cc.update_agent_status("a1", "running", task="build", progress=75)
        cc.add_task(make_card("Task", card_id="t1", assignee="a1"))
        cc.move_task("t1", "in_progress")
        exported = cc.export_state()

        cc2 = CommandCenter(tmp_path)
        cc2.import_state(exported)
        assert cc2.get_fleet_summary()["total"] == 1
        board = cc2.get_board()
        assert len(board["in_progress"]) == 1
        agent = cc2.get_agent_details("a1")["agent"]
        assert agent["progress"] == 75


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_state_persisted_to_json_file(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "backend")
        cc.add_task(make_card("Task", card_id="t1"))
        assert cc.state_file.exists()
        data = json.loads(cc.state_file.read_text(encoding="utf-8"))
        assert len(data["agents"]) == 1
        assert len(data["board"]["columns"]["todo"]) == 1

    def test_reload_from_disk_restores_state(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        cc.register_agent("a1", "backend")
        cc.update_agent_status("a1", "running", progress=40)
        cc.add_task(make_card("Task", card_id="t1"))

        cc2 = CommandCenter(tmp_path)
        agents = cc2.list_agents()
        assert len(agents) == 1
        assert agents[0]["status"] == "running"
        assert agents[0]["progress"] == 40
        board = cc2.get_board()
        assert len(board["todo"]) == 1

    def test_no_state_file_starts_empty(self, tmp_path: Path) -> None:
        cc = CommandCenter(tmp_path)
        assert cc.list_agents() == []
        assert cc.get_board()["todo"] == []
