"""Tests for runtime/uninstaller_gui.py — GUI uninstaller logic.

These tests cover the non-UI logic (category loading, toggle, backup path)
without launching the actual tkinter mainloop, which requires a display.
"""

from __future__ import annotations

import importlib
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

import pytest


def _make_tmp_root(tmp_path: Path) -> Path:
    """Create a minimal aiZee root for testing."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='aizee'\n", encoding="utf-8")
    (tmp_path / "aizee_cli.py").write_text("# cli", encoding="utf-8")
    (tmp_path / "config.py").write_text("# config", encoding="utf-8")
    (tmp_path / ".aizee-version").write_text("5.0.0", encoding="utf-8")
    (tmp_path / "memory").mkdir(exist_ok=True)
    (tmp_path / "memory" / "store.db").write_bytes(b"fake")
    (tmp_path / "state").mkdir(exist_ok=True)
    (tmp_path / "brain").mkdir(exist_ok=True)
    (tmp_path / "rules").mkdir(exist_ok=True)
    (tmp_path / "rules" / "core.md").write_text("# Core", encoding="utf-8")
    return tmp_path


class TestUninstallerGUI:
    """Tests for the GUI uninstaller module."""

    def test_module_imports(self) -> None:
        """Module can be imported without error."""
        mod = importlib.import_module("runtime.uninstaller_gui")
        assert hasattr(mod, "UninstallerGUI")
        assert hasattr(mod, "main")

    def test_gui_initializes_with_categories(self, tmp_path: Path) -> None:
        """GUI loads categories from the root path."""
        root = _make_tmp_root(tmp_path)
        # Skip if no display (headless CI)
        try:
            tk.Tk().destroy()
        except tk.TclError:
            pytest.skip("No display available for tkinter")

        from runtime.uninstaller_gui import UninstallerGUI

        gui = UninstallerGUI(root)
        try:
            assert len(gui.categories) > 0
            # Should have at least package, memory, state categories
            keys = {c.key for c in gui.categories}
            assert "package" in keys
            assert "memory" in keys
            assert "state" in keys
        finally:
            gui.win.destroy()

    def test_toggle_row_flips_action(self, tmp_path: Path) -> None:
        """Toggling a row flips keep <-> delete."""
        root = _make_tmp_root(tmp_path)
        try:
            tk.Tk().destroy()
        except tk.TclError:
            pytest.skip("No display available for tkinter")

        from runtime.uninstaller import CategoryAction
        from runtime.uninstaller_gui import UninstallerGUI

        gui = UninstallerGUI(root)
        try:
            # Find the package category (default DELETE)
            pkg_cat = next(c for c in gui.categories if c.key == "package")
            assert pkg_cat.action == CategoryAction.DELETE

            # Toggle it
            pkg_idx = gui.categories.index(pkg_cat)
            item_id = gui.tree.get_children()[pkg_idx]
            gui.tree.selection_set(item_id)
            gui._on_toggle_row()

            assert pkg_cat.action == CategoryAction.KEEP

            # Toggle back
            gui._on_toggle_row()
            assert pkg_cat.action == CategoryAction.DELETE
        finally:
            gui.win.destroy()

    def test_keep_all_learned_sets_learned_to_keep(self, tmp_path: Path) -> None:
        """'Keep All Learned' button sets all learned categories to KEEP."""
        root = _make_tmp_root(tmp_path)
        try:
            tk.Tk().destroy()
        except tk.TclError:
            pytest.skip("No display available for tkinter")

        from runtime.uninstaller import CategoryAction
        from runtime.uninstaller_gui import UninstallerGUI

        gui = UninstallerGUI(root)
        try:
            # Force all to DELETE first
            for c in gui.categories:
                c.action = CategoryAction.DELETE

            gui._keep_all_learned()

            for c in gui.categories:
                if c.is_learned:
                    assert c.action == CategoryAction.KEEP
        finally:
            gui.win.destroy()

    def test_delete_all_sets_all_to_delete(self, tmp_path: Path) -> None:
        """'Delete All' button sets ALL categories to DELETE."""
        root = _make_tmp_root(tmp_path)
        try:
            tk.Tk().destroy()
        except tk.TclError:
            pytest.skip("No display available for tkinter")

        from runtime.uninstaller import CategoryAction
        from runtime.uninstaller_gui import UninstallerGUI

        gui = UninstallerGUI(root)
        try:
            gui._delete_all()
            for c in gui.categories:
                assert c.action == CategoryAction.DELETE
        finally:
            gui.win.destroy()

    def test_backup_toggle_enables_disables_entry(self, tmp_path: Path) -> None:
        """Backup checkbox toggles the path entry state."""
        root = _make_tmp_root(tmp_path)
        try:
            tk.Tk().destroy()
        except tk.TclError:
            pytest.skip("No display available for tkinter")

        from runtime.uninstaller_gui import UninstallerGUI

        gui = UninstallerGUI(root)
        try:
            # Uncheck backup
            gui.backup_var.set(False)
            gui._on_backup_toggle()
            assert str(gui.backup_entry.cget("state")) == "disabled"

            # Check backup
            gui.backup_var.set(True)
            gui._on_backup_toggle()
            assert str(gui.backup_entry.cget("state")) == "normal"
        finally:
            gui.win.destroy()

    def test_main_returns_error_on_no_display(self, tmp_path: Path) -> None:
        """main() returns 1 if tkinter is unavailable (headless)."""
        # This test only runs meaningfully on headless systems;
        # on systems with display, the GUI would actually open.
        # We mock UninstallerGUI to raise to simulate no display.
        with patch("runtime.uninstaller_gui.UninstallerGUI") as mock_gui:
            mock_gui.side_effect = tk.TclError("no display")
            from runtime.uninstaller_gui import main
            rc = main([str(tmp_path)])
            assert rc == 1
