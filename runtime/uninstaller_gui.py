#!/usr/bin/env python3
"""aiZee uninstaller — tkinter GUI with selective keep/backup.

Launch:
    python runtime/uninstaller_gui.py
    aizee uninstall --gui

Features:
  - Treeview of categories with Keep/Delete radio per row
  - Size column + learned/OS type indicator
  - Backup checkbox + custom path picker
  - Live log output during uninstall
  - Runs deletion in a background thread (UI stays responsive)
  - Confirmation dialog before destructive actions
"""

from __future__ import annotations

import contextlib
import logging
import queue
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

# Reuse the core logic from the CLI uninstaller
from runtime.uninstaller import (
    CategoryAction,
    UninstallCategory,
    _build_categories,
    _format_size,
    create_backup,
    delete_category,
    pip_uninstall,
    remove_cli_shim,
    remove_mcp_config_entries,
)

if TYPE_CHECKING:
    pass

_logger = logging.getLogger(__name__)


class _UninstallerUIBuilder:
    """Helper that constructs the tkinter UI for UninstallerGUI."""

    def __init__(self, gui: UninstallerGUI) -> None:
        self._gui = gui

    def build(self) -> None:
        """Build all UI sections in order."""
        self._build_header()
        self._build_tree()
        self._build_action_buttons()
        self._build_backup_row()
        self._build_log_area()
        self._build_bottom_buttons()
        self._gui._on_backup_toggle()

    def _build_header(self) -> None:
        header = ttk.Frame(self._gui.win)
        header.pack(fill="x", padx=16, pady=(12, 4))
        ttk.Label(header, text="aiZee Uninstaller", style="Header.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            header,
            text=f"Root: {self._gui.root_path}",
            style="Info.TLabel",
        ).pack(anchor="w")

    def _build_tree(self) -> None:
        tree_frame = ttk.Frame(self._gui.win)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=8)
        cols = ("action", "size", "type", "desc")
        self._gui.tree = ttk.Treeview(
            tree_frame, columns=cols, show="tree headings", height=12
        )
        self._configure_tree_headings()
        self._configure_tree_columns()
        vsb = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self._gui.tree.yview
        )
        self._gui.tree.configure(yscrollcommand=vsb.set)
        self._gui.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._gui.tree.bind("<Double-1>", self._gui._on_toggle_row)
        self._gui.tree.bind("<Return>", self._gui._on_toggle_row)

    def _configure_tree_headings(self) -> None:
        self._gui.tree.heading("#0", text="Category")
        self._gui.tree.heading("action", text="Action")
        self._gui.tree.heading("size", text="Size")
        self._gui.tree.heading("type", text="Type")
        self._gui.tree.heading("desc", text="Description")

    def _configure_tree_columns(self) -> None:
        self._gui.tree.column("#0", width=240, anchor="w")
        self._gui.tree.column("action", width=70, anchor="center")
        self._gui.tree.column("size", width=70, anchor="e")
        self._gui.tree.column("type", width=60, anchor="center")
        self._gui.tree.column("desc", width=280, anchor="w")

    def _build_action_buttons(self) -> None:
        btn_frame = ttk.Frame(self._gui.win)
        btn_frame.pack(fill="x", padx=16, pady=4)
        ttk.Button(
            btn_frame, text="Keep All Learned", command=self._gui._keep_all_learned
        ).pack(side="left", padx=2)
        ttk.Button(
            btn_frame, text="Delete All", command=self._gui._delete_all
        ).pack(side="left", padx=2)
        ttk.Button(
            btn_frame, text="Toggle Selected", command=self._gui._on_toggle_row
        ).pack(side="left", padx=2)

    def _build_backup_row(self) -> None:
        backup_frame = ttk.Frame(self._gui.win)
        backup_frame.pack(fill="x", padx=16, pady=4)
        self._gui.backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            backup_frame,
            text="Create backup zip before uninstall",
            variable=self._gui.backup_var,
            command=self._gui._on_backup_toggle,
        ).pack(side="left")
        self._gui.backup_path_var = tk.StringVar(
            value=str(
                Path.home()
                / f"aizee-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
            )
        )
        self._gui.backup_entry = ttk.Entry(
            backup_frame, textvariable=self._gui.backup_path_var, width=45
        )
        self._gui.backup_entry.pack(side="left", padx=4)
        self._gui.browse_btn = ttk.Button(
            backup_frame, text="Browse...", command=self._gui._browse_backup
        )
        self._gui.browse_btn.pack(side="left", padx=2)

    def _build_log_area(self) -> None:
        log_frame = ttk.LabelFrame(self._gui.win, text="Log", padding=4)
        log_frame.pack(fill="both", expand=False, padx=16, pady=(4, 8))
        self._gui.log_text = tk.Text(
            log_frame,
            height=8,
            wrap="word",
            state="disabled",
            background="#11111b",
            foreground="#a6e3a1",
            font=("Consolas", 9),
            insertbackground="#cdd6f4",
        )
        log_scroll = ttk.Scrollbar(log_frame, command=self._gui.log_text.yview)
        self._gui.log_text.configure(yscrollcommand=log_scroll.set)
        self._gui.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

    def _build_bottom_buttons(self) -> None:
        bottom = ttk.Frame(self._gui.win)
        bottom.pack(fill="x", padx=16, pady=(0, 12))
        self._gui.uninstall_btn = ttk.Button(
            bottom, text="Uninstall", command=self._gui._on_uninstall_click
        )
        self._gui.uninstall_btn.pack(side="right", padx=4)
        ttk.Button(bottom, text="Cancel", command=self._gui.win.destroy).pack(
            side="right", padx=4
        )


class UninstallerGUI:
    """Tkinter GUI for the aiZee uninstaller."""

    tree: ttk.Treeview
    backup_var: tk.BooleanVar
    backup_path_var: tk.StringVar
    backup_entry: ttk.Entry
    browse_btn: ttk.Button
    log_text: tk.Text
    uninstall_btn: ttk.Button
    _log_done: bool = False

    def __init__(self, root_path: Path | None = None) -> None:
        self.root_path = root_path or self._discover_root()
        self.categories: list[UninstallCategory] = []
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None
        self._init_window()
        self._init_style()
        self._build_ui()
        self._load_categories()

    def _init_window(self) -> None:
        """Create and configure the main tkinter window."""
        self.win = tk.Tk()
        self.win.title("aiZee Uninstaller")
        self.win.geometry("780x620")
        self.win.minsize(680, 520)
        self.win.configure(bg="#1e1e2e")

    def _init_style(self) -> None:
        """Configure the ttk style theme and widget styles."""
        style = ttk.Style(self.win)
        with contextlib.suppress(tk.TclError):
            style.theme_use("clam")
        style.configure("Treeview", background="#2a2a3e", foreground="#cdd6f4",
                        fieldbackground="#2a2a3e", rowheight=28)
        style.configure("Treeview.Heading", background="#181825",
                        foreground="#cdd6f4", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#45475a")])
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4",
                        font=("Segoe UI", 10))
        style.configure("TButton", background="#45475a", foreground="#cdd6f4",
                        font=("Segoe UI", 10, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"),
                        foreground="#f38ba8")
        style.configure("Info.TLabel", foreground="#a6adc8",
                        font=("Segoe UI", 9))
        style.configure("Log.Text", background="#11111b", foreground="#a6e3a1",
                        font=("Consolas", 9))

    @staticmethod
    def _discover_root() -> Path:
        """Discover aiZee root via config or env."""
        env = Path(__file__).resolve().parent.parent
        env_root = env.parent
        try:
            import config as config_mod
            return Path(config_mod.discover_root())
        except Exception as exc:
            _logger.debug("root discovery failed: %s", exc, exc_info=True)
            return env_root

    # --- UI Construction ---

    def _build_ui(self) -> None:
        """Build the full UI layout."""
        _UninstallerUIBuilder(self).build()

    # --- Category loading ---

    def _load_categories(self) -> None:
        """Load categories from the uninstaller module and populate the tree."""
        all_cats = _build_categories(self.root_path)
        self.categories = [
            c for c in all_cats
            if c.exists() or c.key in ("package", "cli_shim", "symlinks")
        ]

        if not self.categories:
            messagebox.showinfo("aiZee", "Nothing to uninstall — no aiZee files found.")
            self.win.destroy()
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        for cat in self.categories:
            size = cat.total_size_bytes()
            size_str = _format_size(size) if size > 0 else "-"
            type_str = "learned" if cat.is_learned else "OS"
            action_str = cat.action.value
            self.tree.insert(
                "",
                "end",
                text=cat.label,
                values=(action_str, size_str, type_str, cat.description),
                tags=(cat.key,),
            )

    # --- UI callbacks ---

    def _on_toggle_row(self, _event: object | None = None) -> None:
        """Toggle the selected row's action between keep/delete."""
        sel = self.tree.selection()
        if not sel:
            return
        item_id = sel[0]
        tags = self.tree.item(item_id, "tags")
        if not tags:
            return
        key = tags[0]
        for cat in self.categories:
            if cat.key == key:
                cat.action = (
                    CategoryAction.DELETE
                    if cat.action == CategoryAction.KEEP
                    else CategoryAction.KEEP
                )
                self._update_row(item_id, cat)
                break

    def _update_row(self, item_id: str, cat: UninstallCategory) -> None:
        """Refresh a single tree row from its category."""
        size = cat.total_size_bytes()
        size_str = _format_size(size) if size > 0 else "-"
        type_str = "learned" if cat.is_learned else "OS"
        self.tree.item(
            item_id,
            values=(cat.action.value, size_str, type_str, cat.description),
        )

    def _keep_all_learned(self) -> None:
        """Set all learned categories to KEEP."""
        for cat in self.categories:
            if cat.is_learned:
                cat.action = CategoryAction.KEEP
        self._refresh_all_rows()

    def _delete_all(self) -> None:
        """Set ALL categories to DELETE (full wipe)."""
        for cat in self.categories:
            cat.action = CategoryAction.DELETE
        self._refresh_all_rows()

    def _refresh_all_rows(self) -> None:
        """Re-read all categories and update their rows."""
        for item_id in self.tree.get_children():
            tags = self.tree.item(item_id, "tags")
            if not tags:
                continue
            key = tags[0]
            for cat in self.categories:
                if cat.key == key:
                    self._update_row(item_id, cat)
                    break

    def _on_backup_toggle(self) -> None:
        """Enable/disable backup path entry based on checkbox."""
        enabled = self.backup_var.get()
        new_state = "normal" if enabled else "disabled"
        self.backup_entry.configure(state=new_state)
        self.browse_btn.configure(state=new_state)

    def _browse_backup(self) -> None:
        """Open a file picker for the backup zip path."""
        initial = self.backup_path_var.get() or str(Path.home())
        path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("Zip files", "*.zip"), ("All files", "*.*")],
            initialdir=str(Path(initial).parent) if Path(initial).parent.exists() else str(Path.home()),
            initialfile=Path(initial).name if Path(initial).name else "aizee-backup.zip",
        )
        if path:
            self.backup_path_var.set(path)

    # --- Uninstall execution ---

    def _on_uninstall_click(self) -> None:
        """Confirm and start the uninstall in a background thread."""
        delete_cats = [c for c in self.categories if c.action == CategoryAction.DELETE]
        if not delete_cats:
            messagebox.showwarning("aiZee", "No categories selected for deletion.")
            return
        if not self._confirm_uninstall(delete_cats):
            return
        self.uninstall_btn.configure(state="disabled")
        self._log("Starting uninstall...\n")
        backup_path = self._resolve_backup_path()
        self.worker = threading.Thread(
            target=self._run_uninstall,
            args=(backup_path,),
            daemon=True,
        )
        self.worker.start()
        self.win.after(200, self._poll_log)

    def _confirm_uninstall(self, delete_cats: list[UninstallCategory]) -> bool:
        """Show confirmation dialog and return True if user confirms."""
        delete_labels = "\n".join(f"  - {c.label}" for c in delete_cats)
        keep_cats = [c for c in self.categories if c.action == CategoryAction.KEEP]
        keep_labels = "\n".join(f"  - {c.label}" for c in keep_cats) or "  (none)"
        backup_msg = ""
        if self.backup_var.get():
            backup_msg = f"\n\nBackup: {self.backup_path_var.get()}"
        return messagebox.askyesno(
            "Confirm Uninstall",
            f"The following will be DELETED:\n{delete_labels}\n\n"
            f"The following will be KEPT:\n{keep_labels}{backup_msg}\n\n"
            f"This action is irreversible. Continue?",
            icon="warning",
            default="no",
        )

    def _resolve_backup_path(self) -> Path | None:
        """Resolve the backup path from the UI, or None if backup is disabled."""
        if not self.backup_var.get():
            return None
        bp = self.backup_path_var.get().strip()
        return Path(bp) if bp else None

    def _run_uninstall(self, backup_path: Path | None) -> None:
        """Worker thread: execute the uninstall plan."""
        try:
            if backup_path:
                self._create_backup(backup_path)
            self._execute_deletions()
            self._log("\nUninstall complete.\n")
            self._log_done = True
        except Exception as e:
            self._log(f"\nERROR: {e}\n")
            self._log_done = True

    def _create_backup(self, backup_path: Path) -> None:
        """Create a backup zip of all categories."""
        self._log(f"Creating backup at {backup_path}...\n")
        result = create_backup(self.root_path, self.categories, backup_path)
        if result and result.exists():
            self._log(f"  Backup created: {result}\n")
        else:
            self._log("  Backup completed (may be empty).\n")

    def _execute_deletions(self) -> None:
        """Iterate categories and delete or keep each one."""
        for cat in self.categories:
            if cat.action != CategoryAction.DELETE:
                self._log(f"  [KEEP] {cat.label}\n")
                continue
            self._log(f"  [DELETE] {cat.label}... ")
            self._delete_single_category(cat)

    def _delete_single_category(self, cat: UninstallCategory) -> None:
        """Execute deletion for a single category based on its key."""
        if cat.key == "package":
            ok = pip_uninstall()
            self._log(f"pip uninstall: {'OK' if ok else 'skipped'}\n")
        elif cat.key == "cli_shim":
            ok = remove_cli_shim()
            self._log(f"shim removed: {'yes' if ok else 'no'}\n")
        elif cat.key == "mcp_configs":
            removed = remove_mcp_config_entries(self.root_path)
            self._log(f"configs cleaned: {len(removed)}\n")
        elif cat.key == "symlinks":
            self._log("symlinks: checked\n")
        else:
            removed = delete_category(cat)
            self._log(f"removed {len(removed)} paths\n")

    def _log(self, msg: str) -> None:
        """Push a log message to the queue (thread-safe)."""
        self.log_queue.put(msg)

    def _poll_log(self) -> None:
        """Drain the log queue and append to the Text widget."""
        self.log_text.configure(state="normal")
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_text.insert("end", msg)
            self.log_text.see("end")
        self.log_text.configure(state="disabled")

        if self._log_done:
            self.uninstall_btn.configure(state="normal")
            self._log_done = False
            messagebox.showinfo("aiZee", "Uninstall complete. See log for details.")
        else:
            self.win.after(200, self._poll_log)

    # --- Run ---

    def run(self) -> None:
        """Start the tkinter main loop."""
        self.win.mainloop()


def main(argv: list[str] | None = None) -> int:
    """Entry point for the GUI uninstaller."""
    args = argv if argv is not None else sys.argv[1:]
    root_path: Path | None = None
    if args:
        root_path = Path(args[0])

    try:
        gui = UninstallerGUI(root_path)
        gui.run()
    except Exception as e:
        # Fallback to console if tkinter is unavailable (headless)
        print(f"GUI unavailable ({e}). Use 'aizee uninstall' for console mode.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
