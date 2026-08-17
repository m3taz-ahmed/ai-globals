#!/usr/bin/env python3
"""aiZee brain backup — save learned data to a timestamped folder.

Backs up:
  - memory/       (episodic, semantic, factual, procedural memories)
  - state/        (runtime state, budgets, audit logs, dashboard token)
  - brain/        (agent brain state, learned patterns)
  - graphify-out/ (knowledge graph — expensive to regenerate)
  - .env          (MCP credentials: LinkedIn, Upwork, Freelancer, Fiverr)

Output: <dest>/aizee-backup-<YYYY-MM-DD>-<HHMMSS>/

Usage:
    python scripts/backup_brain.py                    # backup to <root>/backups/
    python scripts/backup_brain.py --dest D:\backups  # custom destination
    python scripts/backup_brain.py --root C:\aizee    # custom aiZee root
"""

from __future__ import annotations

import argparse
import contextlib
import shutil
from datetime import datetime
from pathlib import Path

LEARNED_DIRS = ["memory", "state", "brain", "graphify-out"]
LEARNED_FILES = [".env"]


def _dir_size(path: Path) -> int:
    """Calculate total size of a directory in bytes."""
    total = 0
    if path.is_dir():
        for f in path.rglob("*"):
            if f.is_file():
                with contextlib.suppress(OSError):
                    total += f.stat().st_size
    return total


def _format_size(bytes_val: int) -> str:
    """Format bytes as human-readable string."""
    if bytes_val < 1024:
        return f"{bytes_val}B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f}KB"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.1f}MB"
    return f"{bytes_val / (1024 * 1024 * 1024):.2f}GB"


def _backup_item(src: Path, dst: Path) -> bool:
    """Copy a file or directory to dst. Returns True if copied."""
    try:
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return True
        elif src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            return True
    except (OSError, shutil.Error) as e:
        print(f"    [WARN] Could not copy {src.name}: {e}")
    return False


def run_backup(root: Path, dest: Path) -> int:
    """Main backup flow. Returns exit code."""
    print("=" * 60)
    print("  aiZee Brain Backup — Save learned data")
    print("=" * 60)
    print()
    print(f"  Source: {root}")
    print(f"  Dest:   {dest}")
    print()

    # Check source exists
    if not root.exists():
        print(f"[ERROR] aiZee root not found: {root}")
        return 1

    # Create timestamped backup folder
    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    backup_folder = dest / f"aizee-backup-{ts}"
    backup_folder.mkdir(parents=True, exist_ok=True)

    # Write metadata file
    meta = backup_folder / "_backup_meta.txt"
    meta.write_text(
        f"aiZee Brain Backup\n"
        f"Created: {datetime.now().isoformat()}\n"
        f"Source:  {root}\n"
        f"Version: {(root / '.aizee-version').read_text(encoding='utf-8').strip() if (root / '.aizee-version').exists() else 'unknown'}\n",
        encoding="utf-8",
    )

    total_size = 0
    copied_count = 0

    # Backup directories
    for dirname in LEARNED_DIRS:
        src = root / dirname
        if not src.exists():
            print(f"  [SKIP] {dirname}/ — not found")
            continue

        size = _dir_size(src)
        total_size += size
        dst = backup_folder / dirname

        print(f"  [COPY] {dirname}/ ({_format_size(size)})... ", end="", flush=True)
        if _backup_item(src, dst):
            copied_count += 1
            print("OK")
        else:
            print("FAILED")

    # Backup files
    for filename in LEARNED_FILES:
        src = root / filename
        if not src.exists():
            print(f"  [SKIP] {filename} — not found")
            continue

        size = src.stat().st_size
        total_size += size
        dst = backup_folder / filename

        print(f"  [COPY] {filename} ({_format_size(size)})... ", end="", flush=True)
        if _backup_item(src, dst):
            copied_count += 1
            print("OK")
        else:
            print("FAILED")

    # Summary
    print()
    print("=" * 60)
    if copied_count > 0:
        print(f"  [DONE] Backup created: {backup_folder}")
        print(f"  Items: {copied_count} | Total size: {_format_size(total_size)}")
        print(f"  To restore: python scripts/restore_brain.py --from \"{backup_folder}\"")
    else:
        print(f"  [WARN] Nothing to backup. No learned data found in {root}")
        # Remove empty backup folder (including _backup_meta.txt)
        with contextlib.suppress(OSError):
            shutil.rmtree(backup_folder)
    print("=" * 60)

    return 0 if copied_count > 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="aiZee brain backup — save learned data")
    parser.add_argument("--root", default=None, help="aiZee root directory (default: auto-detect)")
    parser.add_argument("--dest", default=None, help="Backup destination folder (default: <root>/backups/)")
    args = parser.parse_args(argv)

    # Auto-detect root
    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent

    # Default destination: <root>/backups/
    dest = Path(args.dest) if args.dest else root / "backups"

    dest.mkdir(parents=True, exist_ok=True)
    return run_backup(root, dest)


if __name__ == "__main__":
    raise SystemExit(main())
