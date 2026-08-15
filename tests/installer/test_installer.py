#!/usr/bin/env python3
"""Tests for installer helpers (log, retry, checksum, auto-detect, health check).

These tests verify the helper functions embedded in install.ps1 and install.sh
by testing the underlying logic via Python equivalents.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent.parent


def _sha256(path: Path) -> str:
    """Compute SHA256 checksum of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_checksum_consistency(tmp_path: Path):
    """Checksum of the same file should be consistent."""
    f = tmp_path / "test.txt"
    f.write_text("hello world", encoding="utf-8")
    h1 = _sha256(f)
    h2 = _sha256(f)
    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex length


def test_checksum_detects_changes(tmp_path: Path):
    """Checksum should change when file content changes."""
    f = tmp_path / "test.txt"
    f.write_text("hello", encoding="utf-8")
    h1 = _sha256(f)
    f.write_text("world", encoding="utf-8")
    h2 = _sha256(f)
    assert h1 != h2


def test_checksum_identical_files(tmp_path: Path):
    """Two files with identical content should have identical checksums."""
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("same content", encoding="utf-8")
    f2.write_text("same content", encoding="utf-8")
    assert _sha256(f1) == _sha256(f2)


def test_version_comparison_logic():
    """Test version comparison matches installer logic."""
    def compare(a: str, b: str) -> int:
        ap = [int(x) for x in a.split(".")]
        bp = [int(x) for x in b.split(".")]
        while len(ap) < 3: ap.append(0)
        while len(bp) < 3: bp.append(0)
        for i in range(3):
            if ap[i] < bp[i]: return -1
            if ap[i] > bp[i]: return 1
        return 0

    assert compare("4.22.0", "4.22.0") == 0
    assert compare("4.21.0", "4.22.0") == -1
    assert compare("4.22.0", "4.21.0") == 1
    assert compare("4.22.0", "5.0.0") == -1
    assert compare("5.0.0", "4.22.0") == 1
    assert compare("4.22", "4.22.0") == 0
    assert compare("4.22.10", "4.22.9") == 1


def test_root_validity_check(tmp_path: Path):
    """Test that root validity check works correctly."""
    def root_valid(root: Path) -> bool:
        return (root / "pyproject.toml").exists() or (root / "config.py").exists()

    # Empty dir - not valid
    assert not root_valid(tmp_path)

    # With pyproject.toml - valid
    (tmp_path / "pyproject.toml").write_text('[project]\nversion="1.0"', encoding="utf-8")
    assert root_valid(tmp_path)

    # With config.py only - valid
    tmp_path2 = tmp_path / "sub"
    tmp_path2.mkdir()
    (tmp_path2 / "config.py").write_text("VERSION='1.0'", encoding="utf-8")
    assert root_valid(tmp_path2)


def test_resolve_stale_root_logic(tmp_path: Path):
    """Test auto-detect moved repo logic."""
    def resolve_stale_root(repo: Path, current: str) -> str:
        if current and not Path(current).exists():
            if (repo / "pyproject.toml").exists():
                return str(repo)
        if current and not (Path(current) / "pyproject.toml").exists():
            if (repo / "pyproject.toml").exists():
                return str(repo)
        return current

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("version='1.0'", encoding="utf-8")

    # Stale root (doesn't exist) -> should return repo
    assert resolve_stale_root(repo, "/nonexistent/path") == str(repo)

    # Valid current root -> should return current
    valid_root = tmp_path / "valid"
    valid_root.mkdir()
    (valid_root / "pyproject.toml").write_text("version='1.0'", encoding="utf-8")
    assert resolve_stale_root(repo, str(valid_root)) == str(valid_root)

    # Current root exists but doesn't have pyproject.toml -> should return repo
    stale_root2 = tmp_path / "stale_no_pyproject"
    stale_root2.mkdir()
    (stale_root2 / "other.txt").write_text("not a project", encoding="utf-8")
    assert resolve_stale_root(repo, str(stale_root2)) == str(repo)


def test_mcp_health_check_logic(tmp_path: Path):
    """Test MCP health check logic with a mock config."""
    config = {
        "mcpServers": {
            "ai-global-os": {"command": "python", "args": []},
            "context7": {"command": "npx", "args": ["-y", "@upstash/context7-mcp"]},
            "fiverr": {"command": "uvx", "args": ["fiverr-mcp-server"]},
        }
    }
    config_path = tmp_path / "mcp_config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    # Simulate health check logic
    import shutil
    results = {}
    for name, srv in config["mcpServers"].items():
        cmd = srv["command"]
        if cmd == "python":
            results[name] = "python-based (deferred)"
        elif cmd == "npx":
            results[name] = "ready" if shutil.which("npx") else "npx not found"
        elif cmd == "uvx":
            results[name] = "ready" if shutil.which("uvx") else "uvx not found"

    assert "ai-global-os" in results
    assert "context7" in results
    assert "fiverr" in results
    assert results["ai-global-os"] == "python-based (deferred)"


def test_install_ps1_exists():
    """Verify install.ps1 exists in repo."""
    assert (_REPO / "install.ps1").exists()


def test_install_sh_exists():
    """Verify install.sh exists in repo."""
    assert (_REPO / "install.sh").exists()


def test_gui_installer_exists():
    """Verify GUI installer exists."""
    assert (_REPO / "installer" / "gui_installer.ps1").exists()


def test_migrate_script_exists():
    """Verify migrate.py exists."""
    assert (_REPO / "scripts" / "migrate.py").exists()


def test_aios_version_file_exists():
    """Verify .aios-version exists."""
    assert (_REPO / ".aios-version").exists()


def test_install_ps1_has_log_function():
    """Verify install.ps1 has logging support."""
    content = (_REPO / "install.ps1").read_text(encoding="utf-8")
    assert "Start-Log" in content
    assert "Write-Log" in content
    assert "LogFile" in content


def test_install_ps1_has_retry_function():
    """Verify install.ps1 has retry logic."""
    content = (_REPO / "install.ps1").read_text(encoding="utf-8")
    assert "Invoke-WithRetry" in content
    assert "MaxRetries" in content


def test_install_ps1_has_health_check():
    """Verify install.ps1 has MCP health check."""
    content = (_REPO / "install.ps1").read_text(encoding="utf-8")
    assert "Test-MCPServers" in content
    assert "Health check" in content


def test_install_ps1_has_rollback():
    """Verify install.ps1 has rollback support."""
    content = (_REPO / "install.ps1").read_text(encoding="utf-8")
    assert "RollbackStack" in content
    assert "Invoke-Rollback" in content
    assert "Push-Rollback" in content


def test_install_ps1_has_auto_detect():
    """Verify install.ps1 has auto-detect moved repo."""
    content = (_REPO / "install.ps1").read_text(encoding="utf-8")
    assert "Resolve-StaleRoot" in content
    assert "Test-RootValid" in content


def test_install_ps1_has_checksum():
    """Verify install.ps1 has checksum verification."""
    content = (_REPO / "install.ps1").read_text(encoding="utf-8")
    assert "Get-FileChecksum" in content
    assert "Test-FileChecksum" in content


def test_install_ps1_has_gui_redirect():
    """Verify install.ps1 redirects to GUI installer."""
    content = (_REPO / "install.ps1").read_text(encoding="utf-8")
    assert "Gui" in content
    assert "gui_installer.ps1" in content


def test_install_sh_has_log_function():
    """Verify install.sh has logging support."""
    content = (_REPO / "install.sh").read_text(encoding="utf-8")
    assert "start_log" in content
    assert "LOG_FILE" in content


def test_install_sh_has_retry_function():
    """Verify install.sh has retry logic."""
    content = (_REPO / "install.sh").read_text(encoding="utf-8")
    assert "retry()" in content
    assert "RETRY_MAX" in content


def test_install_sh_has_health_check():
    """Verify install.sh has MCP health check."""
    content = (_REPO / "install.sh").read_text(encoding="utf-8")
    assert "health_check_mcp" in content


def test_install_sh_has_auto_detect():
    """Verify install.sh has auto-detect moved repo."""
    content = (_REPO / "install.sh").read_text(encoding="utf-8")
    assert "resolve_stale_root" in content
    assert "root_valid" in content


def test_gui_installer_has_8_pages():
    """Verify GUI installer has all 8 wizard pages."""
    content = (_REPO / "installer" / "gui_installer.ps1").read_text(encoding="utf-8")
    pages = ["PageWelcome", "PageLicense", "PageLocation", "PageComponents",
             "PageConfig", "PagePreFlight", "PageProgress", "PageFinish"]
    for page in pages:
        assert page in content, f"Missing page: {page}"


def test_gui_installer_has_component_selection():
    """Verify GUI installer has component checkboxes."""
    content = (_REPO / "installer" / "gui_installer.ps1").read_text(encoding="utf-8")
    components = ["CompCore", "CompPip", "CompGraphify", "CompMCPGraphify",
                  "CompMCPContext7", "CompMCPUpwork", "CompMCPFreelancer",
                  "CompMCPFiverr", "CompAgentClaude", "CompAgentWindsurf",
                  "CompAgentCursor", "CompAgentAider", "CompAgentDevin",
                  "CompCLIShim", "CompEnvVar"]
    for comp in components:
        assert comp in content, f"Missing component: {comp}"


def test_gui_installer_has_silent_mode():
    """Verify GUI installer supports silent mode."""
    content = (_REPO / "installer" / "gui_installer.ps1").read_text(encoding="utf-8")
    assert "Silent" in content
    assert "install.ps1" in content


def test_gui_installer_has_preflight_checks():
    """Verify GUI installer has pre-flight checks."""
    content = (_REPO / "installer" / "gui_installer.ps1").read_text(encoding="utf-8")
    assert "CheckPython" in content
    assert "CheckNpx" in content
    assert "CheckUvx" in content
    assert "CheckDisk" in content
    assert "Run-PreFlightChecks" in content
