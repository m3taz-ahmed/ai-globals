#!/usr/bin/env python3
"""Tests for the aiZee uninstaller module."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.uninstaller import (
    CategoryAction,
    UninstallCategory,
    _build_categories,
    _format_size,
    create_backup,
    delete_category,
    interactive_uninstall,
    pip_uninstall,
    remove_mcp_config_entries,
)


@pytest.fixture
def fake_root(tmp_path: Path) -> Path:
    """Create a fake aiZee root with minimal structure."""
    (tmp_path / "pyproject.toml").write_text('name = "aizee"', encoding="utf-8")
    (tmp_path / "aizee_cli.py").write_text("# cli", encoding="utf-8")
    (tmp_path / "config.py").write_text("# config", encoding="utf-8")
    (tmp_path / ".aizee-version").write_text("5.0.0", encoding="utf-8")
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "store.db").write_text("data", encoding="utf-8")
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "budget.json").write_text("{}", encoding="utf-8")
    (tmp_path / "brain").mkdir()
    (tmp_path / ".env").write_text("KEY=secret", encoding="utf-8")
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "test.md").write_text("# rule", encoding="utf-8")
    (tmp_path / "runtime").mkdir()
    (tmp_path / "runtime" / "kernel.py").write_text("# kernel", encoding="utf-8")
    (tmp_path / ".devin").mkdir(parents=True)
    (tmp_path / ".devin" / "mcp_config.json").write_text(
        json.dumps({"mcpServers": {"aizee": {"command": "python"}}}), encoding="utf-8"
    )
    return tmp_path


class TestUninstallCategory:
    """Tests for UninstallCategory."""

    def test_default_action_for_learned_is_keep(self, tmp_path: Path) -> None:
        cat = UninstallCategory("memory", "Memory", [tmp_path / "memory"], is_learned=True)
        assert cat.action == CategoryAction.KEEP

    def test_default_action_for_os_is_delete(self, tmp_path: Path) -> None:
        cat = UninstallCategory("rules", "Rules", [tmp_path / "rules"], is_learned=False)
        assert cat.action == CategoryAction.DELETE

    def test_exists_returns_true_when_path_exists(self, tmp_path: Path) -> None:
        (tmp_path / "test.txt").write_text("x", encoding="utf-8")
        cat = UninstallCategory("test", "Test", [tmp_path / "test.txt"])
        assert cat.exists() is True

    def test_exists_returns_false_when_path_missing(self, tmp_path: Path) -> None:
        cat = UninstallCategory("test", "Test", [tmp_path / "nonexistent"])
        assert cat.exists() is False

    def test_total_size_bytes_calculates_file_size(self, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("hello world", encoding="utf-8")
        cat = UninstallCategory("test", "Test", [tmp_path / "f.txt"])
        assert cat.total_size_bytes() == 11

    def test_total_size_bytes_calculates_directory_size(self, tmp_path: Path) -> None:
        d = tmp_path / "dir"
        d.mkdir()
        (d / "a.txt").write_text("aaaa", encoding="utf-8")
        (d / "b.txt").write_text("bb", encoding="utf-8")
        cat = UninstallCategory("test", "Test", [d])
        assert cat.total_size_bytes() == 6


class TestBuildCategories:
    """Tests for _build_categories."""

    def test_returns_all_expected_categories(self, tmp_path: Path) -> None:
        cats = _build_categories(tmp_path)
        keys = [c.key for c in cats]
        assert "package" in keys
        assert "memory" in keys
        assert "state" in keys
        assert "brain" in keys
        assert "env" in keys
        assert "os_files" in keys
        assert "mcp_configs" in keys

    def test_learned_categories_are_marked(self, tmp_path: Path) -> None:
        cats = _build_categories(tmp_path)
        learned_keys = {c.key for c in cats if c.is_learned}
        assert "memory" in learned_keys
        assert "state" in learned_keys
        assert "brain" in learned_keys
        assert "env" in learned_keys

    def test_os_categories_are_not_learned(self, tmp_path: Path) -> None:
        cats = _build_categories(tmp_path)
        os_keys = {c.key for c in cats if not c.is_learned}
        assert "package" in os_keys
        assert "os_files" in os_keys


class TestCreateBackup:
    """Tests for create_backup."""

    def test_backup_creates_zip_with_kept_files(self, fake_root: Path, tmp_path: Path) -> None:
        cats = _build_categories(fake_root)
        keep_cats = [c for c in cats if c.is_learned]
        for c in keep_cats:
            c.action = CategoryAction.KEEP

        backup_path = tmp_path / "backup.zip"
        result = create_backup(fake_root, cats, backup_path)

        assert result is not None
        assert result.exists()
        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
            assert any("memory" in n for n in names)
            assert any(".env" in n for n in names)

    def test_backup_returns_none_when_nothing_to_keep(self, fake_root: Path, tmp_path: Path) -> None:
        cats = _build_categories(fake_root)
        for c in cats:
            c.action = CategoryAction.DELETE

        result = create_backup(fake_root, cats, tmp_path / "backup.zip")
        assert result is None


class TestDeleteCategory:
    """Tests for delete_category."""

    def test_deletes_existing_files(self, tmp_path: Path) -> None:
        f1 = tmp_path / "file1.txt"
        f2 = tmp_path / "file2.txt"
        f1.write_text("a", encoding="utf-8")
        f2.write_text("b", encoding="utf-8")
        cat = UninstallCategory("test", "Test", [f1, f2])

        removed = delete_category(cat)

        assert len(removed) == 2
        assert not f1.exists()
        assert not f2.exists()

    def test_deletes_directories(self, tmp_path: Path) -> None:
        d = tmp_path / "dir"
        d.mkdir()
        (d / "inner.txt").write_text("x", encoding="utf-8")
        cat = UninstallCategory("test", "Test", [d])

        removed = delete_category(cat)

        assert len(removed) == 1
        assert not d.exists()

    def test_does_not_fail_on_missing_paths(self, tmp_path: Path) -> None:
        cat = UninstallCategory("test", "Test", [tmp_path / "nonexistent"])
        removed = delete_category(cat)
        assert len(removed) == 0


class TestRemoveMcpConfigEntries:
    """Tests for remove_mcp_config_entries."""

    def test_removes_aizee_entry_from_configs(self, fake_root: Path) -> None:
        removed = remove_mcp_config_entries(fake_root)

        cfg = json.loads((fake_root / ".devin" / "mcp_config.json").read_text())
        assert "aizee" not in cfg.get("mcpServers", {})
        assert len(removed) >= 1

    def test_does_not_remove_other_servers(self, fake_root: Path) -> None:
        cfg_path = fake_root / ".devin" / "mcp_config.json"
        cfg_path.write_text(
            json.dumps({"mcpServers": {"aizee": {}, "context7": {}, "graphify": {}}}),
            encoding="utf-8",
        )

        remove_mcp_config_entries(fake_root)

        cfg = json.loads(cfg_path.read_text())
        servers = cfg.get("mcpServers", {})
        assert "aizee" not in servers
        assert "context7" in servers
        assert "graphify" in servers


class TestPipUninstall:
    """Tests for pip_uninstall."""

    def test_pip_uninstall_calls_subprocess(self) -> None:
        with patch("runtime.uninstaller.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = pip_uninstall()
            assert result is True
            mock_run.assert_called_once()

    def test_pip_uninstall_returns_false_on_error(self) -> None:
        with patch("runtime.uninstaller.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("fail")
            result = pip_uninstall()
            assert result is False


class TestFormatSize:
    """Tests for _format_size."""

    def test_bytes(self) -> None:
        assert _format_size(500) == "500B"

    def test_kilobytes(self) -> None:
        assert _format_size(2048) == "2.0KB"

    def test_megabytes(self) -> None:
        assert _format_size(1024 * 1024 * 5) == "5.0MB"


class TestInteractiveUninstall:
    """Tests for interactive_uninstall."""

    def test_assume_yes_keeps_learned_and_deletes_os(self, fake_root: Path) -> None:
        with patch("runtime.uninstaller.pip_uninstall", return_value=True), \
             patch("runtime.uninstaller.remove_cli_shim", return_value=True):
            rc = interactive_uninstall(fake_root, assume_yes=True)

        assert rc == 0
        # Learned data should be kept
        assert (fake_root / "memory").exists()
        assert (fake_root / ".env").exists()
        # OS files should be deleted
        assert not (fake_root / "rules").exists()
        assert not (fake_root / "runtime").exists()

    def test_returns_zero_when_nothing_to_uninstall(self, tmp_path: Path) -> None:
        # Empty directory with no aiZee files
        rc = interactive_uninstall(tmp_path, assume_yes=True)
        assert rc == 0
