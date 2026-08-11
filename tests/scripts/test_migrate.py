#!/usr/bin/env python3
"""Tests for scripts/migrate.py."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

# Path to the migrate.py script.
_MIGRATE = Path(__file__).resolve().parent.parent.parent / "scripts" / "migrate.py"


def _load_migrate_module():
    """Load scripts/migrate.py as a module (it's not in a package)."""
    spec = importlib.util.spec_from_file_location("migrate_module", _MIGRATE)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_migrate(root: Path, *args: str) -> tuple[int, str]:
    """Run migrate.py with args and return (exit_code, stdout)."""
    result = subprocess.run(
        [sys.executable, str(_MIGRATE), "--root", str(root), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout + result.stderr


def _write_pyproject(root: Path, version: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nversion = "{version}"\n', encoding="utf-8"
    )


def _write_version_file(root: Path, version: str) -> None:
    (root / ".aios-version").write_text(version, encoding="utf-8")


def test_migrate_check_up_to_date(tmp_path: Path):
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.22.0")
    code, output = _run_migrate(tmp_path, "--check")
    assert code == 0
    assert "Up-to-date" in output


def test_migrate_check_pending(tmp_path: Path):
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.21.0")
    code, output = _run_migrate(tmp_path, "--check")
    assert code == 3
    assert "Pending" in output
    assert "4.21.0" in output
    assert "4.22.0" in output


def test_migrate_no_version_file_treats_as_zero(tmp_path: Path):
    _write_pyproject(tmp_path, "4.22.0")
    # No .aios-version file
    code, output = _run_migrate(tmp_path, "--check")
    assert code == 3
    assert "0.0.0" in output or "Pending" in output


def test_migrate_dry_run_does_not_write_version(tmp_path: Path):
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.21.0")
    code, output = _run_migrate(tmp_path, "--dry-run")
    assert code == 3
    # Version file should still say 4.21.0
    assert (tmp_path / ".aios-version").read_text(encoding="utf-8").strip() == "4.21.0"


def test_migrate_run_writes_target_version(tmp_path: Path):
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.21.0")
    code, output = _run_migrate(tmp_path)
    # Migration should complete (exit 1 = migrated successfully)
    assert code in (1, 0)
    # Version file should now say 4.22.0
    assert (tmp_path / ".aios-version").read_text(encoding="utf-8").strip() == "4.22.0"


def test_migrate_already_at_target_exits_zero(tmp_path: Path):
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.22.0")
    code, output = _run_migrate(tmp_path)
    assert code == 0
    assert "No migration needed" in output


def test_migrate_no_pyproject_returns_error(tmp_path: Path):
    # No pyproject.toml in root
    code, output = _run_migrate(tmp_path, "--check")
    assert code == 2
    assert "does not look like" in output


def test_migrate_future_version_jumps_directly(tmp_path: Path):
    """If current is 4.22.0 and target is 5.0.0 (no migration chain), jump."""
    _write_pyproject(tmp_path, "5.0.0")
    _write_version_file(tmp_path, "4.22.0")
    code, output = _run_migrate(tmp_path)
    # No chain exists from 4.22 → 5.0, so it jumps and writes version
    assert code in (0, 1)
    assert (tmp_path / ".aios-version").read_text(encoding="utf-8").strip() == "5.0.0"


def test_migrate_version_tuple_ordering():
    """Test that version comparison works correctly."""
    mod = _load_migrate_module()
    assert mod._version_tuple("4.22.0") == (4, 22, 0)
    assert mod._version_tuple("4.22") == (4, 22, 0)
    assert mod._version_tuple("5.0") == (5, 0, 0)
    assert mod._version_tuple("4.22.0") < mod._version_tuple("4.23.0")
    assert mod._version_tuple("4.22.0") < mod._version_tuple("5.0.0")
    assert mod._version_tuple("4.22.10") > mod._version_tuple("4.22.9")


def test_migrate_build_chain_finds_path():
    """Test that the migration chain builder finds ordered migrations."""
    mod = _load_migrate_module()

    # 4.21 → 4.22 should find one migration
    chain = mod._build_chain("4.21.0", "4.22.0")
    assert len(chain) == 1
    assert chain[0][0] == "4.21.0"
    assert chain[0][1] == "4.22.0"

    # 4.22 → 4.23 should find two migrations (4.22→4.22.1→4.23)
    chain = mod._build_chain("4.22.0", "4.23.0")
    assert len(chain) == 2

    # 4.21 → 4.23 should find three migrations
    chain = mod._build_chain("4.21.0", "4.23.0")
    assert len(chain) == 3


def test_migrate_build_chain_no_path():
    """Test that chain builder returns empty when no migration exists."""
    mod = _load_migrate_module()
    chain = mod._build_chain("4.23.0", "5.0.0")
    assert len(chain) == 0


def test_migrate_4_21_to_4_22_removes_disabled_flag(tmp_path: Path):
    """Test that the 4.21→4.22 migration removes disabled flags from MCP config."""
    mod = _load_migrate_module()
    import json

    devin_dir = tmp_path / ".devin"
    devin_dir.mkdir(parents=True)
    config = {
        "mcpServers": {
            "upwork": {"command": "npx", "args": ["-y", "@furkankoykiran/upwork-mcp"], "disabled": True},
            "fiverr": {"command": "uvx", "args": ["fiverr-mcp-server"], "disabled": True},
        }
    }
    (devin_dir / "mcp_config.json").write_text(json.dumps(config), encoding="utf-8")

    mod._migrate_4_21_to_4_22(tmp_path)

    updated = json.loads((devin_dir / "mcp_config.json").read_text(encoding="utf-8"))
    assert "disabled" not in updated["mcpServers"]["upwork"]
    assert "disabled" not in updated["mcpServers"]["fiverr"]


def test_migrate_4_22_to_4_23_is_noop(tmp_path: Path):
    """Test that the 4.22→4.23 migration is a no-op (placeholder)."""
    mod = _load_migrate_module()
    mod._migrate_4_22_to_4_23(tmp_path)
