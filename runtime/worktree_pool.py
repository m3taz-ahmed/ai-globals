#!/usr/bin/env python3
"""Parallel agent execution via git worktrees for aiZee.

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

import hashlib
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
    assignment_file: Path | None = None  # Tether file for crash recovery
    respawn_count: int = 0  # Track restarts (stall detection)
    last_output_hash: str = ""  # For stall detection via output hashing
    last_check_time: float = 0.0  # Last stall check timestamp


def _atomic_write_verify(path: Path, content: str) -> bool:
    """Write file atomically with fsync and post-write verification."""
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        with open(tmp, "r+b") as f:
            os.fsync(f.fileno())
        tmp.replace(path)
        return path.read_text(encoding="utf-8") == content
    except OSError:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return False


@dataclass
class TetherFile:
    """Persistent assignment file for crash recovery (from sol).

    Each work assignment is written to disk atomically. On crash,
    the tether file allows recovery of the agent's last assignment.
    """

    tether_dir: Path

    def __post_init__(self) -> None:
        self.tether_dir.mkdir(parents=True, exist_ok=True)

    def write(self, agent_id: str, assignment: str) -> bool:
        """Write a tether file for an agent's assignment."""
        path = self.tether_dir / f"{agent_id}.tether"
        return _atomic_write_verify(path, assignment)

    def read(self, agent_id: str) -> str | None:
        """Read an agent's tether file."""
        path = self.tether_dir / f"{agent_id}.tether"
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    def remove(self, agent_id: str) -> bool:
        """Remove an agent's tether file."""
        path = self.tether_dir / f"{agent_id}.tether"
        try:
            if path.exists():
                path.unlink()
            return True
        except OSError:
            return False


@dataclass
class StallDetector:
    """Detect stalled agents via output hashing (from sol sentinel).

    Monitors agent output by hashing recent output. If the hash
    doesn't change over a configurable interval, the agent is
    considered stalled.
    """

    stall_timeout_seconds: float = 600.0  # 10 minutes default
    max_respawns: int = 2

    def check_stalled(self, wt: Worktree, current_output: str) -> bool:
        """Check if a worktree's agent is stalled.

        Returns True if output hasn't changed since last check AND
        enough time has passed.
        """
        now = time.time()
        output_hash = hashlib.sha256(current_output.encode("utf-8")).hexdigest()[:16]
        if wt.last_output_hash == output_hash:
            # Output unchanged — check if enough time has passed
            if wt.last_check_time > 0 and (now - wt.last_check_time) >= self.stall_timeout_seconds:
                return True
        else:
            # Output changed — update hash and reset timer
            wt.last_output_hash = output_hash
            wt.last_check_time = now
        return False

    def should_respawn(self, wt: Worktree) -> bool:
        """Check if agent should be respawned (under max respawns)."""
        return wt.respawn_count < self.max_respawns

    def record_respawn(self, wt: Worktree) -> None:
        """Record a respawn event."""
        wt.respawn_count += 1
        wt.last_output_hash = ""
        wt.last_check_time = time.time()


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
    stall_detector: StallDetector = field(default_factory=StallDetector)
    tether: TetherFile | None = None

    def __post_init__(self) -> None:
        self.worktree_base = self.project_root.parent / ".ai-worktrees"
        self.worktree_base.mkdir(parents=True, exist_ok=True)
        tether_dir = self.worktree_base / ".tethers"
        self.tether = TetherFile(tether_dir)

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
        wt = Worktree(
            id=wt_id,
            agent_id=agent_id,
            branch=branch,
            path=wt_path,
            created_at=datetime.now(UTC).isoformat(),
        )
        # Write tether file for crash recovery
        if self.tether:
            assignment = json.dumps({"agent_id": agent_id, "branch": branch, "created_at": wt.created_at})
            self.tether.write(agent_id, assignment)
            wt.assignment_file = self.tether.tether_dir / f"{agent_id}.tether"
        self._worktrees[wt_id] = wt
        return wt

    def get(self, agent_id: str) -> Worktree | None:
        """Get a worktree by agent ID."""
        return self._worktrees.get(agent_id)

    def list_active(self) -> list[Worktree]:
        """List all active worktrees."""
        return [wt for wt in self._worktrees.values() if wt.status == "active"]

    def check_stalled(self, agent_id: str, current_output: str) -> bool:
        """Check if an agent is stalled via output hashing."""
        wt = self._worktrees.get(agent_id)
        if wt is None:
            return False
        return self.stall_detector.check_stalled(wt, current_output)

    def respawn(self, agent_id: str) -> bool:
        """Attempt to respawn a stalled agent (if under max respawns)."""
        wt = self._worktrees.get(agent_id)
        if wt is None:
            return False
        if not self.stall_detector.should_respawn(wt):
            return False
        self.stall_detector.record_respawn(wt)
        return True

    def read_tether(self, agent_id: str) -> str | None:
        """Read an agent's tether file for crash recovery."""
        if self.tether:
            return self.tether.read(agent_id)
        return None

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
        # Remove tether file
        if self.tether:
            self.tether.remove(agent_id)
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
                    "respawn_count": wt.respawn_count,
                    "has_tether": wt.assignment_file is not None and wt.assignment_file.exists(),
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
