"""Tests for scripts/backup_brain.py and scripts/restore_brain.py.

Tests cover:
  - Backup creates timestamped folder with correct structure
  - Backup skips missing items gracefully
  - Restore overwrites existing data
  - Restore --list shows available backups
  - Round-trip: backup → restore preserves data
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_script(script_path: Path):
    """Dynamically load a script as a module."""
    spec = importlib.util.spec_from_file_location(script_path.stem, script_path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_fake_aizee(root: Path) -> None:
    """Create a fake aiZee root with learned data."""
    (root / "memory").mkdir(parents=True)
    (root / "memory" / "store.db").write_bytes(b"fake-memory-db-content")
    (root / "memory" / "index.json").write_text('{"v":1}', encoding="utf-8")

    (root / "state").mkdir(parents=True)
    (root / "state" / "budget.json").write_text('{"budget":100}', encoding="utf-8")

    (root / "brain").mkdir(parents=True)
    (root / "brain" / "patterns.json").write_text('{"p":[]}', encoding="utf-8")

    (root / "graphify-out").mkdir(parents=True)
    (root / "graphify-out" / "graph.json").write_text('{"n":0}', encoding="utf-8")

    (root / ".env").write_text("LINKEDIN_TOKEN=fake-token\n", encoding="utf-8")

    (root / ".aizee-version").write_text("5.0.0", encoding="utf-8")


SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"


class TestBackupBrain:
    """Tests for backup_brain.py."""

    def test_backup_creates_timestamped_folder(self, tmp_path: Path) -> None:
        """Backup creates a folder named aizee-backup-<date>-<time>."""
        root = tmp_path / "aizee"
        root.mkdir()
        _make_fake_aizee(root)
        dest = tmp_path / "backups"

        mod = _load_script(SCRIPTS / "backup_brain.py")
        rc = mod.run_backup(root, dest)

        assert rc == 0
        backups = list(dest.glob("aizee-backup-*"))
        assert len(backups) == 1
        backup = backups[0]
        assert (backup / "memory" / "store.db").exists()
        assert (backup / "memory" / "index.json").exists()
        assert (backup / "state" / "budget.json").exists()
        assert (backup / "brain" / "patterns.json").exists()
        assert (backup / "graphify-out" / "graph.json").exists()
        assert (backup / ".env").exists()
        assert (backup / "_backup_meta.txt").exists()

    def test_backup_skips_missing_items(self, tmp_path: Path) -> None:
        """Backup skips directories that don't exist without error."""
        root = tmp_path / "aizee"
        root.mkdir()
        (root / "memory").mkdir()
        (root / "memory" / "store.db").write_bytes(b"x")
        # No state/, brain/, graphify-out/, .env
        dest = tmp_path / "backups"

        mod = _load_script(SCRIPTS / "backup_brain.py")
        rc = mod.run_backup(root, dest)

        assert rc == 0
        backup = next(iter(dest.glob("aizee-backup-*")))
        assert (backup / "memory" / "store.db").exists()
        assert not (backup / "state").exists()
        assert not (backup / ".env").exists()

    def test_backup_empty_root_returns_error(self, tmp_path: Path) -> None:
        """Backup of empty root returns error code 1."""
        root = tmp_path / "empty"
        root.mkdir()
        dest = tmp_path / "backups"

        mod = _load_script(SCRIPTS / "backup_brain.py")
        rc = mod.run_backup(root, dest)

        assert rc == 1
        # Empty backup folder should be cleaned up
        backups = list(dest.glob("aizee-backup-*"))
        assert len(backups) == 0

    def test_backup_nonexistent_root_returns_error(self, tmp_path: Path) -> None:
        """Backup of nonexistent root returns error code 1."""
        root = tmp_path / "nonexistent"
        dest = tmp_path / "backups"

        mod = _load_script(SCRIPTS / "backup_brain.py")
        rc = mod.run_backup(root, dest)

        assert rc == 1


class TestRestoreBrain:
    """Tests for restore_brain.py."""

    def test_restore_overwrites_existing(self, tmp_path: Path) -> None:
        """Restore overwrites existing learned data."""
        # Create backup
        backup_root = tmp_path / "original"
        backup_root.mkdir()
        _make_fake_aizee(backup_root)
        dest = tmp_path / "backups"

        backup_mod = _load_script(SCRIPTS / "backup_brain.py")
        backup_mod.run_backup(backup_root, dest)
        backup_folder = next(iter(dest.glob("aizee-backup-*")))

        # Create target with different data
        target = tmp_path / "target"
        target.mkdir()
        (target / "memory").mkdir()
        (target / "memory" / "store.db").write_bytes(b"old-data")
        (target / ".aizee-version").write_text("5.0.0", encoding="utf-8")

        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        rc = restore_mod.run_restore(backup_folder, target, assume_yes=True)

        assert rc == 0
        # Data should be overwritten
        assert (target / "memory" / "store.db").read_bytes() == b"fake-memory-db-content"
        assert (target / "memory" / "index.json").exists()
        assert (target / "state" / "budget.json").exists()
        assert (target / ".env").exists()

    def test_restore_to_empty_target(self, tmp_path: Path) -> None:
        """Restore to a target with no existing learned data."""
        backup_root = tmp_path / "original"
        backup_root.mkdir()
        _make_fake_aizee(backup_root)
        dest = tmp_path / "backups"

        backup_mod = _load_script(SCRIPTS / "backup_brain.py")
        backup_mod.run_backup(backup_root, dest)
        backup_folder = next(iter(dest.glob("aizee-backup-*")))

        target = tmp_path / "target"
        target.mkdir()
        (target / ".aizee-version").write_text("5.0.0", encoding="utf-8")

        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        rc = restore_mod.run_restore(backup_folder, target, assume_yes=True)

        assert rc == 0
        assert (target / "memory" / "store.db").exists()
        assert (target / "brain" / "patterns.json").exists()

    def test_restore_nonexistent_backup_returns_error(self, tmp_path: Path) -> None:
        """Restore from nonexistent backup returns error."""
        target = tmp_path / "target"
        target.mkdir()

        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        rc = restore_mod.run_restore(tmp_path / "no-backup", target, assume_yes=True)

        assert rc == 1

    def test_restore_empty_backup_returns_error(self, tmp_path: Path) -> None:
        """Restore from empty backup folder returns error."""
        empty_backup = tmp_path / "empty-backup"
        empty_backup.mkdir()
        target = tmp_path / "target"
        target.mkdir()

        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        rc = restore_mod.run_restore(empty_backup, target, assume_yes=True)

        assert rc == 1

    def test_list_backups_shows_available(self, tmp_path: Path) -> None:
        """--list shows available backups sorted by date."""
        dest = tmp_path / "backups"
        dest.mkdir()

        # Create two backups
        for i in range(2):
            root = tmp_path / f"aizee-{i}"
            root.mkdir()
            (root / "memory").mkdir()
            (root / "memory" / "store.db").write_bytes(b"x")
            backup_mod = _load_script(SCRIPTS / "backup_brain.py")
            backup_mod.run_backup(root, dest)

        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        rc = restore_mod.list_backups(dest)

        assert rc == 0

    def test_list_backups_empty_returns_error(self, tmp_path: Path) -> None:
        """--list on empty dest returns error."""
        dest = tmp_path / "empty"
        dest.mkdir()

        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        rc = restore_mod.list_backups(dest)

        assert rc == 1


class TestBackupRestoreRoundTrip:
    """End-to-end: backup → wipe → restore → verify."""

    def test_roundtrip_preserves_all_data(self, tmp_path: Path) -> None:
        """Backup then restore preserves all learned data."""
        # Setup original
        original = tmp_path / "original"
        original.mkdir()
        _make_fake_aizee(original)

        original_memory = (original / "memory" / "store.db").read_bytes()
        original_env = (original / ".env").read_text(encoding="utf-8")
        original_state = (original / "state" / "budget.json").read_text(encoding="utf-8")

        # Backup
        dest = tmp_path / "backups"
        backup_mod = _load_script(SCRIPTS / "backup_brain.py")
        rc = backup_mod.run_backup(original, dest)
        assert rc == 0

        backup_folder = next(iter(dest.glob("aizee-backup-*")))

        # Wipe original learned data
        import shutil
        shutil.rmtree(original / "memory")
        shutil.rmtree(original / "state")
        shutil.rmtree(original / "brain")
        shutil.rmtree(original / "graphify-out")
        (original / ".env").unlink()

        # Restore
        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        rc = restore_mod.run_restore(backup_folder, original, assume_yes=True)
        assert rc == 0

        # Verify
        assert (original / "memory" / "store.db").read_bytes() == original_memory
        assert (original / ".env").read_text(encoding="utf-8") == original_env
        assert (original / "state" / "budget.json").read_text(encoding="utf-8") == original_state


class TestCheckpoint:
    """Tests for the restore checkpoint system."""

    def test_full_restore_creates_checkpoint(self, tmp_path: Path) -> None:
        """Full restore creates a checkpoint file in state/."""
        # Setup
        backup_root = tmp_path / "original"
        backup_root.mkdir()
        _make_fake_aizee(backup_root)
        dest = tmp_path / "backups"

        backup_mod = _load_script(SCRIPTS / "backup_brain.py")
        backup_mod.run_backup(backup_root, dest)
        backup_folder = next(iter(dest.glob("aizee-backup-*")))

        # Target
        target = tmp_path / "target"
        target.mkdir()
        (target / ".aizee-version").write_text("5.0.0", encoding="utf-8")

        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        rc = restore_mod.run_restore(backup_folder, target, assume_yes=True)
        assert rc == 0

        # Check checkpoint exists
        cp_path = target / "state" / "restore_checkpoint.json"
        assert cp_path.exists()
        import json
        cp = json.loads(cp_path.read_text(encoding="utf-8"))
        assert cp["mode"] == "full"
        assert cp["last_backup_folder"] == backup_folder.name
        assert "last_restore_timestamp" in cp

    def test_load_checkpoint_returns_empty_if_missing(self, tmp_path: Path) -> None:
        """_load_checkpoint returns empty dict if no checkpoint exists."""
        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        cp = restore_mod._load_checkpoint(tmp_path)
        assert cp == {}

    def test_save_and_load_checkpoint_roundtrip(self, tmp_path: Path) -> None:
        """_save_checkpoint then _load_checkpoint preserves data."""
        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        checkpoint = {
            "last_restore_timestamp": "2026-08-17-153045",
            "last_backup_folder": "aizee-backup-2026-08-17-153045",
            "restored_backups": ["aizee-backup-2026-08-17-153045"],
            "mode": "auto-merge",
        }
        restore_mod._save_checkpoint(tmp_path, checkpoint)
        loaded = restore_mod._load_checkpoint(tmp_path)
        assert loaded["last_restore_timestamp"] == "2026-08-17-153045"
        assert loaded["mode"] == "auto-merge"

    def test_find_backups_after_filters_by_timestamp(self, tmp_path: Path) -> None:
        """_find_backups_after returns only backups newer than checkpoint."""
        dest = tmp_path / "backups"
        dest.mkdir()
        # Create fake backup folders
        for ts in ["2026-08-10-100000", "2026-08-15-200000", "2026-08-20-300000"]:
            (dest / f"aizee-backup-{ts}").mkdir()

        restore_mod = _load_script(SCRIPTS / "restore_brain.py")

        # No checkpoint → all backups
        all_backups = restore_mod._find_backups_after(dest, "")
        assert len(all_backups) == 3

        # Checkpoint at 2026-08-15 → only 2026-08-20
        new_backups = restore_mod._find_backups_after(dest, "2026-08-15-200000")
        assert len(new_backups) == 1
        assert "2026-08-20-300000" in new_backups[0].name

    def test_extract_timestamp(self) -> None:
        """_extract_timestamp parses backup folder names correctly."""
        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        assert restore_mod._extract_timestamp("aizee-backup-2026-08-17-153045") == "2026-08-17-153045"
        assert restore_mod._extract_timestamp("random-folder") == ""
        assert restore_mod._extract_timestamp("aizee-backup-") == ""


class TestAutoMerge:
    """Tests for the --auto merge mode."""

    def test_auto_merge_no_checkpoint_processes_all(self, tmp_path: Path) -> None:
        """Auto-merge with no checkpoint processes all backups."""
        import sqlite3

        root = tmp_path / "aizee"
        root.mkdir()
        (root / "state").mkdir()  # Needed for checkpoint
        (root / ".aizee-version").write_text("5.0.0", encoding="utf-8")
        dest = tmp_path / "backups"

        backup_mod = _load_script(SCRIPTS / "backup_brain.py")

        # Create 2 backups with real SQLite DBs
        import time
        for i in range(2):
            if i > 0:
                time.sleep(1.1)  # Ensure different timestamps
            src = tmp_path / f"src-{i}"
            src.mkdir()
            (src / "memory").mkdir()
            db = src / "memory" / "store.db"
            with sqlite3.connect(str(db)) as conn:
                conn.execute("""
                    CREATE TABLE memories (
                        id TEXT PRIMARY KEY, kind TEXT, content TEXT, source TEXT,
                        meta TEXT, created_at TEXT, valid_from TEXT, valid_to TEXT
                    )
                """)
                conn.execute(
                    f"INSERT INTO memories VALUES ('m{i}', 'fact', 'content-{i}', 'src', NULL, '2026-01-0{i}', '2026-01-0{i}', NULL)"
                )
                conn.commit()
            (src / "state").mkdir()
            (src / "state" / "budget.json").write_text(f'{{"v":{i}}}', encoding="utf-8")
            backup_mod.run_backup(src, dest)

        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        rc = restore_mod.run_auto_restore(root, dest, assume_yes=True)
        assert rc == 0

        # Checkpoint should be updated
        import json
        cp = json.loads((root / "state" / "restore_checkpoint.json").read_text(encoding="utf-8"))
        assert cp["mode"] == "auto-merge"
        assert len(cp["restored_backups"]) == 2

        # Verify both memories were merged
        with sqlite3.connect(str(root / "memory" / "store.db")) as conn:
            count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            assert count == 2

    def test_auto_merge_skips_already_restored(self, tmp_path: Path) -> None:
        """Auto-merge with checkpoint skips already-restored backups."""
        import sqlite3

        root = tmp_path / "aizee"
        root.mkdir()
        (root / "state").mkdir()
        (root / ".aizee-version").write_text("5.0.0", encoding="utf-8")
        dest = tmp_path / "backups"

        backup_mod = _load_script(SCRIPTS / "backup_brain.py")

        # Create one backup with real SQLite DB
        src = tmp_path / "src"
        src.mkdir()
        (src / "memory").mkdir()
        db = src / "memory" / "store.db"
        with sqlite3.connect(str(db)) as conn:
            conn.execute("""
                CREATE TABLE memories (
                    id TEXT PRIMARY KEY, kind TEXT, content TEXT, source TEXT,
                    meta TEXT, created_at TEXT, valid_from TEXT, valid_to TEXT
                )
            """)
            conn.execute(
                "INSERT INTO memories VALUES ('m0', 'fact', 'content-0', 'src', NULL, '2026-01-01', '2026-01-01', NULL)"
            )
            conn.commit()
        backup_mod.run_backup(src, dest)

        restore_mod = _load_script(SCRIPTS / "restore_brain.py")

        # First auto-merge
        rc = restore_mod.run_auto_restore(root, dest, assume_yes=True)
        assert rc == 0

        # Second auto-merge — should find nothing new
        rc = restore_mod.run_auto_restore(root, dest, assume_yes=True)
        assert rc == 0  # Returns 0 with "already up to date" message

    def test_auto_merge_memory_sqlite_inserts_new(self, tmp_path: Path) -> None:
        """_merge_memory_sqlite inserts new memories from source."""
        import sqlite3

        # Create source DB with one memory
        source_db = tmp_path / "source.db"
        with sqlite3.connect(str(source_db)) as conn:
            conn.execute("""
                CREATE TABLE memories (
                    id TEXT PRIMARY KEY, kind TEXT, content TEXT, source TEXT,
                    meta TEXT, created_at TEXT, valid_from TEXT, valid_to TEXT
                )
            """)
            conn.execute(
                "INSERT INTO memories VALUES ('m1', 'fact', 'test', 'src', NULL, '2026-01-01', '2026-01-01', NULL)"
            )
            conn.commit()

        # Create target DB (empty, no schema)
        target_db = tmp_path / "target.db"

        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        stats = restore_mod._merge_memory_sqlite(source_db, target_db)

        assert stats["inserted"] == 1
        assert stats["updated"] == 0

        # Verify memory was inserted
        with sqlite3.connect(str(target_db)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            assert count == 1

    def test_auto_merge_memory_sqlite_updates_newer(self, tmp_path: Path) -> None:
        """_merge_memory_sqlite updates memory if source has newer timestamp."""
        import sqlite3

        # Create source DB with newer version of memory
        source_db = tmp_path / "source.db"
        with sqlite3.connect(str(source_db)) as conn:
            conn.execute("""
                CREATE TABLE memories (
                    id TEXT PRIMARY KEY, kind TEXT, content TEXT, source TEXT,
                    meta TEXT, created_at TEXT, valid_from TEXT, valid_to TEXT
                )
            """)
            conn.execute(
                "INSERT INTO memories VALUES ('m1', 'fact', 'updated-content', 'src', NULL, '2026-06-01', '2026-06-01', NULL)"
            )
            conn.commit()

        # Create target DB with older version
        target_db = tmp_path / "target.db"
        with sqlite3.connect(str(target_db)) as conn:
            conn.execute("""
                CREATE TABLE memories (
                    id TEXT PRIMARY KEY, kind TEXT, content TEXT, source TEXT,
                    meta TEXT, created_at TEXT, valid_from TEXT, valid_to TEXT
                )
            """)
            conn.execute(
                "INSERT INTO memories VALUES ('m1', 'fact', 'old-content', 'src', NULL, '2026-01-01', '2026-01-01', NULL)"
            )
            conn.commit()

        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        stats = restore_mod._merge_memory_sqlite(source_db, target_db)

        assert stats["updated"] == 1
        assert stats["inserted"] == 0

        # Verify content was updated
        with sqlite3.connect(str(target_db)) as conn:
            content = conn.execute("SELECT content FROM memories WHERE id='m1'").fetchone()[0]
            assert content == "updated-content"

    def test_auto_merge_memory_sqlite_skips_older(self, tmp_path: Path) -> None:
        """_merge_memory_sqlite skips memory if source has older timestamp."""
        import sqlite3

        # Source has OLDER version
        source_db = tmp_path / "source.db"
        with sqlite3.connect(str(source_db)) as conn:
            conn.execute("""
                CREATE TABLE memories (
                    id TEXT PRIMARY KEY, kind TEXT, content TEXT, source TEXT,
                    meta TEXT, created_at TEXT, valid_from TEXT, valid_to TEXT
                )
            """)
            conn.execute(
                "INSERT INTO memories VALUES ('m1', 'fact', 'old-content', 'src', NULL, '2026-01-01', '2026-01-01', NULL)"
            )
            conn.commit()

        # Target has NEWER version
        target_db = tmp_path / "target.db"
        with sqlite3.connect(str(target_db)) as conn:
            conn.execute("""
                CREATE TABLE memories (
                    id TEXT PRIMARY KEY, kind TEXT, content TEXT, source TEXT,
                    meta TEXT, created_at TEXT, valid_from TEXT, valid_to TEXT
                )
            """)
            conn.execute(
                "INSERT INTO memories VALUES ('m1', 'fact', 'newer-content', 'src', NULL, '2026-06-01', '2026-06-01', NULL)"
            )
            conn.commit()

        restore_mod = _load_script(SCRIPTS / "restore_brain.py")
        stats = restore_mod._merge_memory_sqlite(source_db, target_db)

        assert stats["skipped"] == 1
        assert stats["updated"] == 0

        # Verify content was NOT changed
        with sqlite3.connect(str(target_db)) as conn:
            content = conn.execute("SELECT content FROM memories WHERE id='m1'").fetchone()[0]
            assert content == "newer-content"
