"""Tests for sub-agent orchestrator."""

from __future__ import annotations

from pathlib import Path

from runtime.kernel import Kernel
from runtime.orchestrator import AgentPool


def test_kernel_agent_lifecycle(tmp_path: Path) -> None:
    k = Kernel(tmp_path, tmp_path)
    spawn = k.spawn_agent("reviewer", "code-reviewer", ["Read", "Review"])
    assert spawn["ok"] is True
    assert spawn["id"] == "reviewer"

    delegate = k.delegate("reviewer", "Read", path="spec.md", approved=True)
    assert delegate["ok"] is True

    denied = k.delegate("reviewer", "Bash", command="ls", approved=True)
    assert denied["ok"] is False

    agents = k.pool.list_agents()
    assert len(agents) == 1


def test_delegate_nonexistent_agent_returns_error(tmp_path: Path) -> None:
    """Cover line 71: delegate returns error for unknown agent_id."""
    for sub in ("runtime/policies", "state"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    pool = AgentPool(tmp_path)
    result = pool.delegate("ghost", "Read")
    assert not result["ok"]
    assert "not found" in result["error"]


def test_synchronize_returns_all_agent_states(tmp_path: Path) -> None:
    """Cover lines 78-79: synchronize returns status for all registered agents."""
    for sub in ("runtime/policies", "state"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    pool = AgentPool(tmp_path)
    pool.register("agent-a", ["DEV"], ["Read"])
    pool.register("agent-b", ["QA"], ["Review"])
    sync = pool.synchronize()
    assert "agent-a" in sync
    assert "agent-b" in sync
    assert sync["agent-a"]["persona"] == "DEV"
    assert sync["agent-b"]["persona"] == "QA"
    assert "status" in sync["agent-a"]
