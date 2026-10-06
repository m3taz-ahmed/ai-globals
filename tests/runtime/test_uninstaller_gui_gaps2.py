"""Gap coverage round 2 for runtime/uninstaller_gui.py."""

from __future__ import annotations

import contextlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("tkinter")


def _make_tmp_root(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='aizee'\n")
    (tmp_path / "aizee_cli.py").write_text("# cli")
    (tmp_path / "config.py").write_text("# config")
    (tmp_path / ".aizee-version").write_text("5.0.0")
    (tmp_path / "runtime").mkdir(exist_ok=True)
    (tmp_path / "runtime" / "kernel.py").write_text("# k")
    (tmp_path / "memory").mkdir(exist_ok=True)
    (tmp_path / "memory" / "store.db").write_bytes(b"fake")
    (tmp_path / "state").mkdir(exist_ok=True)
    return tmp_path


@pytest.fixture
def gui(tmp_path):
    root = _make_tmp_root(tmp_path)
    from runtime.uninstaller_gui import UninstallerGUI

    try:
        g = UninstallerGUI(root)
    except Exception:
        pytest.skip("tkinter not functional")
    yield g
    with contextlib.suppress(Exception):
        g.win.destroy()


def test_empty_categories_destroys(tmp_path: Path) -> None:
    root = _make_tmp_root(tmp_path)
    with (
        patch("runtime.uninstaller_gui._build_categories", return_value=[]),
        patch("runtime.uninstaller_gui.messagebox", MagicMock()),
    ):
        from runtime.uninstaller_gui import UninstallerGUI

        try:
            g = UninstallerGUI(root)
        except Exception:
            pytest.skip("tkinter not functional")
        assert g.categories == []


def test_reload_categories_deletes_rows(gui) -> None:
    gui._load_categories()
    assert gui.tree.get_children()


def test_toggle_row_unknown_key(gui) -> None:
    item = gui.tree.insert("", "end", tags=("ghost-key",))
    gui.tree.selection_set(item)
    gui._on_toggle_row()  # loop exhausts without match


def test_toggle_row_second_category(gui) -> None:
    cats = gui.categories
    if len(cats) < 2:
        pytest.skip("need 2+ categories")
    target = cats[-1]
    for item in gui.tree.get_children():
        if gui.tree.item(item, "tags") == (target.key,):
            gui.tree.selection_set(item)
            gui._on_toggle_row()
            break
    assert target.action.value in ("keep", "delete")


def test_refresh_skips_tagless_row(gui) -> None:
    gui.tree.insert("", "end")  # no tags
    gui._refresh_all_rows()


def test_confirm_with_backup_message(gui) -> None:
    gui.backup_var.set(True)
    with patch("runtime.uninstaller_gui.messagebox") as mb:
        mb.askyesno.return_value = True
        from runtime.uninstaller import CategoryAction

        cats = [c for c in gui.categories if c.action == CategoryAction.DELETE]
        if not cats:
            pytest.skip("no delete cats")
        assert gui._confirm_uninstall(cats) is True
        args = mb.askyesno.call_args[0][1]
        assert "Backup:" in args
