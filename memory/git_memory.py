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
    |-- facts/
    |   |-- 001.json
    |   `-- 002.json
    |-- preferences/
    |   `-- 001.json
    |-- corrections/
    |   `-- 001.json
    `-- sessions/
        `-- 2026-01-01.json

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
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

# Safe single path component: no separators, no "..", bounded length.
_SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _safe_component(value: str, kind: str) -> str:
    """Validate a category/entry_id as a safe single path component."""
    if not _SAFE_COMPONENT_RE.match(value) or ".." in value:
        raise ValueError(f"Unsafe git-memory {kind}: {value!r}")
    return value


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
        _safe_component(category, "category")
        _safe_component(entry_id, "entry_id")
        cat_dir = self.repo_path / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        file_path = cat_dir / f"{entry_id}.json"
        now = datetime.now(timezone.utc).isoformat()
        existing = ""
        if file_path.exists():
            existing = file_path.read_text(encoding="utf-8")
        created_at = now
        if existing:
            try:
                created_at = json.loads(existing).get("created_at", now)
            except (ValueError, AttributeError):
                created_at = now
        entry = MemoryEntry(
            id=entry_id,
            category=category,
            content=content,
            created_at=created_at,
            updated_at=now,
        )
        file_path.write_text(entry.to_json(), encoding="utf-8")
        return file_path

    def read(self, category: str, entry_id: str) -> MemoryEntry | None:
        """Read a memory entry from the store. Corrupt files yield None."""
        _safe_component(category, "category")
        _safe_component(entry_id, "entry_id")
        file_path = self.repo_path / category / f"{entry_id}.json"
        if not file_path.exists():
            return None
        try:
            return MemoryEntry.from_json(file_path.read_text(encoding="utf-8"))
        except (ValueError, KeyError, TypeError, OSError, UnicodeDecodeError):
            return None

    def delete(self, category: str, entry_id: str) -> bool:
        """Delete a memory entry."""
        _safe_component(category, "category")
        _safe_component(entry_id, "entry_id")
        file_path = self.repo_path / category / f"{entry_id}.json"
        if not file_path.exists():
            return False
        file_path.unlink()
        return True

    def list_entries(self, category: str | None = None) -> list[str]:
        """List all entry IDs, optionally filtered by category."""
        entries: list[str] = []
        if category:
            _safe_component(category, "category")
            cat_dir = self.repo_path / category
            if cat_dir.exists():
                entries = [f.stem for f in cat_dir.glob("*.json")]
        else:
            for cat_dir in self.repo_path.iterdir():
                if cat_dir.is_dir() and cat_dir.name != ".git":
                    entries.extend(f.stem for f in cat_dir.glob("*.json"))
        return sorted(entries)

    def commit(self, message: str) -> bool:
        """Stage tracked memory files and commit to the memory repo.

        Stages only ``*.json`` under the repo root (never ``git add -A``,
        which could sweep up accidentally dropped secrets).
        """
        self._git("add", "--", "*.json")
        # Check if there are changes to commit
        status = self._git("status", "--porcelain", check=False)
        if status.stdout.strip() == "":
            return False  # Nothing to commit
        if not message or len(message) > 500:
            raise ValueError("Commit message must be 1..500 chars")
        self._git("commit", "-m", message)
        return True

    def log(self, limit: int = 20) -> list[dict[str, str]]:
        """Return commit history."""
        try:
            limit = max(1, min(int(limit), 200))
        except (TypeError, ValueError):
            limit = 20
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

    _REF_RE: ClassVar[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@-]{0,127}$")

    def _safe_ref(self, ref: str, what: str = "ref") -> str:
        """Validate a git ref/branch/remote name (blocks option injection)."""
        if not isinstance(ref, str) or self._REF_RE.match(ref) is None or ref.startswith("-"):
            raise ValueError(f"Invalid git {what} {ref!r}")
        return ref

    def diff(self, ref: str = "HEAD~1") -> str:
        """Show diff between HEAD and a reference (default: previous commit)."""
        # No `--` here: these are revisions, not paths (`--` would turn the
        # ref into a pathspec). Option injection is blocked by _safe_ref
        # (rejects leading `-`).
        result = self._git("diff", self._safe_ref(ref), "HEAD", check=False)
        return result.stdout

    def checkout(self, ref: str) -> bool:
        """Checkout a specific commit or branch (time-travel)."""
        result = self._git("checkout", self._safe_ref(ref), check=False)
        return result.returncode == 0

    def create_branch(self, name: str) -> bool:
        """Create and checkout a new branch (e.g., for a persona)."""
        result = self._git("checkout", "-b", self._safe_ref(name, "branch"), check=False)
        return result.returncode == 0

    def switch_branch(self, name: str) -> bool:
        """Switch to an existing branch."""
        result = self._git("checkout", self._safe_ref(name, "branch"), check=False)
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
        result = self._git(
            "push", self._safe_ref(remote, "remote"), self._safe_ref(branch, "branch"),
            check=False,
        )
        return result.returncode == 0

    def pull(self, remote: str = "origin", branch: str = "main") -> bool:
        """Pull memory from a remote repository."""
        result = self._git(
            "pull", self._safe_ref(remote, "remote"), self._safe_ref(branch, "branch"),
            check=False,
        )
        return result.returncode == 0

    # Allowed git remote URL schemes. ``ext::`` and ``file://`` are rejected
    # because they can execute arbitrary commands or read local paths. SSH and
    # git@...:user/repo forms are allowed for trusted private remotes.
    _SAFE_REMOTE_SCHEMES: ClassVar[frozenset[str]] = frozenset({"https", "http", "ssh", "git"})
    _REMOTE_NAME_RE: ClassVar[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

    def _validate_remote_url(self, url: str) -> None:
        """Validate a git remote URL against a safe scheme/host allowlist.

        Rejects ``ext::`` (command execution), ``file://`` (local path access),
        and other unsafe protocols that git would otherwise happily pass to
        the shell. Raises ``ValueError`` on invalid URLs.
        """
        if not url:
            raise ValueError("Remote URL must not be empty")
        # Reject the ext:: transport outright — it runs arbitrary commands.
        if url.startswith("ext::"):
            raise ValueError(
                "git 'ext::' transport is forbidden (arbitrary command execution)"
            )
        # Handle SCP-style: git@host:user/repo
        if "@" in url and ":" in url and not url.startswith(("http://", "https://", "ssh://", "git://")):
            # git@github.com:user/repo — allowed (SSH)
            return
        # URL-style: scheme://host/path
        if "://" in url:
            scheme = url.split("://", 1)[0].lower()
            if scheme == "file":
                raise ValueError("git 'file://' transport is forbidden (local path access)")
            if scheme not in self._SAFE_REMOTE_SCHEMES:
                raise ValueError(
                    f"Unsupported git remote scheme {scheme!r}; "
                    f"allowed: {sorted(self._SAFE_REMOTE_SCHEMES)}"
                )
            return
        # Bare path (relative/absolute) — reject; must be a real remote URL.
        raise ValueError(
            f"Invalid git remote URL {url!r}; expected https://, http://, "
            f"ssh://, git://, or git@host:user/repo form"
        )

    def add_remote(self, name: str, url: str) -> bool:
        """Add a remote repository.

        Validates the remote name (safe component) and URL scheme before
        invoking git, blocking unsafe transports (``ext::``, ``file://``).
        """
        if not self._REMOTE_NAME_RE.match(name):
            raise ValueError(f"Invalid remote name {name!r}")
        self._validate_remote_url(url)
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
