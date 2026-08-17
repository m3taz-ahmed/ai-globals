#!/usr/bin/env python3
"""aiZee brain restore — restore/merge learned data from backup folder(s).

Modes:
  --from <folder>     Full restore (overwrite) from a specific backup folder.
  --auto              Smart merge: read checkpoint, merge all backups newer
                      than the last restore. Memory is merged by timestamp
                      (INSERT OR REPLACE if source is newer). state/brain/.env
                      take the latest backup's version.
  --list              List available backups.
  --checkpoint        Show current restore checkpoint.

Checkpoint:
  state/restore_checkpoint.json tracks the last backup folder restored.
  Subsequent --auto runs only process backups NEWER than the checkpoint.

Usage:
    python scripts/restore_brain.py --from "<root>/backups/aizee-backup-2026-08-17-153045"
    python scripts/restore_brain.py --auto
    python scripts/restore_brain.py --auto --dest D:\backups
    python scripts/restore_brain.py --list
    python scripts/restore_brain.py --checkpoint
"""

from __future__ import annotations

import argparse
import contextlib
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

LEARNED_DIRS = ["memory", "state", "brain", "graphify-out"]
LEARNED_FILES = [".env"]

# Items that get MERGED (not overwritten) in --auto mode.
MERGE_DIRS = ["memory"]

# Items that get OVERWRITTEN with the latest backup's version in --auto mode.
OVERWRITE_DIRS = ["state", "brain", "graphify-out"]
OVERWRITE_FILES = [".env"]

CHECKPOINT_FILE = "restore_checkpoint.json"


def _format_size(bytes_val: int) -> str:
    """Format bytes as human-readable string."""
    if bytes_val < 1024:
        return f"{bytes_val}B"
    if bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f}KB"
    if bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.1f}MB"
    return f"{bytes_val / (1024 * 1024 * 1024):.2f}GB"


def _dir_size(path: Path) -> int:
    """Calculate total size of a directory in bytes."""
    total = 0
    if path.is_dir():
        for f in path.rglob("*"):
            if f.is_file():
                with contextlib.suppress(OSError):
                    total += f.stat().st_size
    return total


def _restore_item(src: Path, dst: Path) -> bool:
    """Copy a file or directory from backup to destination. Returns True if copied."""
    try:
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return True
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            return True
    except (OSError, shutil.Error) as e:
        print(f"    [WARN] Could not restore {src.name}: {e}")
    return False


def _extract_timestamp(folder_name: str) -> str:
    """Extract timestamp from backup folder name.

    'aizee-backup-2026-08-17-153045' → '2026-08-17-153045'
    Returns empty string if no timestamp found.
    """
    prefix = "aizee-backup-"
    if folder_name.startswith(prefix):
        return folder_name[len(prefix):]
    return ""


def _load_checkpoint(root: Path) -> dict[str, object]:
    """Load the restore checkpoint from state/restore_checkpoint.json.

    Returns empty dict if checkpoint doesn't exist.
    """
    cp_path = root / "state" / CHECKPOINT_FILE
    if not cp_path.exists():
        return {}
    try:
        return json.loads(cp_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_checkpoint(root: Path, checkpoint: dict[str, object]) -> None:
    """Save the restore checkpoint to state/restore_checkpoint.json."""
    cp_dir = root / "state"
    cp_dir.mkdir(parents=True, exist_ok=True)
    cp_path = cp_dir / CHECKPOINT_FILE
    cp_path.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")


def _show_checkpoint(root: Path) -> int:
    """Print the current restore checkpoint."""
    cp = _load_checkpoint(root)
    if not cp:
        print(f"No restore checkpoint found in {root}/state/")
        return 1
    print(f"\nRestore checkpoint ({root}/state/{CHECKPOINT_FILE}):\n")
    print(json.dumps(cp, indent=2))
    return 0


def _find_backups_after(dest: Path, last_timestamp: str) -> list[Path]:
    """Find backup folders newer than the given timestamp.

    Returns sorted list (oldest first).
    """
    backups = []
    for b in dest.glob("aizee-backup-*"):
        ts = _extract_timestamp(b.name)
        if not ts:
            continue
        if not last_timestamp or ts > last_timestamp:
            backups.append(b)
    backups.sort(key=lambda p: _extract_timestamp(p.name))
    return backups


def _merge_memory_sqlite(source_db: Path, target_db: Path) -> dict[str, int]:
    """Merge memories from source SQLite DB into target DB.

    Strategy: for each memory in source, if ID doesn't exist in target → INSERT.
    If ID exists and source created_at > target created_at → UPDATE.

    Also merges relations table.

    Returns dict with counts: {inserted, updated, skipped, relations}.
    """
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "relations": 0}

    if not source_db.exists():
        return stats

    # Ensure target DB exists with schema
    target_db.parent.mkdir(parents=True, exist_ok=True)

    # Try to open source DB — skip if not a valid SQLite file
    try:
        src_conn = sqlite3.connect(str(source_db))
        src_conn.row_factory = sqlite3.Row
        # Test that it's a real SQLite DB
        src_conn.execute("SELECT 1").fetchone()
    except sqlite3.DatabaseError:
        # Source is not a valid SQLite DB — skip merge, just copy the file
        shutil.copy2(source_db, target_db)
        return stats

    with sqlite3.connect(str(target_db)) as tgt:
        tgt.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                meta TEXT,
                created_at TEXT NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT
            )
        """)
        tgt.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        with src_conn as src:
            # Merge memories
            try:
                rows = src.execute(
                    "SELECT id, kind, content, source, meta, created_at, valid_from, valid_to FROM memories"
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []

            for row in rows:
                mem_id = row["id"]
                # Check if exists in target
                existing = tgt.execute(
                    "SELECT created_at FROM memories WHERE id = ?", (mem_id,)
                ).fetchone()

                if existing is None:
                    # INSERT
                    tgt.execute(
                        "INSERT OR REPLACE INTO memories (id, kind, content, source, meta, created_at, valid_from, valid_to) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (row["id"], row["kind"], row["content"], row["source"],
                         row["meta"], row["created_at"], row["valid_from"], row["valid_to"]),
                    )
                    stats["inserted"] += 1
                else:
                    # Compare timestamps — update if source is newer
                    if row["created_at"] > existing[0]:
                        tgt.execute(
                            "UPDATE memories SET kind=?, content=?, source=?, meta=?, created_at=?, valid_from=?, valid_to=? "
                            "WHERE id=?",
                            (row["kind"], row["content"], row["source"], row["meta"],
                             row["created_at"], row["valid_from"], row["valid_to"], mem_id),
                        )
                        stats["updated"] += 1
                    else:
                        stats["skipped"] += 1

            # Merge relations
            try:
                rel_rows = src.execute(
                    "SELECT id, source_id, target_id, relation, created_at FROM relations"
                ).fetchall()
            except sqlite3.OperationalError:
                rel_rows = []

            for row in rel_rows:
                tgt.execute(
                    "INSERT OR REPLACE INTO relations (id, source_id, target_id, relation, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (row["id"], row["source_id"], row["target_id"],
                     row["relation"], row["created_at"]),
                )
                stats["relations"] += 1

        tgt.commit()

    return stats


def _merge_memory_dir(source_dir: Path, target_dir: Path) -> dict[str, int]:
    """Merge memory directory: SQLite DB merge + copy other files."""
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "relations": 0}

    target_dir.mkdir(parents=True, exist_ok=True)

    # Merge SQLite DBs
    source_db = source_dir / "store.db"
    target_db = target_dir / "store.db"

    if source_db.exists():
        stats = _merge_memory_sqlite(source_db, target_db)

    # Copy non-DB files (index.json, etc.) — overwrite with latest
    for f in source_dir.iterdir():
        if f.is_file() and f.name != "store.db":
            shutil.copy2(f, target_dir / f.name)

    return stats


def list_backups(dest: Path) -> int:
    """List available backups in the destination folder."""
    backups = sorted(dest.glob("aizee-backup-*"), reverse=True)
    if not backups:
        print(f"No backups found in {dest}")
        return 1

    print(f"\nAvailable backups in {dest}:\n")
    print(f"{'#':<4} {'Folder':<40} {'Size':>10}")
    print("-" * 56)
    for i, b in enumerate(backups, 1):
        size = _dir_size(b)
        print(f"{i:<4} {b.name:<40} {_format_size(size):>10}")
    print(f"\nTo restore: python scripts/restore_brain.py --from \"{backups[0]}\"")
    print("To auto-merge: python scripts/restore_brain.py --auto")
    return 0


def run_restore(backup_folder: Path, root: Path, assume_yes: bool = False) -> int:
    """Full restore (overwrite) from a specific backup folder. Returns exit code."""
    print("=" * 60)
    print("  aiZee Brain Restore — Full restore (overwrite)")
    print("=" * 60)
    print()
    print(f"  Backup: {backup_folder}")
    print(f"  Target: {root}")
    print()

    if not backup_folder.exists():
        print(f"[ERROR] Backup folder not found: {backup_folder}")
        return 1

    if not root.exists():
        print("[ERROR] Target aiZee root not found. Install aiZee first, then restore.")
        return 1

    # Check what's in the backup
    items_found: list[str] = []
    for dirname in LEARNED_DIRS:
        if (backup_folder / dirname).exists():
            items_found.append(f"{dirname}/")
    for filename in LEARNED_FILES:
        if (backup_folder / filename).exists():
            items_found.append(filename)

    if not items_found:
        print("[ERROR] No learned data found in backup folder.")
        return 1

    print(f"  Items to restore: {', '.join(items_found)}")
    print()

    # Warn about overwrite
    existing: list[str] = []
    for dirname in LEARNED_DIRS:
        if (root / dirname).exists():
            existing.append(f"{dirname}/")
    for filename in LEARNED_FILES:
        if (root / filename).exists():
            existing.append(filename)

    if existing:
        print("  [WARN] These items already exist in target and will be OVERWRITTEN:")
        for e in existing:
            print(f"    - {e}")
        print()

    if not assume_yes:
        try:
            answer = input("  Proceed with restore? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled.")
            return 1
        if answer != "y":
            print("  Cancelled.")
            return 1

    # Restore
    print("\n  Restoring...")
    restored_count = 0

    for dirname in LEARNED_DIRS:
        src = backup_folder / dirname
        if not src.exists():
            continue
        dst = root / dirname
        size = _dir_size(src)
        print(f"    [RESTORE] {dirname}/ ({_format_size(size)})... ", end="", flush=True)
        if _restore_item(src, dst):
            restored_count += 1
            print("OK")
        else:
            print("FAILED")

    for filename in LEARNED_FILES:
        src = backup_folder / filename
        if not src.exists():
            continue
        dst = root / filename
        size = src.stat().st_size
        print(f"    [RESTORE] {filename} ({_format_size(size)})... ", end="", flush=True)
        if _restore_item(src, dst):
            restored_count += 1
            print("OK")
        else:
            print("FAILED")

    # Update checkpoint
    ts = _extract_timestamp(backup_folder.name)
    if ts:
        checkpoint: dict[str, object] = {
            "last_restore_timestamp": ts,
            "last_backup_folder": backup_folder.name,
            "restored_backups": [backup_folder.name],
            "last_restore_at": datetime.now().isoformat(),
            "mode": "full",
        }
        _save_checkpoint(root, checkpoint)

    # Summary
    print()
    print("=" * 60)
    if restored_count > 0:
        print(f"  [DONE] Restore complete. {restored_count} item(s) restored to {root}")
        print("  Run 'aizee memory ingest' to refresh the search index.")
    else:
        print("  [ERROR] Nothing was restored.")
    print("=" * 60)

    return 0 if restored_count > 0 else 1


def run_auto_restore(root: Path, dest: Path, assume_yes: bool = False) -> int:
    """Smart merge: read checkpoint, merge all backups newer than last restore.

    - memory/: SQLite merge by timestamp (INSERT or UPDATE if newer).
    - state/brain/graphify-out/.env: overwrite with latest backup's version.
    - Updates checkpoint after merge.
    """
    print("=" * 60)
    print("  aiZee Brain Auto-Restore — Smart merge from checkpoint")
    print("=" * 60)
    print()

    if not root.exists():
        print("[ERROR] Target aiZee root not found. Install aiZee first.")
        return 1

    if not dest.exists():
        print(f"[ERROR] Backup destination not found: {dest}")
        return 1

    # Load checkpoint
    checkpoint = _load_checkpoint(root)
    last_ts = str(checkpoint.get("last_restore_timestamp", ""))
    raw_history = checkpoint.get("restored_backups", [])
    restored_history: list[str] = list(raw_history) if isinstance(raw_history, list) else []

    if last_ts:
        print(f"  Last restore: {last_ts} ({checkpoint.get('last_backup_folder', '?')})")
    else:
        print("  No previous restore checkpoint found. Will process ALL backups.")

    # Find backups newer than checkpoint
    new_backups = _find_backups_after(dest, last_ts)

    if not new_backups:
        print("\n  [OK] No new backups to merge. Already up to date.")
        print(f"  Last checkpoint: {last_ts or '(none)'}")
        return 0

    print(f"\n  Found {len(new_backups)} new backup(s) to merge:")
    for b in new_backups:
        size = _dir_size(b)
        print(f"    - {b.name} ({_format_size(size)})")
    print()

    if not assume_yes:
        try:
            answer = input("  Proceed with auto-merge? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled.")
            return 1
        if answer != "y":
            print("  Cancelled.")
            return 1

    # Process each backup (oldest → newest)
    total_inserted = 0
    total_updated = 0
    total_skipped = 0
    total_relations = 0
    merged_count = 0

    for backup in new_backups:
        print(f"\n  Processing {backup.name}...")

        # 1. Merge memory (SQLite merge by timestamp)
        src_memory = backup / "memory"
        tgt_memory = root / "memory"
        if src_memory.exists():
            print("    [MERGE] memory/... ", end="", flush=True)
            stats = _merge_memory_dir(src_memory, tgt_memory)
            total_inserted += stats["inserted"]
            total_updated += stats["updated"]
            total_skipped += stats["skipped"]
            total_relations += stats["relations"]
            print(f"inserted={stats['inserted']}, updated={stats['updated']}, skipped={stats['skipped']}, relations={stats['relations']}")
        else:
            print("    [SKIP] memory/ — not in backup")

        # 2. Overwrite state/brain/graphify-out/.env with latest backup
        # (only from the LAST backup in the list — newest wins)
        if backup == new_backups[-1]:
            for dirname in OVERWRITE_DIRS:
                src = backup / dirname
                if src.exists():
                    dst = root / dirname
                    size = _dir_size(src)
                    print(f"    [OVERWRITE] {dirname}/ ({_format_size(size)})... ", end="", flush=True)
                    if _restore_item(src, dst):
                        print("OK")
                    else:
                        print("FAILED")

            for filename in OVERWRITE_FILES:
                src = backup / filename
                if src.exists():
                    dst = root / filename
                    print(f"    [OVERWRITE] {filename}... ", end="", flush=True)
                    if _restore_item(src, dst):
                        print("OK")
                    else:
                        print("FAILED")

        merged_count += 1
        restored_history.append(backup.name)

    # Update checkpoint with the newest backup
    newest_ts = _extract_timestamp(new_backups[-1].name)
    new_checkpoint = {
        "last_restore_timestamp": newest_ts,
        "last_backup_folder": new_backups[-1].name,
        "restored_backups": restored_history,
        "last_restore_at": datetime.now().isoformat(),
        "mode": "auto-merge",
        "total_inserted": total_inserted,
        "total_updated": total_updated,
        "total_relations": total_relations,
    }
    _save_checkpoint(root, new_checkpoint)

    # Summary
    print()
    print("=" * 60)
    print(f"  [DONE] Auto-merge complete. {merged_count} backup(s) processed.")
    print(f"  Memory:  +{total_inserted} new, ~{total_updated} updated, {total_skipped} skipped, +{total_relations} relations")
    print(f"  Checkpoint updated: {newest_ts}")
    print("  Run 'aizee memory ingest' to refresh the search index.")
    print("=" * 60)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="aiZee brain restore — restore/merge learned data from backup"
    )
    parser.add_argument("--from", dest="backup_folder", default=None,
                        help="Backup folder to restore from (full overwrite mode)")
    parser.add_argument("--auto", action="store_true",
                        help="Smart merge: read checkpoint, merge all newer backups")
    parser.add_argument("--root", default=None, help="aiZee root directory (default: auto-detect)")
    parser.add_argument("--dest", default=None, help="Backup destination folder (default: <root>/backups/)")
    parser.add_argument("--list", action="store_true", help="List available backups")
    parser.add_argument("--checkpoint", action="store_true", help="Show current restore checkpoint")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    args = parser.parse_args(argv)

    # Auto-detect root
    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent

    # Default backup destination: <root>/backups/
    dest = Path(args.dest) if args.dest else root / "backups"

    # Checkpoint mode
    if args.checkpoint:
        return _show_checkpoint(root)

    # List mode
    if args.list:
        return list_backups(dest)

    # Auto-merge mode
    if args.auto:
        return run_auto_restore(root, dest, assume_yes=args.yes)

    # Full restore mode — require --from
    if not args.backup_folder:
        parser.error("--from is required (or use --auto / --list / --checkpoint)")

    backup_folder = Path(args.backup_folder)
    return run_restore(backup_folder, root, assume_yes=args.yes)


if __name__ == "__main__":
    raise SystemExit(main())
