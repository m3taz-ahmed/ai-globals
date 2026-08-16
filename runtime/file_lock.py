#!/usr/bin/env python3
"""Single-writer locking for concurrent session prevention.

Implements atomic lock files that block concurrent work-log corruption
in multi-agent scenarios. One branch = one owner. Lock files are
written atomically with fsync and post-write verification.

Inspired by agentic-os ``recover_worklog_lock.py``.

Usage::

    from runtime.file_lock import WorkLogLock

    lock = WorkLogLock(Path(".ai/locks"))
    result = lock.acquire("feature-branch", owner="agent-1", session="s1")
    if result == LockState.ACQUIRED:
        # ... do work ...
        lock.release("feature-branch", owner="agent-1")
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class LockState(str, Enum):
    """Result of a lock acquisition attempt."""

    ACQUIRED = "acquired"        # Created or refreshed (proceed)
    HELD_BY_OTHER = "held"       # Active, held by another session
    FS_FAILURE = "fs_failure"    # Persistent filesystem failure


@dataclass
class LockInfo:
    """Metadata stored in a lock file."""

    owner: str
    session: str
    branch: str
    phase: str
    acquired_at: float
    expires_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "session": self.session,
            "branch": self.branch,
            "phase": self.phase,
            "acquired_at": self.acquired_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LockInfo:
        return cls(
            owner=data.get("owner", ""),
            session=data.get("session", ""),
            branch=data.get("branch", ""),
            phase=data.get("phase", ""),
            acquired_at=data.get("acquired_at", 0.0),
            expires_at=data.get("expires_at", 0.0),
        )


class WorkLogLock:
    """Atomic lock files for concurrent session prevention.

    One branch = one owner. Locks expire after a TTL to prevent
    orphaned locks from blocking progress indefinitely.
    """

    def __init__(self, lock_dir: Path, ttl_seconds: float = 3600.0) -> None:
        self.lock_dir = lock_dir
        self.ttl_seconds = ttl_seconds
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def _lock_path(self, branch: str) -> Path:
        safe = branch.replace("/", "_").replace("\\", "_")
        return self.lock_dir / f"{safe}.lock.json"

    def acquire(
        self,
        branch: str,
        owner: str,
        session: str,
        phase: str = "entering",
    ) -> LockState:
        """Acquire or refresh a work log lock.

        Returns:
        - ACQUIRED: created, updated, or recovered (proceed)
        - HELD_BY_OTHER: active lock held by another session
        - FS_FAILURE: persistent filesystem failure
        """
        path = self._lock_path(branch)
        now = time.time()
        new_info = LockInfo(
            owner=owner, session=session, branch=branch,
            phase=phase, acquired_at=now, expires_at=now + self.ttl_seconds,
        )
        existing = self._read_lock(path)
        if existing and not self._is_expired(existing, now) and (existing.owner != owner or existing.session != session):
            return LockState.HELD_BY_OTHER
        if not self._atomic_write(path, new_info.to_dict()):
            return LockState.FS_FAILURE
        return LockState.ACQUIRED

    def release(self, branch: str, owner: str) -> bool:
        """Release a lock if owned by the given owner."""
        path = self._lock_path(branch)
        existing = self._read_lock(path)
        if not existing or existing.owner != owner:
            return False
        try:
            path.unlink()
            return True
        except OSError:
            return False

    def _read_lock(self, path: Path) -> LockInfo | None:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return LockInfo.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _is_expired(info: LockInfo, now: float) -> bool:
        return now > info.expires_at

    @staticmethod
    def _atomic_write(path: Path, data: dict[str, Any]) -> bool:
        """Write lock file atomically with fsync and verification."""
        tmp = path.with_suffix(".tmp")
        try:
            content = json.dumps(data, indent=2)
            tmp.write_text(content, encoding="utf-8")
            with open(tmp, "r+b") as f:
                os.fsync(f.fileno())
            tmp.replace(path)
            # Post-write verification
            return path.read_text(encoding="utf-8") == content
        except OSError:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
            return False


if __name__ == "__main__":
    lock = WorkLogLock(Path(".ai/locks"))
    result = lock.acquire("main", owner="test", session="s1")
    print(f"Lock result: {result.value}")
    lock.release("main", owner="test")
