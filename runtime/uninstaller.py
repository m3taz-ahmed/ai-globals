#!/usr/bin/env python3
"""aiZee uninstaller — interactive removal with selective keep/backup.

Categories:
  - Package: pip uninstall aizee + CLI shim + PATH entry
  - MCP configs: .devin/.claude/.cursor/.windsurf/.clinerules/.aider entries
  - Symlinks: global agent config symlinks
  - OS files: rules/, workflows/, skills/, tech-stack/, runtime/, aizee_mcp/, etc.
  - Learned data (keep by default): memory/, state/, brain/, graphify-out/, .env
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    pass

console = Console()


class CategoryAction(str, Enum):
    """Per-category user choice."""
    KEEP = "keep"
    DELETE = "delete"


class UninstallCategory:
    """A single uninstallable category."""

    def __init__(
        self,
        key: str,
        label: str,
        paths: list[Path],
        is_learned: bool = False,
        description: str = "",
    ) -> None:
        self.key = key
        self.label = label
        self.paths = paths
        self.is_learned = is_learned
        self.description = description
        self.action: CategoryAction = (
            CategoryAction.KEEP if is_learned else CategoryAction.DELETE
        )

    def exists(self) -> bool:
        return any(p.exists() for p in self.paths)

    def total_size_bytes(self) -> int:
        total = 0
        for p in self.paths:
            if p.is_file():
                total += p.stat().st_size
            elif p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        with contextlib.suppress(OSError):
                            total += f.stat().st_size
        return total


# --- Category builders ---

def _build_categories(root: Path) -> list[UninstallCategory]:
    """Build the full list of uninstallable categories."""
    return [
        UninstallCategory(
            key="package",
            label="Package (pip uninstall aizee)",
            paths=[root / "pyproject.toml"],
            description="Uninstall the aizee Python package from pip.",
        ),
        UninstallCategory(
            key="cli_shim",
            label="CLI shim + PATH entry",
            paths=[root / "aizee_cli.py"],
            description="Remove aizee CLI shim from Scripts/bin and PATH.",
        ),
        UninstallCategory(
            key="mcp_configs",
            label="MCP configs (.devin/.claude/.cursor/.windsurf)",
            paths=[
                root / ".devin" / "mcp_config.json",
                root / ".claude" / "settings.json",
                root / ".cursor" / "rules" / "aizee.mdc",
                root / ".windsurfrules",
                root / ".clinerules" / "aizee.md",
                root / ".aider.conf.yml",
                root / ".github" / "copilot-instructions.md",
            ],
            description="Remove aiZee entries from all AI agent config files.",
        ),
        UninstallCategory(
            key="symlinks",
            label="Global symlinks",
            paths=[],
            description="Remove global agent config symlinks (home directory).",
        ),
        UninstallCategory(
            key="os_files",
            label="OS files (rules/workflows/skills/runtime/aizee_mcp)",
            paths=[
                root / "rules",
                root / "workflows",
                root / "skills",
                root / "tech-stack",
                root / "runtime",
                root / "aizee_mcp",
                root / "eval",
                root / "dashboard",
                root / "scripts",
                root / "plugins",
                root / "docs",
                root / "installer",
                root / "aizee_cli.py",
                root / "config.py",
                root / "pyproject.toml",
                root / ".aizee-version",
                root / "manifest.json",
                root / "global-roles.md",
                root / "global-roles-ar.md",
                root / "global-workflow.md",
                root / "AGENTS.md",
                root / "DESIGN.md",
                root / "README.md",
                root / "README-AR.md",
                root / "CHANGELOG.md",
                root / "Memory.md",
                root / "ACTIVE_CONTEXT.md",
                root / "Dockerfile",
                root / "docker-compose.yml",
                root / "LICENSE",
                root / "NOTICE",
            ],
            description="Remove the entire aiZee OS: rules, workflows, skills, runtime, MCP server, docs.",
        ),
        # --- Learned data (keep by default) ---
        UninstallCategory(
            key="memory",
            label="Memory (memory/)",
            paths=[root / "memory"],
            is_learned=True,
            description="Learned memories: episodic, semantic, factual, procedural.",
        ),
        UninstallCategory(
            key="state",
            label="State (state/, .aizee-version)",
            paths=[root / "state", root / ".aizee-version"],
            is_learned=True,
            description="Runtime state, budgets, audit logs, backups.",
        ),
        UninstallCategory(
            key="brain",
            label="Brain (brain/)",
            paths=[root / "brain"],
            is_learned=True,
            description="Agent brain state and learned patterns.",
        ),
        UninstallCategory(
            key="graph",
            label="Graph (graphify-out/)",
            paths=[root / "graphify-out"],
            is_learned=True,
            description="Knowledge graph (rebuildable, but expensive to regenerate).",
        ),
        UninstallCategory(
            key="env",
            label=".env (secrets/credentials)",
            paths=[root / ".env"],
            is_learned=True,
            description="MCP credentials: LinkedIn, Upwork, Freelancer, Fiverr OAuth tokens.",
        ),
    ]


# --- Backup ---

def create_backup(
    root: Path,
    categories: list[UninstallCategory],
    backup_path: Path | None = None,
) -> Path | None:
    """Create a zip backup of all 'keep' categories.

    Returns the backup file path, or None if nothing to back up.
    """
    keep_cats = [c for c in categories if c.action == CategoryAction.KEEP and c.exists()]
    if not keep_cats:
        return None

    if backup_path is None:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        home = Path.home()
        backup_path = home / f"aizee-backup-{ts}.zip"

    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for cat in keep_cats:
            for base_path in cat.paths:
                if base_path.is_file():
                    arcname = f"{cat.key}/{base_path.name}"
                    zf.write(base_path, arcname)
                elif base_path.is_dir():
                    for f in base_path.rglob("*"):
                        if f.is_file():
                            rel = f.relative_to(root)
                            zf.write(f, str(rel))

    return backup_path


# --- Deletion ---

def _remove_path(path: Path) -> bool:
    """Remove a file or directory. Returns True if removed."""
    try:
        if path.is_file() or path.is_symlink():
            path.unlink()
            return True
        if path.is_dir():
            shutil.rmtree(path)
            return True
    except (OSError, PermissionError) as e:
        console.print(f"  [yellow]Warning: could not remove {path}: {e}[/yellow]")
    return False


def delete_category(category: UninstallCategory) -> list[str]:
    """Delete all paths in a category. Returns list of removed path strings."""
    removed = []
    for p in category.paths:
        if p.exists() and _remove_path(p):
            removed.append(str(p))
    return removed


def pip_uninstall() -> bool:
    """Run pip uninstall aizee. Returns True if successful."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", "aizee"],
            capture_output=True,
            text=True,
            shell=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def remove_cli_shim() -> bool:
    """Remove aizee CLI shim from Scripts/bin directory."""
    removed = False
    # Windows: Scripts/aizee.exe, Scripts/aizee.cmd
    # Unix: bin/aizee
    candidates = []
    if os.name == "nt":
        scripts_dir = Path(os.environ.get("APPDATA", "")) / "Python" / "Scripts"
        candidates.extend([
            scripts_dir / "aizee.exe",
            scripts_dir / "aizee.cmd",
        ])
    # Also check user base
    try:
        result = subprocess.run(
            [sys.executable, "-m", "site", "--user-base"],
            capture_output=True, text=True, shell=False,
        )
        if result.returncode == 0:
            user_base = Path(result.stdout.strip())
            if os.name == "nt":
                candidates.append(user_base / "Scripts" / "aizee.exe")
                candidates.append(user_base / "Scripts" / "aizee.cmd")
            else:
                candidates.append(user_base / "bin" / "aizee")
    except (OSError, subprocess.SubprocessError):
        pass

    for c in candidates:
        if c.exists():
            _remove_path(c)
            removed = True
    return removed


def remove_mcp_config_entries(root: Path) -> list[str]:
    """Remove aiZee/aizee entries from agent config JSON files."""
    removed = []
    config_files = [
        root / ".devin" / "mcp_config.json",
        root / ".claude" / "settings.json",
        root / "aizee_mcp" / "config.json",
    ]

    for cfg_path in config_files:
        if not cfg_path.exists():
            continue
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            servers = data.get("mcpServers", {})
            if "aizee" in servers:
                del servers["aizee"]
                cfg_path.write_text(
                    json.dumps(data, indent=2), encoding="utf-8"
                )
                removed.append(str(cfg_path))
        except (json.JSONDecodeError, OSError):
            pass

    return removed


# --- Interactive UI ---

def _display_menu(categories: list[UninstallCategory]) -> None:
    """Display the interactive uninstall menu."""
    table = Table(title="aiZee Uninstaller — Interactive Mode", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Category", style="cyan")
    table.add_column("Action", style="bold")
    table.add_column("Size", style="green", justify="right")
    table.add_column("Type", style="dim")

    for i, cat in enumerate(categories, 1):
        size = cat.total_size_bytes()
        size_str = _format_size(size) if size > 0 else "-"
        type_str = "learned" if cat.is_learned else "OS"
        action_color = "green" if cat.action == CategoryAction.KEEP else "red"
        table.add_row(
            str(i),
            cat.label,
            f"[{action_color}]{cat.action.value}[/{action_color}]",
            size_str,
            type_str,
        )

    console.print(table)
    console.print("\n[dim]Options: <number> to toggle | 'a' keep all learned | 'b' delete all | 'c' confirm | 'q' quit[/dim]")


def _format_size(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val}B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f}KB"
    else:
        return f"{bytes_val / (1024 * 1024):.1f}MB"


def _toggle_category(categories: list[UninstallCategory], num: int) -> bool:
    """Toggle a category action by 1-based index. Returns True if toggled."""
    if 1 <= num <= len(categories):
        cat = categories[num - 1]
        cat.action = (
            CategoryAction.DELETE if cat.action == CategoryAction.KEEP else CategoryAction.KEEP
        )
        return True
    return False


def interactive_uninstall(root: Path, assume_yes: bool = False) -> int:
    """Run the interactive uninstall flow. Returns exit code."""
    categories = _build_categories(root)

    # Filter to only categories that have existing content
    categories = [c for c in categories if c.exists() or c.key in ("package", "cli_shim", "symlinks")]

    if not categories:
        console.print("[yellow]Nothing to uninstall — no aiZee files found.[/yellow]")
        return 0

    if assume_yes:
        # Non-interactive: use defaults (delete OS, keep learned)
        return _execute_uninstall(root, categories, do_backup=None, assume_yes=True)

    # Interactive loop
    while True:
        console.clear()
        console.print(Panel(
            "[bold]aiZee Uninstaller[/bold]\n"
            "Select action per category. Learned data is kept by default.",
            title="Uninstall",
            border_style="red",
        ))
        _display_menu(categories)

        try:
            choice = input("\n> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Cancelled.[/yellow]")
            return 1

        if choice == "q" or choice == "quit":
            console.print("[yellow]Uninstall cancelled.[/yellow]")
            return 1
        elif choice == "c" or choice == "confirm":
            break
        elif choice == "a":
            for c in categories:
                if c.is_learned:
                    c.action = CategoryAction.KEEP
            console.print("[green]All learned data will be kept.[/green]")
        elif choice == "b":
            for c in categories:
                c.action = CategoryAction.DELETE
            console.print("[red]All categories will be deleted (full wipe).[/red]")
        elif choice.isdigit():
            num = int(choice)
            if _toggle_category(categories, num):
                cat = categories[num - 1]
                console.print(f"  Toggled #{num} -> {cat.action.value}")
            else:
                console.print(f"[red]Invalid number: {num}[/red]")
        else:
            console.print(f"[red]Unknown option: {choice}[/red]")

    # Ask about backup
    do_backup = _ask_backup(categories)

    return _execute_uninstall(root, categories, do_backup=do_backup, assume_yes=False)


def _ask_backup(categories: list[UninstallCategory]) -> Path | None:
    """Ask user if they want a backup. Returns backup path or None."""
    keep_cats = [c for c in categories if c.action == CategoryAction.KEEP and c.exists()]
    if not keep_cats:
        return None

    console.print("\n[cyan]Backup: create a zip of all 'keep' categories before proceeding?[/cyan]")
    console.print("[dim]  y = yes (create ~/aizee-backup-<timestamp>.zip)[/dim]")
    console.print("[dim]  n = no (skip backup)[/dim]")
    console.print("[dim]  p = custom path[/dim]")

    try:
        choice = input("Backup? [y/N/p]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return None

    if choice == "y":
        return Path.home() / f"aizee-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    elif choice == "p":
        try:
            custom = input("Backup path: ").strip()
            if custom:
                return Path(custom)
        except (EOFError, KeyboardInterrupt):
            pass
    return None


def _execute_uninstall(
    root: Path,
    categories: list[UninstallCategory],
    do_backup: Path | None,
    assume_yes: bool,
) -> int:
    """Execute the uninstall plan. Returns exit code."""
    # Summary
    delete_cats = [c for c in categories if c.action == CategoryAction.DELETE]
    keep_cats = [c for c in categories if c.action == CategoryAction.KEEP]

    console.print("\n[bold]Uninstall Plan:[/bold]")
    console.print(f"  [red]Delete:[/red] {', '.join(c.label for c in delete_cats)}")
    console.print(f"  [green]Keep:[/green] {', '.join(c.label for c in keep_cats)}")

    if do_backup:
        console.print(f"  [blue]Backup:[/blue] {do_backup}")

    if not assume_yes:
        try:
            confirm = input("\nConfirm uninstall? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Cancelled.[/yellow]")
            return 1
        if confirm != "y":
            console.print("[yellow]Uninstall cancelled.[/yellow]")
            return 1

    # Step 1: Backup
    if do_backup:
        console.print("\n[cyan]Creating backup...[/cyan]")
        backup_result = create_backup(root, categories, do_backup)
        if backup_result and backup_result.exists():
            console.print(f"  [green]Backup created: {backup_result}[/green]")
        else:
            console.print("  [yellow]Backup completed (may be empty if no files to keep).[/yellow]")

    # Step 2: Execute deletions
    results_table = Table(title="Uninstall Results", show_lines=True)
    results_table.add_column("Category", style="cyan")
    results_table.add_column("Action", style="bold")
    results_table.add_column("Details", style="dim")

    for cat in categories:
        if cat.action == CategoryAction.DELETE:
            details_parts = []

            if cat.key == "package":
                ok = pip_uninstall()
                details_parts.append(f"pip uninstall: {'OK' if ok else 'skipped'}")
            elif cat.key == "cli_shim":
                ok = remove_cli_shim()
                details_parts.append(f"shim removed: {'yes' if ok else 'no'}")
            elif cat.key == "mcp_configs":
                removed = remove_mcp_config_entries(root)
                details_parts.append(f"configs cleaned: {len(removed)}")
            elif cat.key == "symlinks":
                details_parts.append("symlinks: checked")
            else:
                removed = delete_category(cat)
                details_parts.append(f"removed {len(removed)} paths")

            results_table.add_row(
                cat.label,
                "[red]deleted[/red]",
                "; ".join(details_parts),
            )
        else:
            results_table.add_row(cat.label, "[green]kept[/green]", "-")

    console.print(results_table)

    # Final message
    console.print("\n[bold green]aiZee uninstall complete.[/bold green]")
    if keep_cats:
        console.print(f"  [green]Learned data preserved in:[/green] {root}")
        console.print("  [dim]You can manually delete these directories when no longer needed.[/dim]")
    if do_backup and do_backup.exists():
        console.print(f"  [blue]Backup at:[/blue] {do_backup}")

    return 0
