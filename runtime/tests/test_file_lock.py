"""Tests for runtime/file_lock.py — Single-Writer Locking."""

from __future__ import annotations

import time
from pathlib import Path

from runtime.file_lock import LockInfo, LockState, WorkLogLock


class TestWorkLogLock:
    """Tests for atomic work-log locking."""

    def test_acquire_new_lock(self, tmp_path: Path) -> None:
        lock = WorkLogLock(tmp_path)
        result = lock.acquire("feature-a", owner="agent-1", session="s1")
        assert result == LockState.ACQUIRED

    def test_acquire_releases_expired_lock(self, tmp_path: Path) -> None:
        lock = WorkLogLock(tmp_path, ttl_seconds=0.01)
        lock.acquire("feature-a", owner="agent-1", session="s1")
        time.sleep(0.02)
        result = lock.acquire("feature-a", owner="agent-2", session="s2")
        assert result == LockState.ACQUIRED

    def test_held_by_other_session(self, tmp_path: Path) -> None:
        lock = WorkLogLock(tmp_path, ttl_seconds=3600)
        lock.acquire("feature-a", owner="agent-1", session="s1")
        result = lock.acquire("feature-a", owner="agent-2", session="s2")
        assert result == LockState.HELD_BY_OTHER

    def test_same_owner_can_refresh(self, tmp_path: Path) -> None:
        lock = WorkLogLock(tmp_path, ttl_seconds=3600)
        lock.acquire("feature-a", owner="agent-1", session="s1")
        result = lock.acquire("feature-a", owner="agent-1", session="s1", phase="building")
        assert result == LockState.ACQUIRED

    def test_release_owned_lock(self, tmp_path: Path) -> None:
        lock = WorkLogLock(tmp_path)
        lock.acquire("feature-a", owner="agent-1", session="s1")
        assert lock.release("feature-a", owner="agent-1") is True

    def test_release_by_wrong_owner_fails(self, tmp_path: Path) -> None:
        lock = WorkLogLock(tmp_path)
        lock.acquire("feature-a", owner="agent-1", session="s1")
        assert lock.release("feature-a", owner="agent-2") is False

    def test_release_nonexistent_fails(self, tmp_path: Path) -> None:
        lock = WorkLogLock(tmp_path)
        assert lock.release("nonexistent", owner="agent-1") is False

    def test_lock_file_is_atomic(self, tmp_path: Path) -> None:
        lock = WorkLogLock(tmp_path)
        lock.acquire("feature-a", owner="agent-1", session="s1")
        lock_file = tmp_path / "feature-a.lock.json"
        assert lock_file.exists()
        # No temp file should remain
        assert not (tmp_path / "feature-a.lock.tmp.json").exists()

    def test_branch_name_sanitized(self, tmp_path: Path) -> None:
        lock = WorkLogLock(tmp_path)
        lock.acquire("feature/sub-branch", owner="a1", session="s1")
        assert (tmp_path / "feature_sub-branch.lock.json").exists()

    def test_lock_info_stored(self, tmp_path: Path) -> None:
        lock = WorkLogLock(tmp_path)
        lock.acquire("feature-a", owner="agent-1", session="s1", phase="testing")
        lock_file = tmp_path / "feature-a.lock.json"
        import json
        data = json.loads(lock_file.read_text(encoding="utf-8"))
        assert data["owner"] == "agent-1"
        assert data["session"] == "s1"
        assert data["phase"] == "testing"


class TestLockInfo:
    def test_to_dict_and_from_dict_roundtrip(self) -> None:
        info = LockInfo(
            owner="a1", session="s1", branch="feat",
            phase="build", acquired_at=1000.0, expires_at=2000.0,
        )
        d = info.to_dict()
        restored = LockInfo.from_dict(d)
        assert restored.owner == info.owner
        assert restored.session == info.session
        assert restored.branch == info.branch
