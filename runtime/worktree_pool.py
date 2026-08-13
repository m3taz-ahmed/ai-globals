#!/usr/bin/env python3
"""Parallel agent execution via git worktrees for AI Global OS.

Allows multiple personas to work on the same project simultaneously
in isolated git worktrees. Each agent gets its own working directory
sharing the same git repository, enabling true parallel development
without file conflicts.

Features:
- Create worktrees for parallel agent execution
- Track active worktrees and their assigned agents
- Merge completed work back to the main branch
- Clean up worktrees after agent completion
- Automatic branch naming and management

Usage::

    from runtime.worktree_pool import WorktreePool
    pool = WorktreePool(Path("/project"))
    wt = pool.create("agent-arch", "feature/arch-design")
    # Agent works in wt.path
    pool.merge(wt.id)  # merge back to main
    pool.cleanup(wt.id)
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Worktree:
    """Represents a git worktree for parallel agent execution."""

    id: str
    agent_id: str
    branch: str
    path: Path
    created_at: str = ""
    status: str = "active"  # active, merged, abandoned


@dataclass
class WorktreePool:
    """Manages git worktrees for parallel agent execution.

    The pool is bound to a project root that must be a git repository.
    Worktrees are created in a ``.ai-worktrees/`` directory adjacent to
    the project root.
    """

    project_root: Path
    worktree_base: Path = field(default_factory=lambda: Path(".ai-worktrees"))
    _worktrees: dict[str, Worktree] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.worktree_base = self.project_root.parent / ".ai-worktrees"
        self.worktree_base.mkdir(parents=True, exist_ok=True)

    def _git(self, *args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run a git command."""
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd or self.project_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
        return result

    def create(self, agent_id: str, branch: str | None = None) -> Worktree:
        """Create a new worktree for an agent.

        Args:
            agent_id: Unique identifier for the agent.
            branch: Optional branch name. If None, auto-generates from agent_id.

        Returns:
            Worktree instance with the path to the working directory.
        """
        if branch is None:
            branch = f"agent/{agent_id}"
        wt_id = agent_id
        if wt_id in self._worktrees:
            raise ValueError(f"Worktree already exists for agent: {agent_id}")
        wt_path = self.worktree_base / agent_id
        if wt_path.exists():
            raise ValueError(f"Worktree path already exists: {wt_path}")
        # Create the worktree with a new branch
        self._git("worktree", "add", "-b", branch, str(wt_path))
        from datetime import datetime, timezone
        wt = Worktree(
            id=wt_id,
            agent_id=agent_id,
            branch=branch,
            path=wt_path,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._worktrees[wt_id] = wt
        return wt

    def get(self, agent_id: str) -> Worktree | None:
        """Get a worktree by agent ID."""
        return self._worktrees.get(agent_id)

    def list_active(self) -> list[Worktree]:
        """List all active worktrees."""
        return [wt for wt in self._worktrees.values() if wt.status == "active"]

    def list_all(self) -> list[Worktree]:
        """List all worktrees (including merged/abandoned)."""
        return list(self._worktrees.values())

    def merge(self, agent_id: str, target_branch: str = "main") -> bool:
        """Merge a worktree's branch back to the target branch.

        Args:
            agent_id: The agent whose worktree to merge.
            target_branch: The branch to merge into (default: main).

        Returns:
            True if merge succeeded, False otherwise.
        """
        wt = self._worktrees.get(agent_id)
        if wt is None:
            return False
        if wt.status != "active":
            return False
        try:
            # Checkout target branch in main repo
            self._git("checkout", target_branch, check=False)
            # Merge the agent's branch
            result = self._git("merge", "--no-ff", wt.branch, check=False)
            if result.returncode == 0:
                wt.status = "merged"
                return True
            # Merge conflict — abort
            self._git("merge", "--abort", check=False)
            return False
        except RuntimeError:
            return False

    def abandon(self, agent_id: str) -> bool:
        """Abandon a worktree without merging."""
        wt = self._worktrees.get(agent_id)
        if wt is None:
            return False
        wt.status = "abandoned"
        return True

    def cleanup(self, agent_id: str) -> bool:
        """Remove a worktree and its branch.

        Args:
            agent_id: The agent whose worktree to clean up.

        Returns:
            True if cleanup succeeded, False otherwise.
        """
        wt = self._worktrees.get(agent_id)
        if wt is None:
            return False
        try:
            # Remove the worktree
            self._git("worktree", "remove", str(wt.path), "--force", check=False)
            # Delete the branch
            self._git("branch", "-D", wt.branch, check=False)
        except RuntimeError:
            pass
        del self._worktrees[agent_id]
        return True

    def cleanup_all(self) -> int:
        """Clean up all worktrees. Returns count of cleaned worktrees."""
        count = 0
        for agent_id in list(self._worktrees.keys()):
            if self.cleanup(agent_id):
                count += 1
        return count

    def status(self) -> dict[str, Any]:
        """Return pool status summary."""
        active = [wt for wt in self._worktrees.values() if wt.status == "active"]
        merged = [wt for wt in self._worktrees.values() if wt.status == "merged"]
        abandoned = [wt for wt in self._worktrees.values() if wt.status == "abandoned"]
        return {
            "total": len(self._worktrees),
            "active": len(active),
            "merged": len(merged),
            "abandoned": len(abandoned),
            "worktrees": [
                {
                    "id": wt.id,
                    "agent_id": wt.agent_id,
                    "branch": wt.branch,
                    "path": str(wt.path),
                    "status": wt.status,
                    "created_at": wt.created_at,
                }
                for wt in self._worktrees.values()
            ],
        }

    def list_git_worktrees(self) -> list[dict[str, str]]:
        """List worktrees known to git (including external ones)."""
        result = self._git("worktree", "list", "--porcelain", check=False)
        worktrees: list[dict[str, str]] = []
        current: dict[str, str] = {}
        for line in result.stdout.strip().split("\n"):
            if not line:
                if current:
                    worktrees.append(current)
                    current = {}
            elif line.startswith("worktree "):
                current["path"] = line[9:]
            elif line.startswith("HEAD "):
                current["head"] = line[5:]
            elif line.startswith("branch "):
                current["branch"] = line[7:]
        if current:
            worktrees.append(current)
        return worktrees


if __name__ == "__main__":
    import json
    import sys
    pool = WorktreePool(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("."))
    print(json.dumps(pool.status(), indent=2))
