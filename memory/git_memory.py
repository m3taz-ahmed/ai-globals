#!/usr/bin/env python3
"""Git-backed memory layer for aiZee.

Manages agent memory as a git repository, providing:
- Versioned memory entries (commit history)
- Branch-based persona memories
- Push/pull for multi-agent collaboration
- Time-travel through memory history
- Diff-based memory change tracking

Memory entries are stored as JSON files in a directory structure::

    memory_repo/
    ├── facts/
    │   ├── 001.json
    │   └── 002.json
    ├── preferences/
    │   └── 001.json
    ├── corrections/
    │   └── 001.json
    └── sessions/
        └── 2026-01-01.json

Usage::

    from memory.git_memory import GitMemoryStore
    store = GitMemoryStore(Path(".ai/state/memory_repo"))
    store.init()
    store.write("facts", "python-is-great", {"content": "Python is great"})
    store.commit("Added python fact")
    history = store.log()
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class MemoryEntry:
    """A single memory entry."""

    id: str
    category: str  # facts, preferences, corrections, sessions
    content: dict[str, Any]
    created_at: str = ""
    updated_at: str = ""

    def to_json(self) -> str:
        return json.dumps({
            "id": self.id,
            "category": self.category,
            "content": self.content,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }, indent=2, default=str)

    @classmethod
    def from_json(cls, data: str) -> MemoryEntry:
        d = json.loads(data)
        return cls(
            id=d["id"],
            category=d["category"],
            content=d["content"],
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )


class GitMemoryStore:
    """Git-backed memory store for aiZee agents."""

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.repo_path.mkdir(parents=True, exist_ok=True)

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run a git command in the repo directory."""
        result = subprocess.run(
            ["git", *args],
            cwd=str(self.repo_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
        return result

    def init(self) -> None:
        """Initialize the git memory repository."""
        if not (self.repo_path / ".git").exists():
            self._git("init")
            self._git("config", "user.email", "agent@aizee")
            self._git("config", "user.name", "aiZee Agent")
        # Create category directories
        for category in ("facts", "preferences", "corrections", "sessions"):
            (self.repo_path / category).mkdir(exist_ok=True)

    def write(self, category: str, entry_id: str, content: dict[str, Any]) -> Path:
        """Write a memory entry to the store.

        Args:
            category: Memory category (facts, preferences, corrections, sessions).
            entry_id: Unique identifier for the entry.
            content: Memory content as a dict.

        Returns:
            Path to the written file.
        """
        cat_dir = self.repo_path / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        file_path = cat_dir / f"{entry_id}.json"
        now = datetime.now(timezone.utc).isoformat()
        existing = ""
        if file_path.exists():
            existing = file_path.read_text(encoding="utf-8")
        entry = MemoryEntry(
            id=entry_id,
            category=category,
            content=content,
            created_at=json.loads(existing).get("created_at", now) if existing else now,
            updated_at=now,
        )
        file_path.write_text(entry.to_json(), encoding="utf-8")
        return file_path

    def read(self, category: str, entry_id: str) -> MemoryEntry | None:
        """Read a memory entry from the store."""
        file_path = self.repo_path / category / f"{entry_id}.json"
        if not file_path.exists():
            return None
        return MemoryEntry.from_json(file_path.read_text(encoding="utf-8"))

    def delete(self, category: str, entry_id: str) -> bool:
        """Delete a memory entry."""
        file_path = self.repo_path / category / f"{entry_id}.json"
        if not file_path.exists():
            return False
        file_path.unlink()
        return True

    def list_entries(self, category: str | None = None) -> list[str]:
        """List all entry IDs, optionally filtered by category."""
        entries: list[str] = []
        if category:
            cat_dir = self.repo_path / category
            if cat_dir.exists():
                entries = [f.stem for f in cat_dir.glob("*.json")]
        else:
            for cat_dir in self.repo_path.iterdir():
                if cat_dir.is_dir() and cat_dir.name != ".git":
                    entries.extend(f.stem for f in cat_dir.glob("*.json"))
        return sorted(entries)

    def commit(self, message: str) -> bool:
        """Stage all changes and commit to the memory repo."""
        self._git("add", "-A")
        # Check if there are changes to commit
        status = self._git("status", "--porcelain", check=False)
        if status.stdout.strip() == "":
            return False  # Nothing to commit
        self._git("commit", "-m", message)
        return True

    def log(self, limit: int = 20) -> list[dict[str, str]]:
        """Return commit history."""
        result = self._git("log", f"-{limit}", "--pretty=format:%H|%an|%ad|%s", "--date=iso", check=False)
        if result.returncode != 0:
            return []
        commits: list[dict[str, str]] = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3],
                })
        return commits

    def diff(self, ref: str = "HEAD~1") -> str:
        """Show diff between HEAD and a reference (default: previous commit)."""
        result = self._git("diff", ref, "HEAD", check=False)
        return result.stdout

    def checkout(self, ref: str) -> bool:
        """Checkout a specific commit or branch (time-travel)."""
        result = self._git("checkout", ref, check=False)
        return result.returncode == 0

    def create_branch(self, name: str) -> bool:
        """Create and checkout a new branch (e.g., for a persona)."""
        result = self._git("checkout", "-b", name, check=False)
        return result.returncode == 0

    def switch_branch(self, name: str) -> bool:
        """Switch to an existing branch."""
        result = self._git("checkout", name, check=False)
        return result.returncode == 0

    def list_branches(self) -> list[str]:
        """List all branches."""
        result = self._git("branch", "--list", check=False)
        return [
            line.strip().lstrip("* ").strip()
            for line in result.stdout.strip().split("\n")
            if line.strip()
        ]

    def push(self, remote: str = "origin", branch: str = "main") -> bool:
        """Push memory to a remote repository."""
        result = self._git("push", remote, branch, check=False)
        return result.returncode == 0

    def pull(self, remote: str = "origin", branch: str = "main") -> bool:
        """Pull memory from a remote repository."""
        result = self._git("pull", remote, branch, check=False)
        return result.returncode == 0

    def add_remote(self, name: str, url: str) -> bool:
        """Add a remote repository."""
        result = self._git("remote", "add", name, url, check=False)
        return result.returncode == 0

    def status(self) -> dict[str, Any]:
        """Return repo status summary."""
        status_result = self._git("status", "--porcelain", check=False)
        branch_result = self._git("branch", "--show-current", check=False)
        log = self.log(limit=1)
        return {
            "branch": branch_result.stdout.strip() or "main",
            "dirty": bool(status_result.stdout.strip()),
            "changed_files": len(status_result.stdout.strip().split("\n")) if status_result.stdout.strip() else 0,
            "last_commit": log[0] if log else None,
            "total_entries": len(self.list_entries()),
        }


if __name__ == "__main__":
    import sys
    store = GitMemoryStore(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".ai/state/memory_repo"))
    store.init()
    print(json.dumps(store.status(), indent=2))
