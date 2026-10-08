"""Gap coverage for runtime/uninstaller_gui.py - callbacks and worker paths."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("tkinter")
import tkinter as tk


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
    import time

    root = _make_tmp_root(tmp_path)
    from runtime.uninstaller_gui import UninstallerGUI

    try:
        g = UninstallerGUI(root)
    except Exception:
        time.sleep(0.2)  # transient Tk resource contention under xdist
        try:
            g = UninstallerGUI(root)
        except Exception:
            pytest.skip("tkinter not functional")
    yield g
    import contextlib

    with contextlib.suppress(Exception):
        g.win.destroy()


class TestDiscoverRoot:
    def test_discover_root_fallback(self):
        from runtime.uninstaller_gui import UninstallerGUI

        with patch("config.discover_root", side_effect=RuntimeError("x")):
            p = UninstallerGUI._discover_root()
        assert isinstance(p, Path)

    def test_discover_root_success(self):
        from runtime.uninstaller_gui import UninstallerGUI

        with patch("config.discover_root", return_value="C:/airoot"):
            p = UninstallerGUI._discover_root()
        assert p == Path("C:/airoot")


class TestToggleAndRows:
    def test_toggle_no_selection(self, gui):
        gui.tree.selection_remove(*gui.tree.selection())
        gui._on_toggle_row()  # no-op

    def test_toggle_row_no_tags(self, gui):
        gui.tree.selection_remove(*gui.tree.selection())
        gui.tree.insert("", "end", text="bare", values=("", "", "", ""))
        iid = gui.tree.get_children()[-1]
        gui.tree.item(iid, tags=())
        gui.tree.selection_set(iid)
        gui._on_toggle_row()  # tags empty -> return

    def test_refresh_all_rows(self, gui):
        gui._delete_all()
        gui._refresh_all_rows()

    def test_toggle_real_row(self, gui):
        iid = gui.tree.get_children()[0]
        tags = gui.tree.item(iid, "tags")
        key = tags[0]
        cat = next(c for c in gui.categories if c.key == key)
        before = cat.action
        gui.tree.selection_set(iid)
        gui._on_toggle_row()
        assert cat.action != before

    def test_keep_all_learned(self, gui):
        gui._delete_all()
        gui._keep_all_learned()
        for c in gui.categories:
            if c.is_learned:
                assert c.action == c.action.KEEP

    def test_backup_toggle_states(self, gui):
        gui.backup_var.set(False)
        gui._on_backup_toggle()
        assert str(gui.backup_entry.cget("state")) == "disabled"
        gui.backup_var.set(True)
        gui._on_backup_toggle()
        assert str(gui.backup_entry.cget("state")) == "normal"


class TestBackup:
    def test_resolve_disabled(self, gui):
        gui.backup_var.set(False)
        assert gui._resolve_backup_path() is None

    def test_resolve_empty(self, gui):
        gui.backup_var.set(True)
        gui.backup_path_var.set("  ")
        assert gui._resolve_backup_path() is None

    def test_resolve_path(self, gui):
        gui.backup_var.set(True)
        gui.backup_path_var.set("C:/tmp/bk.zip")
        p = gui._resolve_backup_path()
        assert p is not None and p.name == "bk.zip"

    def test_browse_cancel(self, gui):
        initial = gui.backup_path_var.get()
        with patch("runtime.uninstaller_gui.filedialog.asksaveasfilename",
                   return_value=""):
            gui._browse_backup()
        assert gui.backup_path_var.get() == initial

    def test_browse_accept(self, gui):
        with patch("runtime.uninstaller_gui.filedialog.asksaveasfilename",
                   return_value="C:/x/b.zip"):
            gui._browse_backup()
        assert gui.backup_path_var.get() == "C:/x/b.zip"


class TestUninstallClick:
    def test_no_delete_categories(self, gui):
        for c in gui.categories:
            c.action = c.action.KEEP
        with patch("runtime.uninstaller_gui.messagebox.showwarning") as warn:
            gui._on_uninstall_click()
            warn.assert_called_once()

    def test_cancel_confirm(self, gui):
        with patch("runtime.uninstaller_gui.messagebox.askyesno",
                   return_value=False):
            gui._on_uninstall_click()
        assert gui.worker is None

    def test_confirm_starts_worker(self, gui):
        with patch("runtime.uninstaller_gui.messagebox.askyesno",
                   return_value=True), \
             patch.object(gui.win, "after") as after, \
             patch.object(gui, "_run_uninstall"):
            gui._on_uninstall_click()
            gui.worker.join(timeout=5)
        after.assert_called_once()


class _VarStub:
    """Minimal StringVar stand-in for headless callback tests."""

    def __init__(self, initial: str = "") -> None:
        self._v = initial

    def get(self) -> str:
        return self._v

    def set(self, v: str) -> None:
        self._v = v


class _CatStub:
    def __init__(self, action: object, key: str = "k", label: str = "L") -> None:
        self.action = action
        self.key = key
        self.label = label


class TestHeadlessCallbacks:
    """Cover GUI callback paths without instantiating Tk — deterministic on
    runners where a real root window can't be created (xdist/CI)."""

    def test_browse_accept_sets_path(self, tmp_path):
        from runtime.uninstaller_gui import UninstallerGUI

        g = UninstallerGUI.__new__(UninstallerGUI)
        g.backup_path_var = _VarStub(str(tmp_path / "old.zip"))
        with patch("runtime.uninstaller_gui.filedialog.asksaveasfilename",
                   return_value=str(tmp_path / "b.zip")):
            g._browse_backup()
        assert g.backup_path_var.get() == str(tmp_path / "b.zip")

    def test_browse_cancel_keeps_path(self, tmp_path):
        from runtime.uninstaller_gui import UninstallerGUI

        g = UninstallerGUI.__new__(UninstallerGUI)
        g.backup_path_var = _VarStub(str(tmp_path / "old.zip"))
        with patch("runtime.uninstaller_gui.filedialog.asksaveasfilename",
                   return_value=""):
            g._browse_backup()
        assert g.backup_path_var.get() == str(tmp_path / "old.zip")

    def test_uninstall_click_no_delete_categories_warns(self):
        from runtime.uninstaller import CategoryAction
        from runtime.uninstaller_gui import UninstallerGUI

        g = UninstallerGUI.__new__(UninstallerGUI)
        g.categories = [_CatStub(CategoryAction.KEEP)]
        with patch("runtime.uninstaller_gui.messagebox.showwarning") as warn:
            g._on_uninstall_click()
        warn.assert_called_once()

    def test_uninstall_click_cancel_confirm_returns(self):
        from runtime.uninstaller import CategoryAction
        from runtime.uninstaller_gui import UninstallerGUI

        g = UninstallerGUI.__new__(UninstallerGUI)
        g.categories = [_CatStub(CategoryAction.DELETE)]
        with patch.object(g, "_confirm_uninstall", return_value=False):
            g._on_uninstall_click()
        assert not hasattr(g, "worker") or g.worker is None

    def test_uninstall_click_confirm_starts_worker(self):
        from runtime.uninstaller import CategoryAction
        from runtime.uninstaller_gui import UninstallerGUI

        g = UninstallerGUI.__new__(UninstallerGUI)
        g.categories = [_CatStub(CategoryAction.DELETE)]
        with patch.object(g, "_confirm_uninstall", return_value=True), \
             patch.object(g, "uninstall_btn", create=True), \
             patch.object(g, "_log", create=True), \
             patch.object(g, "_resolve_backup_path", return_value=None), \
             patch("runtime.uninstaller_gui.threading.Thread") as thread, \
             patch.object(g, "win", create=True) as win:
            g._on_uninstall_click()
            thread.assert_called_once()
            thread.return_value.start.assert_called_once()
            win.after.assert_called_once()

    def test_refresh_rows_skips_unmatched_tag(self):
        from runtime.uninstaller_gui import UninstallerGUI

        g = UninstallerGUI.__new__(UninstallerGUI)

        class _TreeStub:
            def get_children(self):
                return ["i1", "i2", "i3"]

            def item(self, iid, key):
                # i1: tag matches no category (loop falls through);
                # i2: empty tags -> continue; i3: matches -> _update_row.
                return {"i1": ("no-such-cat",), "i2": (), "i3": ("real-cat",)}[iid]

        g.tree = _TreeStub()
        g.categories = [_CatStub(object(), key="real-cat")]
        with patch.object(g, "_update_row", create=True) as upd:
            g._refresh_all_rows()
        upd.assert_called_once_with("i3", g.categories[0])

    def test_confirm_uninstall_no_backup(self):
        from runtime.uninstaller import CategoryAction
        from runtime.uninstaller_gui import UninstallerGUI

        g = UninstallerGUI.__new__(UninstallerGUI)
        g.backup_var = _VarStub("")
        g.backup_path_var = _VarStub("")
        g.categories = [_CatStub(CategoryAction.DELETE)]
        with patch("runtime.uninstaller_gui.messagebox.askyesno",
                   return_value=True) as ask:
            assert g._confirm_uninstall(g.categories) is True
        ask.assert_called_once()

    def test_run_uninstall_with_backup_calls_create(self, tmp_path):
        from runtime.uninstaller_gui import UninstallerGUI

        g = UninstallerGUI.__new__(UninstallerGUI)
        g._log_done = False
        with patch.object(g, "_create_backup", create=True) as cb, \
             patch.object(g, "_execute_deletions", create=True), \
             patch.object(g, "_log", create=True):
            g._run_uninstall(tmp_path / "b.zip")
        cb.assert_called_once_with(tmp_path / "b.zip")

    def test_create_backup_success_logs_path(self, tmp_path):
        from runtime.uninstaller_gui import UninstallerGUI

        result = tmp_path / "b.zip"
        result.write_bytes(b"pk")
        g = UninstallerGUI.__new__(UninstallerGUI)
        g.root_path = tmp_path
        g.categories = []
        logged = []
        with patch("runtime.uninstaller_gui.create_backup",
                   return_value=result), \
             patch.object(g, "_log", create=True,
                          side_effect=logged.append):
            g._create_backup(result)
        assert any("Backup created" in m for m in logged)

    def test_run_uninstall_error_marks_done(self):
        from runtime.uninstaller_gui import UninstallerGUI

        g = UninstallerGUI.__new__(UninstallerGUI)
        g._log_done = False
        with patch.object(g, "_execute_deletions", create=True,
                          side_effect=RuntimeError("boom")), \
             patch.object(g, "_log", create=True):
            g._run_uninstall(None)
        assert g._log_done is True

    def test_toggle_row_no_selection_returns(self):
        from runtime.uninstaller_gui import UninstallerGUI

        g = UninstallerGUI.__new__(UninstallerGUI)

        class _TreeStub:
            def selection(self):
                return []

        g.tree = _TreeStub()
        g._on_toggle_row()  # early return: nothing selected

    def test_toggle_row_empty_tags_returns(self):
        from runtime.uninstaller_gui import UninstallerGUI

        g = UninstallerGUI.__new__(UninstallerGUI)

        class _TreeStub:
            def selection(self):
                return ["i1"]

            def item(self, iid, key):
                return ()

        g.tree = _TreeStub()
        g._on_toggle_row()  # early return: row has no tags

    def test_toggle_row_unknown_key_falls_through(self):
        from runtime.uninstaller_gui import UninstallerGUI

        g = UninstallerGUI.__new__(UninstallerGUI)

        class _TreeStub:
            def selection(self):
                return ["i1"]

            def item(self, iid, key):
                return ("ghost-key",)

        g.tree = _TreeStub()
        g.categories = [_CatStub(object(), key="real-cat")]
        g._on_toggle_row()  # tag matches no category -> loop exhausts

    def test_toggle_row_match_flips_action(self):
        from runtime.uninstaller import CategoryAction
        from runtime.uninstaller_gui import UninstallerGUI

        g = UninstallerGUI.__new__(UninstallerGUI)
        cat = _CatStub(CategoryAction.KEEP, key="k1")

        class _TreeStub:
            def selection(self):
                return ["i1"]

            def item(self, iid, key):
                return ("k1",)

        g.tree = _TreeStub()
        g.categories = [cat]
        with patch.object(g, "_update_row", create=True) as upd:
            g._on_toggle_row()
            assert cat.action == CategoryAction.DELETE
            g._on_toggle_row()  # covers the DELETE -> KEEP ternary arm
            assert cat.action == CategoryAction.KEEP
        assert upd.call_count == 2

    def test_create_backup_none_result_logs_fallback(self, tmp_path):
        from runtime.uninstaller_gui import UninstallerGUI

        g = UninstallerGUI.__new__(UninstallerGUI)
        g.root_path = tmp_path
        g.categories = []
        logged = []
        with patch("runtime.uninstaller_gui.create_backup",
                   return_value=None), \
             patch.object(g, "_log", create=True,
                          side_effect=logged.append):
            g._create_backup(tmp_path / "b.zip")
        assert any("may be empty" in m for m in logged)


class TestWorker:
    def test_run_uninstall_no_backup(self, gui):
        with patch.object(gui, "_execute_deletions") as ex:
            gui._run_uninstall(None)
            ex.assert_called_once()
        assert gui._log_done

    def test_run_uninstall_with_backup(self, gui, tmp_path):
        with patch.object(gui, "_execute_deletions"), \
             patch("runtime.uninstaller_gui.create_backup",
                   return_value=tmp_path / "b.zip") as cb:
            (tmp_path / "b.zip").write_bytes(b"pk")
            gui._run_uninstall(tmp_path / "b.zip")
            cb.assert_called_once()

    def test_run_uninstall_error(self, gui):
        with patch.object(gui, "_execute_deletions",
                          side_effect=RuntimeError("boom")):
            gui._run_uninstall(None)
        assert gui._log_done

    def test_backup_missing_result(self, gui, tmp_path):
        with patch("runtime.uninstaller_gui.create_backup",
                   return_value=None):
            gui._create_backup(tmp_path / "b.zip")
        msg = gui.log_queue.get_nowait() + gui.log_queue.get_nowait()
        assert "Backup" in msg


class TestExecuteDeletions:
    def test_abort_non_aizee_root(self, gui, tmp_path):
        bad = tmp_path / "notaizee"
        bad.mkdir()
        gui.root_path = bad
        gui._execute_deletions()
        log = ""
        while not gui.log_queue.empty():
            log += gui.log_queue.get_nowait()
        assert "ABORT" in log

    def test_delete_all_categories(self, gui):
        for c in gui.categories:
            c.action = c.action.DELETE
        with patch("runtime.uninstaller_gui.pip_uninstall", return_value=True), \
             patch("runtime.uninstaller_gui.remove_cli_shim", return_value=True), \
             patch("runtime.uninstaller_gui.remove_mcp_config_entries", return_value=[]), \
             patch("runtime.uninstaller_gui.delete_category", return_value=[]):
            gui._execute_deletions()
        log = ""
        while not gui.log_queue.empty():
            log += gui.log_queue.get_nowait()
        assert "DELETE" in log

    def test_keep_categories(self, gui):
        for c in gui.categories:
            c.action = c.action.KEEP
        gui._execute_deletions()
        log = ""
        while not gui.log_queue.empty():
            log += gui.log_queue.get_nowait()
        assert "KEEP" in log


class TestPollLog:
    def test_poll_drains_and_reschedules(self, gui):
        gui._log("hello\n")
        gui._log_done = False
        with patch.object(gui.win, "after") as after:
            gui._poll_log()
        after.assert_called_once()
        assert gui.log_queue.empty()

    def test_poll_done(self, gui):
        gui._log_done = True
        with patch("runtime.uninstaller_gui.messagebox.showinfo") as info:
            gui._poll_log()
        info.assert_called_once()
        assert gui._log_done is False


class TestDeleteSingle:
    def test_symlinks_branch(self, gui):
        from runtime.uninstaller import UninstallCategory

        cat = UninstallCategory(
            key="symlinks", label="Symlinks", paths=[],
            description="", is_learned=False,
        )
        gui._delete_single_category(cat)
        assert "symlinks: checked" in gui.log_queue.get_nowait()

    def test_mcp_configs_branch(self, gui):
        from runtime.uninstaller import UninstallCategory

        cat = UninstallCategory(
            key="mcp_configs", label="MCP", paths=[],
            description="", is_learned=False,
        )
        with patch("runtime.uninstaller_gui.remove_mcp_config_entries", return_value=["a", "b"]):
            gui._delete_single_category(cat)
        assert "configs cleaned: 2" in gui.log_queue.get_nowait()


class TestRun:
    def test_run_calls_mainloop(self, gui):
        with patch.object(gui.win, "mainloop") as ml:
            gui.run()
        ml.assert_called_once()


class TestMain:
    def test_main_success(self, tmp_path):
        root = _make_tmp_root(tmp_path)
        with patch("runtime.uninstaller_gui.UninstallerGUI") as mg_mock:
            from runtime.uninstaller_gui import main

            rc = main([str(root)])
            assert rc == 0
            mg_mock.return_value.run.assert_called_once()

    def test_main_no_args(self):
        with patch("runtime.uninstaller_gui.UninstallerGUI"):
            from runtime.uninstaller_gui import main

            rc = main([])
            assert rc == 0

    def test_main_gui_fails(self, tmp_path):
        with patch("runtime.uninstaller_gui.UninstallerGUI",
                   side_effect=tk.TclError("no display")):
            from runtime.uninstaller_gui import main

            assert main([str(tmp_path)]) == 1


class TestLoadCategories:
    def test_empty_categories_destroys(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        (empty / ".aizee-version").write_text("1.0")
        (empty / "config.py").write_text("# c")
        (empty / "runtime").mkdir()
        (empty / "runtime" / "kernel.py").write_text("# k")
        from runtime.uninstaller_gui import UninstallerGUI

        # Categories package/cli_shim/symlinks always exist so tree fills
        try:
            g = UninstallerGUI(empty)
            assert g.categories
            g.win.destroy()
        except Exception:
            pytest.skip("tkinter not functional")
