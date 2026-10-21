"""Tests for scripts/update.py --dry-run --json plan contract.

The plan must be read-only (no pull, no stash, no post-hooks) and report
exactly what an update would do: commits behind, files changed, local
changes to stash, stale paths removed, and post-install steps.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

_UPDATE = Path(__file__).resolve().parent.parent.parent / "scripts" / "update.py"


def _load_update():
    spec = importlib.util.spec_from_file_location("update_module", _UPDATE)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def update():
    return _load_update()


def _git_root(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    (tmp_path / "scripts").mkdir()
    return tmp_path


def _fake_run(responses: dict[tuple[str, ...], tuple[int, str, str]]):
    """Return a _run replacement keyed by command tuple prefix."""
    def runner(cmd, cwd=None, check=True):
        key = tuple(cmd)
        for prefix, result in responses.items():
            if key[: len(prefix)] == prefix:
                return result
        return (0, "", "")
    return runner


class TestUpdatePlan:
    def test_plan_reports_behind_and_files(self, update, tmp_path: Path):
        root = _git_root(tmp_path)
        responses = {
            ("git", "rev-parse", "--abbrev-ref"): (0, "main\n", ""),
            ("git", "remote", "get-url"): (0, "https://example/repo.git\n", ""),
            ("git", "fetch"): (0, "", ""),
            ("git", "rev-parse", "HEAD"): (0, "aaa\n", ""),
            ("git", "rev-parse", "origin/main"): (0, "bbb\n", ""),
            ("git", "rev-list", "--count", "HEAD..origin/main"): (0, "3\n", ""),
            ("git", "rev-list", "--count", "origin/main..HEAD"): (0, "0\n", ""),
            ("git", "diff", "--name-only"): (0, "runtime/x.py\nREADME.md\n", ""),
            ("git", "status", "--porcelain"): (0, "", ""),
        }
        with patch.object(update, "_run", _fake_run(responses)):
            plan = update._update_plan(root, "main", update._check_remote(root, "main"))
        assert plan["action"] == "update"
        assert plan["behind"] is True
        assert plan["commits_behind"] == 3
        assert plan["files_changed"] == ["runtime/x.py", "README.md"]
        assert plan["would_stash_local_changes"] is False
        assert "post-update verification" in plan["post_install_steps"]

    def test_plan_flags_local_changes_for_stash(self, update, tmp_path: Path):
        root = _git_root(tmp_path)
        responses = {
            ("git", "status", "--porcelain"): (0, " M runtime/x.py\n", ""),
        }
        with patch.object(update, "_run", _fake_run(responses)):
            assert update._has_local_changes(root) is True
            assert update._update_plan(
                root, "main",
                {"remote_url": "", "behind": True, "commits_behind": 1,
                 "ahead": False, "error": None},
            )["would_stash_local_changes"] is True

    def test_plan_lists_existing_stale_targets(self, update, tmp_path: Path):
        root = _git_root(tmp_path)
        (root / "scripts" / "stale_files.txt").write_text(
            "runtime/old.py\n# comment\nruntime/kept.py\n", encoding="utf-8"
        )
        (root / "runtime").mkdir()
        (root / "runtime" / "old.py").write_text("", encoding="utf-8")
        assert update._stale_targets(root) == ["runtime/old.py"]

    def test_dry_run_json_prints_plan_and_pulls_nothing(self, update, tmp_path: Path, capsys):
        root = _git_root(tmp_path)
        calls: list[list[str]] = []
        responses = {
            ("git", "rev-parse", "--abbrev-ref"): (0, "main\n", ""),
            ("git", "remote", "get-url"): (0, "https://example/repo.git\n", ""),
            ("git", "rev-parse", "HEAD"): (0, "aaa\n", ""),
            ("git", "rev-parse", "origin/main"): (0, "bbb\n", ""),
            ("git", "rev-list", "--count", "HEAD..origin/main"): (0, "1\n", ""),
            ("git", "rev-list", "--count", "origin/main..HEAD"): (0, "0\n", ""),
        }

        def spy_run(cmd, cwd=None, check=True):
            calls.append(list(cmd))
            for prefix, result in responses.items():
                if tuple(cmd)[: len(prefix)] == prefix:
                    return result
            return (0, "", "")

        with patch.object(update, "_run", spy_run):
            rc = update.run_update(root, assume_yes=True, dry_run=True, as_json=True)

        assert rc == 0
        out = capsys.readouterr().out
        plan = json.loads(out[out.index("{"):])
        assert plan["behind"] is True and plan["commits_behind"] == 1
        # Read-only contract: fetch + rev-parse/diff only — never pull/stash.
        forbidden = [c for c in calls if c[1] in {"pull", "stash", "rebase"}]
        assert forbidden == []
