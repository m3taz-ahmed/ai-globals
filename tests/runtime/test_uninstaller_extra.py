"""Gap-coverage tests for runtime/uninstaller.py — UI helpers + flow paths."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runtime import uninstaller
from runtime.uninstaller import (
    CategoryAction,
    UninstallCategory,
    _build_categories,
    _format_size,
    _toggle_category,
    create_backup,
    delete_category,
    interactive_uninstall,
    is_aizee_root,
    pip_uninstall,
    remove_cli_shim,
    remove_mcp_config_entries,
)


def _fake_root(tmp_path: Path) -> Path:
    (tmp_path / ".aizee-version").write_text("5.14.1")
    (tmp_path / "runtime").mkdir()
    (tmp_path / "runtime" / "kernel.py").write_text("# k")
    (tmp_path / "config.py").write_text("# c")
    return tmp_path


class TestFormatSize:
    @pytest.mark.parametrize("b,expected", [
        (512, "512B"), (2048, "2.0KB"), (5 * 1024 * 1024, "5.0MB")])
    def test_sizes(self, b, expected):
        assert _format_size(b) == expected


class TestToggle:
    def test_valid_toggle(self):
        cats = [UninstallCategory("k", "l", [], is_learned=True)]
        assert cats[0].action is CategoryAction.KEEP
        assert _toggle_category(cats, 1) is True
        assert cats[0].action is CategoryAction.DELETE
        assert _toggle_category(cats, 1) is True
        assert cats[0].action is CategoryAction.KEEP

    def test_out_of_range(self):
        cats = [UninstallCategory("k", "l", [])]
        assert _toggle_category(cats, 0) is False
        assert _toggle_category(cats, 99) is False


class TestRemovePath:
    def test_file(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("x")
        assert uninstaller._remove_path(f) is True
        assert not f.exists()

    def test_dir(self, tmp_path):
        d = tmp_path / "d"
        d.mkdir()
        (d / "f").write_text("x")
        assert uninstaller._remove_path(d) is True

    def test_error_returns_false(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("x")
        with patch.object(Path, "unlink", side_effect=OSError("denied")):
            assert uninstaller._remove_path(f) is False


class TestDeleteCategory:
    def test_removes_existing(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("x")
        cat = UninstallCategory("k", "l", [f, tmp_path / "missing"])
        removed = delete_category(cat)
        assert removed == [str(f)]


class TestPipUninstall:
    def test_success(self):
        with patch("subprocess.run",
                   return_value=MagicMock(returncode=0)) as run:
            assert pip_uninstall() is True
            assert run.call_args[0][0][-2:] == ["-y", "aizee"]

    def test_failure(self):
        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            assert pip_uninstall() is False

    def test_oserror(self):
        with patch("subprocess.run", side_effect=OSError):
            assert pip_uninstall() is False


class TestRemoveCliShim:
    # NOTE: os.name cannot be patched (pathlib instantiates PosixPath on
    # Windows and raises). On this host os.name is "nt" — the nt branch is
    # exercised; the posix branch mirrors it structurally.
    def test_removes_appdata_candidate(self, tmp_path, monkeypatch):
        shim = tmp_path / "Python" / "Scripts" / "aizee.exe"
        shim.parent.mkdir(parents=True)
        shim.write_text("x")
        monkeypatch.setenv("APPDATA", str(tmp_path))
        with patch("subprocess.run",
                   return_value=MagicMock(returncode=1, stdout="")):
            assert remove_cli_shim() is True
            assert not shim.exists()

    def test_removes_user_base_candidate(self, tmp_path, monkeypatch):
        monkeypatch.setenv("APPDATA", str(tmp_path / "noappdata"))
        shim = tmp_path / "Scripts" / "aizee.cmd"
        shim.parent.mkdir(parents=True)
        shim.write_text("x")
        with patch("subprocess.run",
                   return_value=MagicMock(returncode=0, stdout=str(tmp_path))):
            assert remove_cli_shim() is True
            assert not shim.exists()

    def test_none_found(self, tmp_path, monkeypatch):
        monkeypatch.setenv("APPDATA", str(tmp_path))
        with patch("subprocess.run",
                   return_value=MagicMock(returncode=0, stdout=str(tmp_path))):
            assert remove_cli_shim() is False

    def test_subprocess_error(self):
        with patch("subprocess.run", side_effect=OSError):
            remove_cli_shim()  # no raise


class TestMcpConfigEntries:
    def test_removes_aizee_key(self, tmp_path):
        cfg = tmp_path / ".devin" / "mcp_config.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(json.dumps(
            {"mcpServers": {"aizee": {"x": 1}, "other": {}}}))
        removed = remove_mcp_config_entries(tmp_path)
        assert removed == [str(cfg)]
        data = json.loads(cfg.read_text())
        assert "aizee" not in data["mcpServers"]
        assert "other" in data["mcpServers"]

    def test_no_aizee_key(self, tmp_path):
        cfg = tmp_path / ".devin" / "mcp_config.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(json.dumps({"mcpServers": {"other": {}}}))
        assert remove_mcp_config_entries(tmp_path) == []

    def test_corrupt_json(self, tmp_path):
        cfg = tmp_path / ".devin" / "mcp_config.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("{bad json")
        assert remove_mcp_config_entries(tmp_path) == []

    def test_missing_files(self, tmp_path):
        assert remove_mcp_config_entries(tmp_path) == []


class TestCreateBackup:
    def test_no_keep_categories(self, tmp_path):
        cats = [UninstallCategory("k", "l", [tmp_path / "x"])]
        assert create_backup(tmp_path, cats) is None

    def test_backs_up_file_and_dir(self, tmp_path):
        keep_file = tmp_path / ".env"
        keep_file.write_text("SECRET=1")
        keep_dir = tmp_path / "memory"
        keep_dir.mkdir()
        (keep_dir / "m.db").write_text("db")
        cats = [
            UninstallCategory("env", "env", [keep_file], is_learned=True),
            UninstallCategory("memory", "mem", [keep_dir], is_learned=True),
        ]
        out = tmp_path / "bk.zip"
        result = create_backup(tmp_path, cats, backup_path=out)
        assert result == out
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        assert "env/.env" in names
        assert "memory/m.db" in names


class TestIsAizeeRoot:
    def test_marker_file(self, tmp_path):
        (tmp_path / ".aizee-version").write_text("x")
        assert is_aizee_root(tmp_path) is True

    def test_config_plus_kernel(self, tmp_path):
        (tmp_path / "config.py").write_text("x")
        (tmp_path / "runtime").mkdir()
        (tmp_path / "runtime" / "kernel.py").write_text("x")
        assert is_aizee_root(tmp_path) is True

    def test_not_aizee(self, tmp_path):
        assert is_aizee_root(tmp_path) is False


class TestInteractiveUninstall:
    def test_refuses_non_aizee_root(self, tmp_path, capsys):
        # content exists (runtime dir) but no markers
        (tmp_path / "runtime").mkdir()
        (tmp_path / "runtime" / "x.py").write_text("x")
        rc = interactive_uninstall(tmp_path, assume_yes=True)
        assert rc == 1

    def test_assume_yes_flow(self, tmp_path):
        _fake_root(tmp_path)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "d.md").write_text("x")
        with patch("runtime.uninstaller.pip_uninstall", return_value=True), \
             patch("runtime.uninstaller.remove_cli_shim", return_value=True):
            rc = interactive_uninstall(tmp_path, assume_yes=True)
        assert rc == 0
        assert not (tmp_path / "docs").exists()

    def test_interactive_quit(self, tmp_path):
        _fake_root(tmp_path)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "d.md").write_text("x")
        with patch("builtins.input", side_effect=["q"]):
            assert interactive_uninstall(tmp_path) == 1
        assert (tmp_path / "docs").exists()

    def test_interactive_eof(self, tmp_path):
        _fake_root(tmp_path)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "d.md").write_text("x")
        with patch("builtins.input", side_effect=EOFError):
            assert interactive_uninstall(tmp_path) == 1

    def test_interactive_toggle_and_confirm(self, tmp_path):
        _fake_root(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "d.md").write_text("x")
        # find index of os_files category to toggle to KEEP
        cats = _build_categories(tmp_path)
        idx = next(i for i, c in enumerate(cats, 1) if c.key == "os_files")
        inputs = iter([str(idx), "bad", "99", "a", "b", "c", "y"])
        with patch("builtins.input", side_effect=inputs), \
             patch("runtime.uninstaller.pip_uninstall", return_value=False), \
             patch("runtime.uninstaller.remove_cli_shim", return_value=False):
            rc = interactive_uninstall(tmp_path)
        assert rc == 0

    def test_interactive_backup_yes(self, tmp_path):
        _fake_root(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "d.md").write_text("x")
        mem = tmp_path / "memory"
        mem.mkdir()
        (mem / "m.db").write_text("db")
        inputs = iter(["c", "y", "y"])  # confirm menu, backup yes, confirm exec
        with patch("builtins.input", side_effect=inputs), \
             patch("runtime.uninstaller.pip_uninstall", return_value=False), \
             patch("runtime.uninstaller.remove_cli_shim", return_value=False), \
             patch("runtime.uninstaller.Path.home", return_value=tmp_path):
            rc = interactive_uninstall(tmp_path)
        assert rc == 0
        backups = list(tmp_path.glob("aizee-backup-*.zip"))
        assert len(backups) == 1

    def test_interactive_backup_custom_path(self, tmp_path):
        _fake_root(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "d.md").write_text("x")
        mem = tmp_path / "memory"
        mem.mkdir()
        (mem / "m.db").write_text("db")
        custom = tmp_path / "my-backup.zip"
        inputs = iter(["c", "p", str(custom), "y"])
        with patch("builtins.input", side_effect=inputs), \
             patch("runtime.uninstaller.pip_uninstall", return_value=False), \
             patch("runtime.uninstaller.remove_cli_shim", return_value=False):
            rc = interactive_uninstall(tmp_path)
        assert rc == 0
        assert custom.exists()

    def test_interactive_backup_eof(self, tmp_path):
        _fake_root(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "d.md").write_text("x")
        mem = tmp_path / "memory"
        mem.mkdir()
        (mem / "m.db").write_text("db")
        inputs = iter(["c", EOFError(), "y"])
        with patch("builtins.input", side_effect=inputs), \
             patch("runtime.uninstaller.pip_uninstall", return_value=False), \
             patch("runtime.uninstaller.remove_cli_shim", return_value=False):
            rc = interactive_uninstall(tmp_path)
        assert rc == 0

    def test_execute_confirm_declined(self, tmp_path):
        _fake_root(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "d.md").write_text("x")
        cats = _build_categories(tmp_path)
        with patch("builtins.input", side_effect=["n"]):
            rc = uninstaller._execute_uninstall(tmp_path, cats, None, False)
        assert rc == 1
        assert docs.exists()

    def test_execute_confirm_eof(self, tmp_path):
        _fake_root(tmp_path)
        cats = _build_categories(tmp_path)
        with patch("builtins.input", side_effect=EOFError):
            assert uninstaller._execute_uninstall(tmp_path, cats, None, False) == 1

    def test_execute_with_mcp_and_symlinks(self, tmp_path):
        _fake_root(tmp_path)
        cfg = tmp_path / ".devin" / "mcp_config.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(json.dumps({"mcpServers": {"aizee": {}}}))
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "d.md").write_text("x")
        cats = _build_categories(tmp_path)
        with patch("runtime.uninstaller.pip_uninstall", return_value=True), \
             patch("runtime.uninstaller.remove_cli_shim", return_value=True):
            rc = uninstaller._execute_uninstall(tmp_path, cats, None, True)
        assert rc == 0
        assert "aizee" not in json.loads(cfg.read_text())["mcpServers"]
