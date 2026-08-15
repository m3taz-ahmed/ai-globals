"""Tests for runtime/worktree_pool.py — parallel agent worktrees."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from runtime.worktree_pool import Worktree, WorktreePool

pytestmark = pytest.mark.slow


@pytest.fixture
def git_project(tmp_path: Path) -> Path:
    """Create a temporary git repository."""
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init"], cwd=str(project), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(project), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(project), capture_output=True)
    (project / "README.md").write_text("# Test Project\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=str(project), capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(project), capture_output=True)
    # Ensure we're on main or master
    result = subprocess.run(["git", "branch", "--show-current"], cwd=str(project), capture_output=True, text=True)
    branch = result.stdout.strip()
    # Force a non-main branch to exercise the rename logic (line 30)
    if branch == "main":
        subprocess.run(["git", "branch", "-m", "master"], cwd=str(project), capture_output=True)
        branch = "master"
    if branch != "main":
        subprocess.run(["git", "branch", "-m", "main"], cwd=str(project), capture_output=True)
    return project


class TestWorktree:
    """Tests for Worktree dataclass."""

    def test_defaults(self) -> None:
        wt = Worktree(id="a1", agent_id="a1", branch="agent/a1", path=Path("/tmp/wt"))
        assert wt.status == "active"
        assert wt.created_at == ""


class TestWorktreePool:
    """Tests for WorktreePool."""

    def test_create_worktree(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        wt = pool.create("agent-1")
        assert wt.agent_id == "agent-1"
        assert wt.path.exists()
        assert wt.branch == "agent/agent-1"
        assert wt.status == "active"

    def test_create_with_custom_branch(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        wt = pool.create("agent-1", branch="feature/custom")
        assert wt.branch == "feature/custom"

    def test_create_duplicate_agent(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        pool.create("agent-1")
        with pytest.raises(ValueError, match="already exists"):
            pool.create("agent-1")

    def test_get_worktree(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        pool.create("agent-1")
        wt = pool.get("agent-1")
        assert wt is not None
        assert wt.agent_id == "agent-1"

    def test_get_nonexistent(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        assert pool.get("nonexistent") is None

    def test_list_active(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        pool.create("agent-1")
        pool.create("agent-2")
        active = pool.list_active()
        assert len(active) == 2

    def test_list_all(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        pool.create("agent-1")
        pool.create("agent-2")
        all_wts = pool.list_all()
        assert len(all_wts) == 2

    def test_merge_success(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        wt = pool.create("agent-1")
        # Make a change in the worktree
        (wt.path / "new_file.txt").write_text("new content\n", encoding="utf-8")
        subprocess.run(["git", "add", "new_file.txt"], cwd=str(wt.path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add new file"], cwd=str(wt.path), capture_output=True)
        # Merge back
        result = pool.merge("agent-1")
        assert result is True
        assert pool.get("agent-1").status == "merged"

    def test_merge_nonexistent(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        assert pool.merge("nonexistent") is False

    def test_merge_already_merged(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        wt = pool.create("agent-1")
        (wt.path / "file.txt").write_text("content\n", encoding="utf-8")
        subprocess.run(["git", "add", "file.txt"], cwd=str(wt.path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add file"], cwd=str(wt.path), capture_output=True)
        pool.merge("agent-1")
        # Second merge should fail (already merged)
        result = pool.merge("agent-1")
        assert result is False

    def test_abandon(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        pool.create("agent-1")
        result = pool.abandon("agent-1")
        assert result is True
        assert pool.get("agent-1").status == "abandoned"

    def test_abandon_nonexistent(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        assert pool.abandon("nonexistent") is False

    def test_cleanup(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        pool.create("agent-1")
        result = pool.cleanup("agent-1")
        assert result is True
        assert pool.get("agent-1") is None

    def test_cleanup_nonexistent(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        assert pool.cleanup("nonexistent") is False

    def test_cleanup_all(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        pool.create("agent-1")
        pool.create("agent-2")
        pool.create("agent-3")
        count = pool.cleanup_all()
        assert count == 3
        assert len(pool.list_all()) == 0

    def test_status(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        pool.create("agent-1")
        pool.create("agent-2")
        status = pool.status()
        assert status["total"] == 2
        assert status["active"] == 2
        assert len(status["worktrees"]) == 2

    def test_status_empty(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        status = pool.status()
        assert status["total"] == 0
        assert status["active"] == 0

    def test_list_git_worktrees(self, git_project: Path) -> None:
        pool = WorktreePool(git_project)
        pool.create("agent-1")
        git_wts = pool.list_git_worktrees()
        # Should have at least 2: main + agent-1
        assert len(git_wts) >= 2

    def test_multiple_agents_parallel(self, git_project: Path) -> None:
        """Test that multiple agents can work in parallel worktrees."""
        pool = WorktreePool(git_project)
        wt1 = pool.create("agent-arch")
        wt2 = pool.create("agent-dev")
        wt3 = pool.create("agent-qa")
        # Each agent makes independent changes
        (wt1.path / "arch.txt").write_text("architecture\n", encoding="utf-8")
        (wt2.path / "dev.txt").write_text("code\n", encoding="utf-8")
        (wt3.path / "qa.txt").write_text("tests\n", encoding="utf-8")
        # Commit in each worktree
        for wt in [wt1, wt2, wt3]:
            subprocess.run(["git", "add", "-A"], cwd=str(wt.path), capture_output=True)
            subprocess.run(["git", "commit", "-m", f"Work by {wt.agent_id}"], cwd=str(wt.path), capture_output=True)
        # All should be active
        assert len(pool.list_active()) == 3
        # Merge all
        for agent_id in ["agent-arch", "agent-dev", "agent-qa"]:
            assert pool.merge(agent_id) is True


class TestEdgeCases:
    """Tests for edge cases and error paths."""

    def test_git_command_failure(self, git_project: Path) -> None:
        """Line 73: _git raises RuntimeError on command failure with check=True."""
        from unittest.mock import MagicMock, patch

        pool = WorktreePool(git_project)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error: something went wrong"
        with patch("runtime.worktree_pool.subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="failed"):
                pool._git("status")

    def test_create_path_already_exists(self, git_project: Path) -> None:
        """Line 93: create raises ValueError when worktree path already exists."""
        pool = WorktreePool(git_project)
        # Pre-create the worktree directory
        wt_path = git_project.parent / ".ai-worktrees" / "agent-1"
        wt_path.mkdir(parents=True, exist_ok=True)
        with pytest.raises(ValueError, match="path already exists"):
            pool.create("agent-1")

    def test_merge_conflict(self, git_project: Path) -> None:
        """Lines 143-146: merge conflict aborts and returns False."""
        pool = WorktreePool(git_project)
        # Create both worktrees from the same base commit
        wt1 = pool.create("agent-1")
        wt2 = pool.create("agent-2")
        # Make conflicting changes to the same file
        (wt1.path / "conflict.txt").write_text("version A\n", encoding="utf-8")
        subprocess.run(["git", "add", "conflict.txt"], cwd=str(wt1.path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "Change A"], cwd=str(wt1.path), capture_output=True)
        (wt2.path / "conflict.txt").write_text("version B\n", encoding="utf-8")
        subprocess.run(["git", "add", "conflict.txt"], cwd=str(wt2.path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "Change B"], cwd=str(wt2.path), capture_output=True)
        # Merge first worktree (succeeds)
        assert pool.merge("agent-1") is True
        # Merge second worktree — conflicts on conflict.txt
        result = pool.merge("agent-2")
        assert result is False

    def test_merge_runtime_error_returns_false(self, git_project: Path) -> None:
        """Lines 145-146: merge catches RuntimeError and returns False."""
        from unittest.mock import patch

        pool = WorktreePool(git_project)
        pool.create("agent-1")
        with patch.object(WorktreePool, "_git", side_effect=RuntimeError("git error")):
            result = pool.merge("agent-1")
        assert result is False

    def test_cleanup_git_error(self, git_project: Path) -> None:
        """Lines 173-174: cleanup catches RuntimeError from git commands."""
        from unittest.mock import patch

        pool = WorktreePool(git_project)
        pool.create("agent-1")
        # Mock _git to raise RuntimeError during cleanup
        with patch.object(WorktreePool, "_git", side_effect=RuntimeError("git error")):
            result = pool.cleanup("agent-1")
        assert result is True  # cleanup still succeeds (error is caught)

    def test_main_block(self, git_project: Path) -> None:
        """Lines 231-234: __main__ block."""
        import runpy
        import sys

        script = str(Path(__file__).resolve().parent.parent / "worktree_pool.py")
        old_argv = sys.argv
        sys.argv = [script, str(git_project)]
        try:
            runpy.run_path(script, run_name="__main__")
        finally:
            sys.argv = old_argv
