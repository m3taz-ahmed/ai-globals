"""Tests for runtime/managers/agent_manager.py."""

from __future__ import annotations

from pathlib import Path

from runtime.kernel import Kernel
from runtime.managers.agent_manager import AgentManager
from runtime.persona import PersonaDetector


def _setup_root(tmp_path: Path) -> Path:
    for sub in ("runtime/policies", "state"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    return tmp_path


class TestAgentManagerSpawn:
    def test_spawn_with_auto_persona(self, tmp_path: Path) -> None:
        root = _setup_root(tmp_path)
        mgr = AgentManager(root, PersonaDetector())
        result = mgr.spawn_agent("reviewer", "auto", ["Read", "Review"])
        assert result["ok"] is True
        assert result["id"] == "reviewer"
        assert "persona" in result

    def test_spawn_with_explicit_persona(self, tmp_path: Path) -> None:
        root = _setup_root(tmp_path)
        mgr = AgentManager(root, PersonaDetector())
        result = mgr.spawn_agent("dev-agent", "DEV", ["Read", "Write"])
        assert result["ok"] is True
        assert result["persona"] == "DEV"

    def test_spawn_with_empty_persona_string_returns_error(self, tmp_path: Path) -> None:
        """Cover line 38: persona splits to empty list returns error."""
        root = _setup_root(tmp_path)
        mgr = AgentManager(root, PersonaDetector())
        result = mgr.spawn_agent("bad-agent", ",,", ["Read"])
        assert result["ok"] is False
        assert "No persona provided" in result["error"]

    def test_delegate_to_nonexistent_agent(self, tmp_path: Path) -> None:
        root = _setup_root(tmp_path)
        mgr = AgentManager(root, PersonaDetector())
        result = mgr.delegate("ghost", "Read")
        assert result["ok"] is False

    def test_list_agents_empty(self, tmp_path: Path) -> None:
        root = _setup_root(tmp_path)
        mgr = AgentManager(root, PersonaDetector())
        assert mgr.list_agents() == []

    def test_list_agents_after_spawn(self, tmp_path: Path) -> None:
        root = _setup_root(tmp_path)
        mgr = AgentManager(root, PersonaDetector())
        mgr.spawn_agent("a1", "DEV", ["Read"])
        agents = mgr.list_agents()
        assert len(agents) == 1
        assert agents[0]["id"] == "a1"
