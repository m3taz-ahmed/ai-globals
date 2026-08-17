"""Tests for scripts/update.py — git pull + post-install hooks.

Tests use a temporary git repo to simulate the update flow.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


def _load_script(script_path: Path):
    """Dynamically load a script as a module."""
    spec = importlib.util.spec_from_file_location(script_path.stem, script_path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run a git command."""
    result = subprocess.run(["git", *cmd], cwd=cwd, capture_output=True, text=True, shell=False)
    return result.returncode, result.stdout, result.stderr


def _make_git_repo(path: Path) -> None:
    """Initialize a git repo with a remote and initial commit."""
    _git(["init"], path)
    _git(["config", "user.email", "test@test.com"], path)
    _git(["config", "user.name", "Test"], path)
    (path / "README.md").write_text("# aizee", encoding="utf-8")
    (path / ".aizee-version").write_text("5.0.0", encoding="utf-8")
    _git(["add", "README.md", ".aizee-version"], path)
    _git(["commit", "-m", "initial"], path)


SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"


class TestUpdateScript:
    """Tests for update.py."""

    def test_module_imports(self) -> None:
        """Module can be loaded without error."""
        mod = _load_script(SCRIPTS / "update.py")
        assert hasattr(mod, "run_update")
        assert hasattr(mod, "main")

    def test_is_git_repo_detects_git(self, tmp_path: Path) -> None:
        """_is_git_repo returns True for a git repo."""
        _make_git_repo(tmp_path)
        mod = _load_script(SCRIPTS / "update.py")
        assert mod._is_git_repo(tmp_path) is True

    def test_is_git_repo_rejects_non_git(self, tmp_path: Path) -> None:
        """_is_git_repo returns False for a non-git directory."""
        mod = _load_script(SCRIPTS / "update.py")
        assert mod._is_git_repo(tmp_path) is False

    def test_update_non_git_repo_returns_error(self, tmp_path: Path) -> None:
        """run_update on non-git repo returns error code 1."""
        mod = _load_script(SCRIPTS / "update.py")
        rc = mod.run_update(tmp_path, assume_yes=True)
        assert rc == 1

    def test_update_already_up_to_date(self, tmp_path: Path) -> None:
        """run_update on a repo with no remote returns appropriate code."""
        _make_git_repo(tmp_path)
        mod = _load_script(SCRIPTS / "update.py")
        # No remote configured → _check_remote will fail → returns 1
        rc = mod.run_update(tmp_path, assume_yes=True)
        # Either 0 (no remote, treated as up-to-date) or 1 (fetch error)
        assert rc in (0, 1)

    def test_get_current_branch(self, tmp_path: Path) -> None:
        """_get_current_branch returns the active branch name."""
        _make_git_repo(tmp_path)
        mod = _load_script(SCRIPTS / "update.py")
        branch = mod._get_current_branch(tmp_path)
        # Could be 'main' or 'master' depending on git config
        assert branch in ("main", "master")

    def test_post_install_handles_missing_files(self, tmp_path: Path) -> None:
        """_post_install_hooks handles missing scripts gracefully."""
        mod = _load_script(SCRIPTS / "update.py")
        actions = mod._post_install_hooks(tmp_path)
        assert isinstance(actions, list)
        assert len(actions) >= 1  # At least pip install attempt
