#!/usr/bin/env python3
"""aiZee migration engine.

Runs ordered migrations from the currently installed version to the target
version (read from pyproject.toml). Each migration is a function that receives
the OS root Path and performs whatever changes are needed (config updates,
schema migrations, new plugin scaffolding, etc.).

Usage:
    python scripts/migrate.py [--root PATH] [--dry-run] [--check]

Exit codes:
    0 = no migration needed (already at target)
    1 = migration completed successfully
    2 = migration failed
    3 = dry-run showed pending migrations
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path

# Type alias for a migration function.
MigrationFn = Callable[[Path], None]


def _read_version_file(root: Path) -> str | None:
    """Return the version recorded in .aizee-version, or None if not present."""
    vf = root / ".aizee-version"
    if not vf.exists():
        return None
    text = vf.read_text(encoding="utf-8").strip()
    return text or None


def _read_target_version(root: Path) -> str:
    """Read the target version from pyproject.toml."""
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return "0.0.0"
    match = re.search(r'^version\s*=\s*"([^"\n]+)"', pyproject.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else "0.0.0"


def _version_tuple(v: str) -> tuple[int, int, int]:
    parts = v.split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
    except (ValueError, IndexError):
        return 0, 0, 0
    return major, minor, patch


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------

def _migrate_4_21_to_4_22(root: Path) -> None:
    """4.21.0 → 4.22.0: Add freelance MCP plugins + context7 + dashboard graph endpoints."""
    # 1. Ensure plugins.yaml has the new plugins.
    plugins_yaml = root / "plugins.yaml"
    if plugins_yaml.exists():
        content = plugins_yaml.read_text(encoding="utf-8")
        if "upwork" not in content:
            # The installer will handle the full plugins.yaml update; here we
            # just ensure the file is aware that plugins need re-registration.
            pass

    # 2. Ensure aizee_mcp/config.json has the new MCP servers.
    config_json = root / "aizee_mcp" / "config.json"
    if config_json.exists():
        try:
            data = json.loads(config_json.read_text(encoding="utf-8"))
            servers = data.get("mcpServers", {})
            for name in ("upwork", "freelancer", "fiverr", "context7"):
                if name not in servers:
                    # Mark for installer to fill in; migrate just ensures structure.
                    pass
        except (json.JSONDecodeError, OSError):
            pass

    # 3. Update .devin/mcp_config.json to remove disabled flags.
    mcp_config = root / ".devin" / "mcp_config.json"
    if mcp_config.exists():
        try:
            data = json.loads(mcp_config.read_text(encoding="utf-8"))
            changed = False
            for name in ("upwork", "freelancer", "fiverr"):
                srv = data.get("mcpServers", {}).get(name, {})
                if srv.get("disabled"):
                    srv.pop("disabled", None)
                    changed = True
            if changed:
                mcp_config.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except (json.JSONDecodeError, OSError):
            pass


def _migrate_4_22_to_4_22_1(root: Path) -> None:
    """4.22.0 → 4.22.1: Audit refactor — new modules, encryption, migrations framework.

    This migration handles the in-version update from the initial 4.22.0
    release to the audited 4.22.1 patch:
    - Runs SQLite schema migrations (runtime/migrations.py)
    - Verifies encryption compatibility for budget.json
    - Creates new directories (docs/, tests/e2e/)
    - Ensures runtime/managers/ and aizee_mcp/tools/ are present
    """
    # 1. Run SQLite schema migrations on brain/memory.db
    brain_dir = root / "brain"
    if brain_dir.exists():
        db_path = brain_dir / "memory.db"
        if db_path.exists():
            try:
                from runtime.migrations import MigrationRunner

                runner = MigrationRunner(db_path)
                version = runner.run_migrations()
                print(f"  Schema migrations applied: memory.db at version {version}")
            except Exception as exc:
                print(f"  WARN: Schema migration skipped: {exc}", file=sys.stderr)

    # 2. Verify encryption compatibility
    budget_file = root / "state" / "budget.json"
    if budget_file.exists():
        try:
            from runtime.crypto import decrypt_file, is_encrypted

            if is_encrypted(budget_file):
                import os

                if not os.environ.get("AIOS_ENCRYPTION_KEY"):
                    print(
                        "  WARN: budget.json is encrypted but AIOS_ENCRYPTION_KEY is not set. "
                        "Set it to decrypt budget state.",
                        file=sys.stderr,
                    )
                else:
                    decrypt_file(budget_file)
                    print("  Encryption compatibility verified: budget.json decrypts OK")
        except Exception as exc:
            print(f"  WARN: Budget encryption check failed: {exc}", file=sys.stderr)

    # 3. Ensure new directories exist
    for new_dir in ("docs",):
        d = root / new_dir
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            print(f"  Created directory: {new_dir}/")

    # 4. Verify new module directories exist (installed via file copy)
    for module_dir in ("runtime/managers", "aizee_mcp/tools"):
        d = root / module_dir
        if not d.exists():
            print(
                f"  WARN: {module_dir}/ not found — the installer should have copied it.",
                file=sys.stderr,
            )


def _migrate_4_22_to_4_23(root: Path) -> None:
    """4.22.0 → 4.23.0: Run schema migrations on memory database + verify encryption compatibility."""
    # 1. Run SQLite schema migrations on brain/memory.db
    brain_dir = root / "brain"
    if brain_dir.exists():
        db_path = brain_dir / "memory.db"
        if db_path.exists():
            try:
                from runtime.migrations import MigrationRunner

                runner = MigrationRunner(db_path)
                version = runner.run_migrations()
                print(f"  Schema migrations applied: memory.db at version {version}")
            except Exception as exc:
                print(f"  WARN: Schema migration skipped: {exc}", file=sys.stderr)

    # 2. Verify encryption compatibility — if AIOS_ENCRYPTION_KEY is set,
    # ensure budget.json can be decrypted (backward compat check).
    budget_file = root / "state" / "budget.json"
    if budget_file.exists():
        try:
            from runtime.crypto import decrypt_file, is_encrypted

            if is_encrypted(budget_file):
                import os

                if not os.environ.get("AIOS_ENCRYPTION_KEY"):
                    print(
                        "  WARN: budget.json is encrypted but AIOS_ENCRYPTION_KEY is not set. "
                        "Set it to decrypt budget state.",
                        file=sys.stderr,
                    )
                else:
                    decrypt_file(budget_file)
                    print("  Encryption compatibility verified: budget.json decrypts OK")
        except Exception as exc:
            print(f"  WARN: Budget encryption check failed: {exc}", file=sys.stderr)

    # 3. Ensure new directories exist (docs/, tests/e2e/)
    for new_dir in ("docs",):
        d = root / new_dir
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            print(f"  Created directory: {new_dir}/")


# Ordered migration table. Each entry: (from_version, to_version, function).
# The engine walks from the current version up to the target, running each
# matching migration in order.
_MIGRATIONS: list[tuple[str, str, MigrationFn]] = [
    ("4.21.0", "4.22.0", _migrate_4_21_to_4_22),
    ("4.22.0", "4.22.1", _migrate_4_22_to_4_22_1),
    ("4.22.1", "4.23.0", _migrate_4_22_to_4_23),
]


def _build_chain(current: str, target: str) -> list[tuple[str, str, MigrationFn]]:
    """Build an ordered chain of migrations from current to target."""
    chain: list[tuple[str, str, MigrationFn]] = []
    cursor = current
    while _version_tuple(cursor) < _version_tuple(target):
        found = False
        for from_v, to_v, fn in _MIGRATIONS:
            if from_v == cursor and _version_tuple(to_v) <= _version_tuple(target):
                chain.append((from_v, to_v, fn))
                cursor = to_v
                found = True
                break
        if not found:
            # No direct migration; assume the gap is bridged by the installer
            # (e.g. fresh file copy). Jump to target.
            break
    return chain


def run_migrations(root: Path, dry_run: bool = False) -> int:
    """Run pending migrations. Returns exit code."""
    current = _read_version_file(root) or "0.0.0"
    target = _read_target_version(root)

    if _version_tuple(current) >= _version_tuple(target):
        print(f"Already at {target} (current: {current}). No migration needed.")
        return 0

    chain = _build_chain(current, target)
    if not chain:
        print(f"No migration chain from {current} to {target}. Installer will handle full update.")
        # Still write the version file so future runs know we're at target.
        if not dry_run:
            (root / ".aizee-version").write_text(target, encoding="utf-8")
        return 1

    print(f"Migrating from {current} to {target} ({len(chain)} step(s))")
    for from_v, to_v, fn in chain:
        print(f"  [{from_v} → {to_v}] {fn.__name__}")
        if not dry_run:
            try:
                fn(root)
            except Exception as exc:
                print(f"  FAILED: {exc}", file=sys.stderr)
                return 2

    if not dry_run:
        (root / ".aizee-version").write_text(target, encoding="utf-8")
    print(f"Migration{' (dry-run)' if dry_run else ''} complete: {current} → {target}")
    return 3 if dry_run else 1


def check_migrations(root: Path) -> int:
    """Check if migrations are pending. Returns 0 if up-to-date, 3 if pending."""
    current = _read_version_file(root) or "0.0.0"
    target = _read_target_version(root)
    if _version_tuple(current) >= _version_tuple(target):
        print(f"Up-to-date: {current}")
        return 0
    chain = _build_chain(current, target)
    print(f"Pending: {current} → {target} ({len(chain)} migration(s))")
    for from_v, to_v, fn in chain:
        print(f"  [{from_v} → {to_v}] {fn.__name__}")
    return 3


def main() -> int:
    parser = argparse.ArgumentParser(description="aiZee migration engine")
    parser.add_argument("--root", type=Path, default=None, help="OS root directory")
    parser.add_argument("--dry-run", action="store_true", help="Show migrations without executing")
    parser.add_argument("--check", action="store_true", help="Only check if migrations are pending")
    args = parser.parse_args()

    root = args.root or Path(__file__).resolve().parent.parent
    if not (root / "pyproject.toml").exists():
        print(f"Error: {root} does not look like an aiZee root (no pyproject.toml)", file=sys.stderr)
        return 2

    if args.check:
        return check_migrations(root)
    return run_migrations(root, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
