#!/usr/bin/env python3
"""Tests for scripts/migrate.py."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    (root / ".aizee-version").write_text(version, encoding="utf-8")


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
    # No .aizee-version file
    code, output = _run_migrate(tmp_path, "--check")
    assert code == 3
    assert "0.0.0" in output or "Pending" in output


def test_migrate_dry_run_does_not_write_version(tmp_path: Path):
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.21.0")
    code, _output = _run_migrate(tmp_path, "--dry-run")
    assert code == 3
    # Version file should still say 4.21.0
    assert (tmp_path / ".aizee-version").read_text(encoding="utf-8").strip() == "4.21.0"


def test_migrate_run_writes_target_version(tmp_path: Path):
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.21.0")
    code, _output = _run_migrate(tmp_path)
    # Migration should complete (exit 1 = migrated successfully)
    assert code in (1, 0)
    # Version file should now say 4.22.0
    assert (tmp_path / ".aizee-version").read_text(encoding="utf-8").strip() == "4.22.0"


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
    code, _output = _run_migrate(tmp_path)
    # No chain exists from 4.22 → 5.0, so it jumps and writes version
    assert code in (0, 1)
    assert (tmp_path / ".aizee-version").read_text(encoding="utf-8").strip() == "5.0.0"


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


# ---------------------------------------------------------------------------
# _read_version_file edge cases (lines 34-38)
# ---------------------------------------------------------------------------

def test_read_version_file_missing(tmp_path: Path):
    """Line 35-36: returns None when .aizee-version doesn't exist."""
    mod = _load_migrate_module()
    assert mod._read_version_file(tmp_path) is None


def test_read_version_file_empty(tmp_path: Path):
    """Line 38: returns None when .aizee-version is empty."""
    mod = _load_migrate_module()
    _write_version_file(tmp_path, "")
    assert mod._read_version_file(tmp_path) is None


def test_read_version_file_whitespace(tmp_path: Path):
    """Line 38: returns None when .aizee-version is only whitespace."""
    mod = _load_migrate_module()
    _write_version_file(tmp_path, "   \n  ")
    assert mod._read_version_file(tmp_path) is None


def test_read_version_file_valid(tmp_path: Path):
    """Line 37: returns stripped version."""
    mod = _load_migrate_module()
    _write_version_file(tmp_path, "4.22.0\n")
    assert mod._read_version_file(tmp_path) == "4.22.0"


# ---------------------------------------------------------------------------
# _read_target_version edge cases (lines 43-47)
# ---------------------------------------------------------------------------

def test_read_target_version_no_pyproject(tmp_path: Path):
    """Line 44-45: returns '0.0.0' when pyproject.toml doesn't exist."""
    mod = _load_migrate_module()
    assert mod._read_target_version(tmp_path) == "0.0.0"


def test_read_target_version_no_version_match(tmp_path: Path):
    """Line 47: returns '0.0.0' when pyproject.toml has no version."""
    mod = _load_migrate_module()
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    assert mod._read_target_version(tmp_path) == "0.0.0"


def test_read_target_version_with_match(tmp_path: Path):
    """Line 46-47: returns version from pyproject.toml."""
    mod = _load_migrate_module()
    _write_pyproject(tmp_path, "5.0.0")
    assert mod._read_target_version(tmp_path) == "5.0.0"


# ---------------------------------------------------------------------------
# _version_tuple edge cases (lines 56-57)
# ---------------------------------------------------------------------------

def test_version_tuple_invalid():
    """Lines 56-57: returns (0,0,0) for invalid version strings."""
    mod = _load_migrate_module()
    assert mod._version_tuple("invalid") == (0, 0, 0)
    assert mod._version_tuple("a.b.c") == (0, 0, 0)
    assert mod._version_tuple("") == (0, 0, 0)
    assert mod._version_tuple("1") == (1, 0, 0)


# ---------------------------------------------------------------------------
# _migrate_4_21_to_4_22 — plugins.yaml and config.json (lines 70-87, 102-103)
# ---------------------------------------------------------------------------

def test_migrate_4_21_to_4_22_with_plugins_yaml(tmp_path: Path):
    """Lines 69-74: migration handles plugins.yaml existence."""
    mod = _load_migrate_module()
    (tmp_path / "plugins.yaml").write_text("plugins:\n  context7:\n    enabled: true\n", encoding="utf-8")
    # Should not crash
    mod._migrate_4_21_to_4_22(tmp_path)


def test_migrate_4_21_to_4_22_with_config_json(tmp_path: Path):
    """Lines 77-87: migration handles aizee_mcp/config.json."""
    mod = _load_migrate_module()
    import json
    config_dir = tmp_path / "aizee_mcp"
    config_dir.mkdir(parents=True)
    config = {"mcpServers": {"existing": {"command": "test"}}}
    (config_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")
    mod._migrate_4_21_to_4_22(tmp_path)


def test_migrate_4_21_to_4_22_config_json_invalid(tmp_path: Path):
    """Lines 86-87: migration handles invalid config.json."""
    mod = _load_migrate_module()
    config_dir = tmp_path / "aizee_mcp"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text("invalid json{", encoding="utf-8")
    # Should not crash
    mod._migrate_4_21_to_4_22(tmp_path)


def test_migrate_4_21_to_4_22_mcp_config_invalid(tmp_path: Path):
    """Lines 102-103: migration handles invalid .devin/mcp_config.json."""
    mod = _load_migrate_module()
    devin_dir = tmp_path / ".devin"
    devin_dir.mkdir(parents=True)
    (devin_dir / "mcp_config.json").write_text("invalid json{", encoding="utf-8")
    # Should not crash
    mod._migrate_4_21_to_4_22(tmp_path)


def test_migrate_4_21_to_4_22_mcp_config_no_disabled(tmp_path: Path):
    """Lines 90-101: migration when no disabled flags present."""
    mod = _load_migrate_module()
    import json
    devin_dir = tmp_path / ".devin"
    devin_dir.mkdir(parents=True)
    config = {"mcpServers": {"upwork": {"command": "npx"}, "fiverr": {"command": "uvx"}}}
    (devin_dir / "mcp_config.json").write_text(json.dumps(config), encoding="utf-8")
    mod._migrate_4_21_to_4_22(tmp_path)
    # No changes should be made
    updated = json.loads((devin_dir / "mcp_config.json").read_text(encoding="utf-8"))
    assert "disabled" not in updated["mcpServers"]["upwork"]


# ---------------------------------------------------------------------------
# _migrate_4_22_to_4_22_1 (lines 117-162)
# ---------------------------------------------------------------------------

def test_migrate_4_22_to_4_22_1_with_brain_db(tmp_path: Path):
    """Lines 117-128: migration runs schema migrations on brain/memory.db."""
    mod = _load_migrate_module()
    brain_dir = tmp_path / "brain"
    brain_dir.mkdir(parents=True)
    (brain_dir / "memory.db").write_text("")  # Create empty file
    # Should handle exception gracefully
    mod._migrate_4_22_to_4_22_1(tmp_path)


def test_migrate_4_22_to_4_22_1_with_encrypted_budget(tmp_path: Path):
    """Lines 131-149: migration checks encrypted budget.json."""
    mod = _load_migrate_module()
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "budget.json").write_text('{"encrypted": true}', encoding="utf-8")
    # Should handle gracefully (no AIOS_ENCRYPTION_KEY set)
    mod._migrate_4_22_to_4_22_1(tmp_path)


def test_migrate_4_22_to_4_22_1_creates_docs_dir(tmp_path: Path):
    """Lines 151-156: migration creates docs/ directory."""
    mod = _load_migrate_module()
    mod._migrate_4_22_to_4_22_1(tmp_path)
    assert (tmp_path / "docs").exists()


def test_migrate_4_22_to_4_22_1_docs_already_exists(tmp_path: Path):
    """Lines 152-155: migration skips when docs/ already exists."""
    mod = _load_migrate_module()
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    mod._migrate_4_22_to_4_22_1(tmp_path)
    assert (tmp_path / "docs").exists()


def test_migrate_4_22_to_4_22_1_missing_module_dirs(tmp_path: Path):
    """Lines 158-165: migration warns about missing module directories."""
    mod = _load_migrate_module()
    # Don't create runtime/managers or aizee_mcp/tools
    mod._migrate_4_22_to_4_22_1(tmp_path)


def test_migrate_4_22_to_4_22_1_with_module_dirs(tmp_path: Path):
    """Lines 159-165: migration verifies module directories exist."""
    mod = _load_migrate_module()
    (tmp_path / "runtime" / "managers").mkdir(parents=True, exist_ok=True)
    (tmp_path / "aizee_mcp" / "tools").mkdir(parents=True, exist_ok=True)
    mod._migrate_4_22_to_4_22_1(tmp_path)


# ---------------------------------------------------------------------------
# _migrate_4_22_to_4_23 (lines 173-204)
# ---------------------------------------------------------------------------

def test_migrate_4_22_to_4_23_with_brain_db(tmp_path: Path):
    """Lines 171-182: migration runs schema migrations on brain/memory.db."""
    mod = _load_migrate_module()
    brain_dir = tmp_path / "brain"
    brain_dir.mkdir(parents=True)
    (brain_dir / "memory.db").write_text("")
    mod._migrate_4_22_to_4_23(tmp_path)


def test_migrate_4_22_to_4_23_with_budget(tmp_path: Path):
    """Lines 186-204: migration checks budget encryption."""
    mod = _load_migrate_module()
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "budget.json").write_text('{"test": true}', encoding="utf-8")
    mod._migrate_4_22_to_4_23(tmp_path)


def test_migrate_4_22_to_4_23_creates_docs(tmp_path: Path):
    """Lines 206-211: migration creates docs/ directory."""
    mod = _load_migrate_module()
    mod._migrate_4_22_to_4_23(tmp_path)
    assert (tmp_path / "docs").exists()


def test_migrate_4_22_to_4_23_no_brain_dir(tmp_path: Path):
    """Lines 117-118: migration handles missing brain directory."""
    mod = _load_migrate_module()
    # Don't create brain directory
    mod._migrate_4_22_to_4_23(tmp_path)


# ---------------------------------------------------------------------------
# run_migrations (lines 245-273)
# ---------------------------------------------------------------------------

def test_run_migrations_full_chain(tmp_path: Path):
    """Lines 260-272: run_migrations executes the full chain."""
    mod = _load_migrate_module()
    _write_pyproject(tmp_path, "4.23.0")
    _write_version_file(tmp_path, "4.21.0")
    code = mod.run_migrations(tmp_path)
    assert code == 1  # migrated successfully
    assert (tmp_path / ".aizee-version").read_text(encoding="utf-8").strip() == "4.23.0"


def test_run_migrations_dry_run_full_chain(tmp_path: Path):
    """Lines 260-272: dry-run doesn't execute migrations."""
    mod = _load_migrate_module()
    _write_pyproject(tmp_path, "4.23.0")
    _write_version_file(tmp_path, "4.21.0")
    code = mod.run_migrations(tmp_path, dry_run=True)
    assert code == 3  # dry-run
    # Version file should still say 4.21.0
    assert (tmp_path / ".aizee-version").read_text(encoding="utf-8").strip() == "4.21.0"


def test_run_migrations_no_chain_jumps(tmp_path: Path):
    """Lines 253-258: no chain found, jumps to target."""
    mod = _load_migrate_module()
    _write_pyproject(tmp_path, "9.9.9")
    _write_version_file(tmp_path, "4.23.0")
    code = mod.run_migrations(tmp_path)
    assert code == 1
    assert (tmp_path / ".aizee-version").read_text(encoding="utf-8").strip() == "9.9.9"


def test_run_migrations_no_chain_dry_run(tmp_path: Path):
    """Lines 253-258: no chain found in dry-run, doesn't write version."""
    mod = _load_migrate_module()
    _write_pyproject(tmp_path, "9.9.9")
    _write_version_file(tmp_path, "4.23.0")
    code = mod.run_migrations(tmp_path, dry_run=True)
    assert code == 1
    # Version file should still say 4.23.0 in dry-run
    assert (tmp_path / ".aizee-version").read_text(encoding="utf-8").strip() == "4.23.0"


# ---------------------------------------------------------------------------
# check_migrations (lines 278-287)
# ---------------------------------------------------------------------------

def test_check_migrations_up_to_date(tmp_path: Path):
    """Lines 280-282: check returns 0 when up-to-date."""
    mod = _load_migrate_module()
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.22.0")
    code = mod.check_migrations(tmp_path)
    assert code == 0


def test_check_migrations_pending_with_chain(tmp_path: Path):
    """Lines 283-287: check returns 3 when pending with chain."""
    mod = _load_migrate_module()
    _write_pyproject(tmp_path, "4.23.0")
    _write_version_file(tmp_path, "4.21.0")
    code = mod.check_migrations(tmp_path)
    assert code == 3


def test_check_migrations_pending_no_chain(tmp_path: Path):
    """Lines 283-287: check returns 3 when pending without chain."""
    mod = _load_migrate_module()
    _write_pyproject(tmp_path, "9.9.9")
    _write_version_file(tmp_path, "4.23.0")
    code = mod.check_migrations(tmp_path)
    assert code == 3


# ---------------------------------------------------------------------------
# main() (line 308)
# ---------------------------------------------------------------------------

def test_main_no_pyproject(tmp_path: Path):
    """Lines 298-300: main returns 2 when no pyproject.toml."""
    code, output = _run_migrate(tmp_path)
    assert code == 2
    assert "does not look like" in output


def test_main_check_flag(tmp_path: Path):
    """Line 302-303: main with --check flag."""
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.22.0")
    code, _output = _run_migrate(tmp_path, "--check")
    assert code == 0


def test_main_dry_run_flag(tmp_path: Path):
    """Line 304: main with --dry-run flag."""
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.21.0")
    code, _output = _run_migrate(tmp_path, "--dry-run")
    assert code == 3


# ---------------------------------------------------------------------------
# __main__ block (line 308)
# ---------------------------------------------------------------------------

def test_main_block_executes(tmp_path: Path):
    """Line 308: __main__ block runs main()."""
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.22.0")
    code, output = _run_migrate(tmp_path)
    assert code == 0
    assert "No migration needed" in output


# ---------------------------------------------------------------------------
# _migrate_4_22_to_4_22_1 — schema migration success (line 126)
# ---------------------------------------------------------------------------

def test_migrate_4_22_to_4_22_1_schema_success(tmp_path: Path):
    """Line 126: schema migration succeeds and prints version."""
    mod = _load_migrate_module()
    brain_dir = tmp_path / "brain"
    brain_dir.mkdir(parents=True)
    (brain_dir / "memory.db").write_text("")
    mock_runner = MagicMock()
    mock_runner.run_migrations.return_value = 5
    with patch("runtime.migrations.MigrationRunner", return_value=mock_runner):
        mod._migrate_4_22_to_4_22_1(tmp_path)


# ---------------------------------------------------------------------------
# _migrate_4_22_to_4_22_1 — encryption paths (lines 137-149)
# ---------------------------------------------------------------------------

def test_migrate_4_22_to_4_22_1_encrypted_no_key(tmp_path: Path, monkeypatch):
    """Lines 137-144: encrypted budget.json with no AIOS_ENCRYPTION_KEY."""
    mod = _load_migrate_module()
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "budget.json").write_text('{"encrypted": true}', encoding="utf-8")
    monkeypatch.delenv("AIOS_ENCRYPTION_KEY", raising=False)
    with patch("runtime.crypto.is_encrypted", return_value=True):
        mod._migrate_4_22_to_4_22_1(tmp_path)


def test_migrate_4_22_to_4_22_1_encrypted_with_key(tmp_path: Path, monkeypatch):
    """Lines 146-147: encrypted budget.json with AIOS_ENCRYPTION_KEY set, decrypts OK."""
    mod = _load_migrate_module()
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "budget.json").write_text('{"encrypted": true}', encoding="utf-8")
    monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "test-key")
    with patch("runtime.crypto.is_encrypted", return_value=True), \
         patch("runtime.crypto.decrypt_file") as mock_decrypt:
        mod._migrate_4_22_to_4_22_1(tmp_path)
        mock_decrypt.assert_called_once()


def test_migrate_4_22_to_4_22_1_encrypted_exception(tmp_path: Path, monkeypatch):
    """Lines 148-149: encryption check raises exception."""
    mod = _load_migrate_module()
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "budget.json").write_text('{"encrypted": true}', encoding="utf-8")
    with patch("runtime.crypto.is_encrypted", side_effect=Exception("crypto error")):
        mod._migrate_4_22_to_4_22_1(tmp_path)


# ---------------------------------------------------------------------------
# _migrate_4_22_to_4_23 — schema migration success (line 180)
# ---------------------------------------------------------------------------

def test_migrate_4_22_to_4_23_schema_success(tmp_path: Path):
    """Line 180: schema migration succeeds and prints version."""
    mod = _load_migrate_module()
    brain_dir = tmp_path / "brain"
    brain_dir.mkdir(parents=True)
    (brain_dir / "memory.db").write_text("")
    mock_runner = MagicMock()
    mock_runner.run_migrations.return_value = 5
    with patch("runtime.migrations.MigrationRunner", return_value=mock_runner):
        mod._migrate_4_22_to_4_23(tmp_path)


# ---------------------------------------------------------------------------
# _migrate_4_22_to_4_23 — encryption paths (lines 192-204)
# ---------------------------------------------------------------------------

def test_migrate_4_22_to_4_23_encrypted_no_key(tmp_path: Path, monkeypatch):
    """Lines 192-199: encrypted budget.json with no AIOS_ENCRYPTION_KEY."""
    mod = _load_migrate_module()
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "budget.json").write_text('{"encrypted": true}', encoding="utf-8")
    monkeypatch.delenv("AIOS_ENCRYPTION_KEY", raising=False)
    with patch("runtime.crypto.is_encrypted", return_value=True):
        mod._migrate_4_22_to_4_23(tmp_path)


def test_migrate_4_22_to_4_23_encrypted_with_key(tmp_path: Path, monkeypatch):
    """Lines 200-202: encrypted budget.json with AIOS_ENCRYPTION_KEY set, decrypts OK."""
    mod = _load_migrate_module()
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "budget.json").write_text('{"encrypted": true}', encoding="utf-8")
    monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "test-key")
    with patch("runtime.crypto.is_encrypted", return_value=True), \
         patch("runtime.crypto.decrypt_file") as mock_decrypt:
        mod._migrate_4_22_to_4_23(tmp_path)
        mock_decrypt.assert_called_once()


def test_migrate_4_22_to_4_23_encrypted_exception(tmp_path: Path, monkeypatch):
    """Lines 203-204: encryption check raises exception."""
    mod = _load_migrate_module()
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "budget.json").write_text('{"encrypted": true}', encoding="utf-8")
    with patch("runtime.crypto.is_encrypted", side_effect=Exception("crypto error")):
        mod._migrate_4_22_to_4_23(tmp_path)


# ---------------------------------------------------------------------------
# run_migrations — already at target (lines 249-250)
# ---------------------------------------------------------------------------

def test_run_migrations_already_at_target(tmp_path: Path):
    """Lines 249-250: run_migrations returns 0 when already at target."""
    mod = _load_migrate_module()
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.22.0")
    code = mod.run_migrations(tmp_path)
    assert code == 0


# ---------------------------------------------------------------------------
# run_migrations — migration failure (lines 266-268)
# ---------------------------------------------------------------------------

def test_run_migrations_migration_fails(tmp_path: Path):
    """Lines 266-268: run_migrations returns 2 when a migration function raises."""
    mod = _load_migrate_module()
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.21.0")

    def _failing_fn(root: Path) -> None:
        raise Exception("migration failed")

    with patch.object(mod, "_MIGRATIONS", [("4.21.0", "4.22.0", _failing_fn)]):
        code = mod.run_migrations(tmp_path)
        assert code == 2


# ---------------------------------------------------------------------------
# main() — direct call (lines 291-304)
# ---------------------------------------------------------------------------

def test_main_direct_call_check(tmp_path: Path, monkeypatch):
    """Lines 291-304: main() with --check flag via direct call."""
    mod = _load_migrate_module()
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.22.0")
    monkeypatch.setattr(sys, "argv", ["migrate.py", "--root", str(tmp_path), "--check"])
    code = mod.main()
    assert code == 0


def test_main_direct_call_dry_run(tmp_path: Path, monkeypatch):
    """Lines 291-304: main() with --dry-run flag via direct call."""
    mod = _load_migrate_module()
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.21.0")
    monkeypatch.setattr(sys, "argv", ["migrate.py", "--root", str(tmp_path), "--dry-run"])
    code = mod.main()
    assert code == 3


def test_main_direct_call_no_pyproject(tmp_path: Path, monkeypatch):
    """Lines 298-300: main() returns 2 when no pyproject.toml."""
    mod = _load_migrate_module()
    monkeypatch.setattr(sys, "argv", ["migrate.py", "--root", str(tmp_path)])
    code = mod.main()
    assert code == 2


def test_main_direct_call_run(tmp_path: Path, monkeypatch):
    """Lines 291-304: main() with no flags runs migrations."""
    mod = _load_migrate_module()
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.21.0")
    monkeypatch.setattr(sys, "argv", ["migrate.py", "--root", str(tmp_path)])
    code = mod.main()
    assert code == 1


# ---------------------------------------------------------------------------
# __main__ block — in-process (line 308)
# ---------------------------------------------------------------------------

def test_main_block_in_process(tmp_path: Path, monkeypatch):
    """Line 308: __main__ block calls sys.exit(main()) — exercised in-process."""
    _write_pyproject(tmp_path, "4.22.0")
    _write_version_file(tmp_path, "4.22.0")
    monkeypatch.setattr(sys, "argv", ["migrate.py", "--root", str(tmp_path), "--check"])
    spec = importlib.util.spec_from_file_location("__main__", _MIGRATE)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    with patch("sys.exit") as mock_exit:
        spec.loader.exec_module(mod)
    mock_exit.assert_called_once_with(0)
