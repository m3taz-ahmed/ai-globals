"""Tests for sub-agent orchestrator."""

from __future__ import annotations

from pathlib import Path

from runtime.kernel import Kernel


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
