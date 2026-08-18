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
    python scripts/backup_brain.py --schedule daily   # run backup every 24h (Ctrl+C to stop)
    python scripts/backup_brain.py --schedule hourly  # run backup every 1h (Ctrl+C to stop)
    python scripts/backup_brain.py --verify <path>    # verify backup integrity
"""

from __future__ import annotations

import argparse
import contextlib
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path

LEARNED_DIRS = ["memory", "state", "brain", "graphify-out"]
LEARNED_FILES = [".env"]

SCHEDULE_INTERVALS = {
    "hourly": 3600,
    "daily": 86400,
}


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


def verify_backup(backup_folder: Path) -> int:
    """Verify backup integrity. Returns exit code (0 = OK, 1 = issues found).

    Runs SQLite PRAGMA integrity_check on .db files and checks that all
    expected items exist in the backup folder.
    """
    print("=" * 60)
    print("  aiZee Brain Backup — Verify integrity")
    print("=" * 60)
    print()
    print(f"  Backup: {backup_folder}")
    print()

    if not backup_folder.exists():
        print(f"[ERROR] Backup folder not found: {backup_folder}")
        return 1

    issues = 0
    checked = 0

    # Verify expected directories and files exist
    for dirname in LEARNED_DIRS:
        dst = backup_folder / dirname
        if not dst.exists():
            print(f"  [MISSING] {dirname}/")
            issues += 1
        else:
            print(f"  [OK]      {dirname}/")
            checked += 1

    for filename in LEARNED_FILES:
        dst = backup_folder / filename
        if not dst.exists():
            print(f"  [MISSING] {filename}")
            issues += 1
        else:
            print(f"  [OK]      {filename}")
            checked += 1

    # Run SQLite integrity_check on all .db files in the backup
    print()
    print("  Checking SQLite databases...")
    db_files = list(backup_folder.rglob("*.db"))
    if not db_files:
        print("  [INFO] No .db files found in backup")
    for db_file in db_files:
        rel = db_file.relative_to(backup_folder)
        try:
            conn = sqlite3.connect(str(db_file))
            result = conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
            status = result[0] if result else "no result"
            if status == "ok":
                print(f"  [OK]      {rel}")
                checked += 1
            else:
                print(f"  [FAIL]    {rel}: {status}")
                issues += 1
        except sqlite3.DatabaseError as e:
            print(f"  [FAIL]    {rel}: {e}")
            issues += 1

    # Summary
    print()
    print("=" * 60)
    if issues == 0:
        print(f"  [PASS] Verification OK — {checked} items checked, no issues")
    else:
        print(f"  [FAIL] {issues} issue(s) found, {checked} items checked")
    print("=" * 60)

    return 0 if issues == 0 else 1


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
    parser.add_argument(
        "--schedule",
        choices=["daily", "hourly"],
        default=None,
        help="Run backups periodically (Ctrl+C to stop)",
    )
    parser.add_argument(
        "--verify",
        default=None,
        help="Verify backup integrity (pass backup folder path)",
    )
    args = parser.parse_args(argv)

    # Verify mode: check an existing backup and exit
    if args.verify is not None:
        return verify_backup(Path(args.verify))

    # Auto-detect root
    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent

    # Default destination: <root>/backups/
    dest = Path(args.dest) if args.dest else root / "backups"

    dest.mkdir(parents=True, exist_ok=True)

    # Schedule mode: run backups in a loop
    if args.schedule is not None:
        interval = SCHEDULE_INTERVALS[args.schedule]
        print(f"  Scheduled backup mode: every {args.schedule} ({interval}s)")
        print("  Press Ctrl+C to stop.")
        print()
        try:
            while True:
                run_backup(root, dest)
                print()
                print(f"  Next backup in {interval}s... (Ctrl+C to stop)")
                print()
                time.sleep(interval)
        except KeyboardInterrupt:
            print()
            print("  [STOP] Scheduled backups interrupted by user.")
            return 0

    return run_backup(root, dest)


if __name__ == "__main__":
    raise SystemExit(main())
