"""Tests for memory/git_memory.py — git-backed memory store."""

from __future__ import annotations

import contextlib
import io
import json
import runpy
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from memory.git_memory import GitMemoryStore, MemoryEntry

pytestmark = pytest.mark.slow


@pytest.fixture
def store(tmp_path: Path) -> GitMemoryStore:
    """Create a git memory store in a temp directory."""
    s = GitMemoryStore(tmp_path / "memory_repo")
    s.init()
    return s


class TestMemoryEntry:
    """Tests for MemoryEntry."""

    def test_to_json_roundtrip(self) -> None:
        entry = MemoryEntry(id="test", category="facts", content={"x": 1})
        json_str = entry.to_json()
        restored = MemoryEntry.from_json(json_str)
        assert restored.id == "test"
        assert restored.category == "facts"
        assert restored.content == {"x": 1}

    def test_to_json_structure(self) -> None:
        entry = MemoryEntry(id="test", category="facts", content={"x": 1}, created_at="2026")
        d = json.loads(entry.to_json())
        assert d["id"] == "test"
        assert d["category"] == "facts"
        assert d["content"] == {"x": 1}
        assert d["created_at"] == "2026"


class TestGitMemoryStore:
    """Tests for GitMemoryStore."""

    def test_init_creates_repo(self, tmp_path: Path) -> None:
        s = GitMemoryStore(tmp_path / "repo")
        s.init()
        assert (tmp_path / "repo" / ".git").exists()

    def test_init_creates_categories(self, tmp_path: Path) -> None:
        s = GitMemoryStore(tmp_path / "repo")
        s.init()
        for cat in ("facts", "preferences", "corrections", "sessions"):
            assert (tmp_path / "repo" / cat).exists()

    def test_init_idempotent(self, tmp_path: Path) -> None:
        s = GitMemoryStore(tmp_path / "repo")
        s.init()
        s.init()  # should not fail
        assert (tmp_path / "repo" / ".git").exists()

    def test_write_and_read(self, store: GitMemoryStore) -> None:
        store.write("facts", "test-1", {"content": "Python is great"})
        entry = store.read("facts", "test-1")
        assert entry is not None
        assert entry.content == {"content": "Python is great"}
        assert entry.id == "test-1"

    def test_read_nonexistent(self, store: GitMemoryStore) -> None:
        assert store.read("facts", "nonexistent") is None

    def test_write_preserves_created_at(self, store: GitMemoryStore) -> None:
        store.write("facts", "test-1", {"v": 1})
        entry1 = store.read("facts", "test-1")
        assert entry1 is not None
        created = entry1.created_at
        # Write again
        store.write("facts", "test-1", {"v": 2})
        entry2 = store.read("facts", "test-1")
        assert entry2 is not None
        assert entry2.created_at == created  # created_at preserved
        assert entry2.content == {"v": 2}

    def test_delete(self, store: GitMemoryStore) -> None:
        store.write("facts", "test-1", {"x": 1})
        assert store.delete("facts", "test-1") is True
        assert store.read("facts", "test-1") is None

    def test_delete_nonexistent(self, store: GitMemoryStore) -> None:
        assert store.delete("facts", "nonexistent") is False

    def test_list_entries_all(self, store: GitMemoryStore) -> None:
        store.write("facts", "a", {"x": 1})
        store.write("facts", "b", {"x": 2})
        store.write("preferences", "c", {"x": 3})
        entries = store.list_entries()
        assert "a" in entries
        assert "b" in entries
        assert "c" in entries

    def test_list_entries_by_category(self, store: GitMemoryStore) -> None:
        store.write("facts", "a", {"x": 1})
        store.write("preferences", "b", {"x": 2})
        facts = store.list_entries("facts")
        assert "a" in facts
        assert "b" not in facts

    def test_list_entries_empty(self, store: GitMemoryStore) -> None:
        assert store.list_entries() == []

    def test_commit_with_changes(self, store: GitMemoryStore) -> None:
        store.write("facts", "test-1", {"x": 1})
        committed = store.commit("Added test-1")
        assert committed is True

    def test_commit_no_changes(self, store: GitMemoryStore) -> None:
        store.commit("Initial commit")
        committed = store.commit("Empty commit")
        assert committed is False

    def test_log(self, store: GitMemoryStore) -> None:
        store.write("facts", "a", {"x": 1})
        store.commit("Commit 1")
        store.write("facts", "b", {"x": 2})
        store.commit("Commit 2")
        log = store.log()
        assert len(log) >= 2
        assert "Commit 2" in log[0]["message"]

    def test_log_empty(self, store: GitMemoryStore) -> None:
        log = store.log()
        assert log == []

    def test_diff(self, store: GitMemoryStore) -> None:
        store.write("facts", "a", {"x": 1})
        store.commit("Commit 1")
        store.write("facts", "b", {"x": 2})
        store.commit("Commit 2")
        diff = store.diff()
        assert isinstance(diff, str)

    def test_create_and_switch_branch(self, store: GitMemoryStore) -> None:
        store.write("facts", "a", {"x": 1})
        store.commit("Initial")
        assert store.create_branch("persona-arch") is True
        assert "persona-arch" in store.list_branches()
        store.write("facts", "b", {"x": 2})
        store.commit("Branch commit")
        assert store.switch_branch("main") is True or store.switch_branch("master") is True

    def test_list_branches(self, store: GitMemoryStore) -> None:
        store.write("facts", "a", {"x": 1})
        store.commit("Initial")
        branches = store.list_branches()
        assert len(branches) >= 1

    def test_status(self, store: GitMemoryStore) -> None:
        store.write("facts", "a", {"x": 1})
        status = store.status()
        assert "branch" in status
        assert "dirty" in status
        assert "total_entries" in status
        assert status["total_entries"] == 1

    def test_status_clean(self, store: GitMemoryStore) -> None:
        store.write("facts", "a", {"x": 1})
        store.commit("Initial")
        status = store.status()
        assert status["dirty"] is False

    def test_status_dirty(self, store: GitMemoryStore) -> None:
        store.write("facts", "a", {"x": 1})
        store.commit("Initial")
        store.write("facts", "b", {"x": 2})  # uncommitted
        status = store.status()
        assert status["dirty"] is True


class TestGitErrorHandling:
    """Tests for git command error paths."""

    def test_git_raises_on_failed_check(self, store: GitMemoryStore) -> None:
        """Line 92: _git raises RuntimeError when check=True and command fails."""
        with pytest.raises(RuntimeError, match="git.*failed"):
            store._git("checkout", "nonexistent-branch-xyz")

    def test_git_check_false_no_raise(self, store: GitMemoryStore) -> None:
        """check=False should not raise even on failure."""
        result = store._git("checkout", "nonexistent-branch-xyz", check=False)
        assert result.returncode != 0


class TestLogEmptyLines:
    """Tests for log parsing edge cases."""

    def test_log_skips_empty_lines(self, store: GitMemoryStore) -> None:
        """Line 179: empty lines in log output are skipped."""
        store.write("facts", "a", {"x": 1})
        store.commit("Commit 1")
        # Mock _git to return output with embedded empty lines
        fake_result = subprocess.CompletedProcess(
            args=["git", "log"],
            returncode=0,
            stdout="abc123|Agent|2026-01-01|Commit 1\n\n\ndef456|Agent|2026-01-02|Commit 2",
            stderr="",
        )
        with patch.object(store, "_git", return_value=fake_result):
            log = store.log()
        assert len(log) == 2
        assert log[0]["hash"] == "abc123"
        assert log[1]["hash"] == "def456"


class TestCheckout:
    """Tests for checkout (time-travel)."""

    def test_checkout_valid_ref(self, store: GitMemoryStore) -> None:
        """Lines 197-198: checkout a valid commit ref returns True."""
        store.write("facts", "a", {"x": 1})
        store.commit("Commit 1")
        store.write("facts", "b", {"x": 2})
        store.commit("Commit 2")
        log = store.log()
        first_commit_hash = log[-1]["hash"]  # oldest commit
        assert store.checkout(first_commit_hash) is True

    def test_checkout_invalid_ref_returns_false(self, store: GitMemoryStore) -> None:
        """Lines 197-198: checkout an invalid ref returns False."""
        assert store.checkout("nonexistent-ref-xyz") is False


class TestPushPullRemote:
    """Tests for push, pull, and add_remote."""

    def test_add_remote_success(self, store: GitMemoryStore) -> None:
        """Lines 231-232: add_remote returns True on success."""
        assert store.add_remote("origin", "https://example.com/repo.git") is True

    def test_push_without_remote_returns_false(self, store: GitMemoryStore) -> None:
        """Lines 221-222: push returns False when no remote is configured."""
        assert store.push() is False

    def test_pull_without_remote_returns_false(self, store: GitMemoryStore) -> None:
        """Lines 226-227: pull returns False when no remote is configured."""
        assert store.pull() is False

    def test_add_remote_duplicate_returns_false(self, store: GitMemoryStore) -> None:
        """Lines 231-232: adding a duplicate remote returns False."""
        store.add_remote("origin", "https://example.com/repo.git")
        assert store.add_remote("origin", "https://example.com/other.git") is False


class TestMainBlock:
    """Tests for the __main__ block (lines 249-252)."""

    def test_main_block_with_arg(self, tmp_path: Path) -> None:
        """Lines 249-252: running the script with a path arg initializes and prints status."""
        repo_path = tmp_path / "main_test_repo"
        script_path = str(Path(__file__).resolve().parents[1] / "git_memory.py")
        old_argv = sys.argv
        sys.argv = ["git_memory.py", str(repo_path)]
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                runpy.run_path(script_path, run_name="__main__")
            status = json.loads(buf.getvalue())
            assert "branch" in status
            assert (repo_path / ".git").exists()
        finally:
            sys.argv = old_argv
