"""Tests for memory/git_memory.py — git-backed memory store."""

from __future__ import annotations

import json
from pathlib import Path

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
