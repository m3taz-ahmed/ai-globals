"""Tests for runtime/daemon.py — background settings-sync daemon."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from runtime.daemon import AizeeDaemon


@pytest.fixture
def daemon_root(tmp_path: Path) -> Path:
    """Create a minimal aiZee root structure for daemon tests."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    # Minimal settings.json with MCP servers
    settings = {
        "version": 2,
        "mcp_servers": {
            "aizee": {"enabled": True},
            "upwork": {"enabled": False},
            "context7": {"enabled": True},
        },
    }
    (state_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    # Minimal MCP config
    mcp_dir = tmp_path / "aizee_mcp"
    mcp_dir.mkdir()
    (mcp_dir / "config.json").write_text(
        json.dumps({"mcpServers": {"aizee": {"command": "python", "args": ["x.py"]}}}),
        encoding="utf-8",
    )
    # .devin directory
    devin_dir = tmp_path / ".devin"
    devin_dir.mkdir()
    return tmp_path


class TestDaemonStatus:
    """Test the status classmethod (no daemon process needed)."""

    def test_status_not_running(self, daemon_root: Path) -> None:
        status = AizeeDaemon.status(daemon_root)
        assert status["running"] is False
        assert status["pid"] is None
        assert status["root"] == str(daemon_root)

    def test_status_with_stale_pid(self, daemon_root: Path) -> None:
        """Stale PID file (process not alive) → running=False."""
        (daemon_root / "state" / "daemon.pid").write_text("999999", encoding="utf-8")
        status = AizeeDaemon.status(daemon_root)
        assert status["running"] is False


class TestDaemonSync:
    """Test the IDE config sync logic (no daemon process needed)."""

    def test_sync_devin_local_disabled(self, daemon_root: Path) -> None:
        """Disabled servers get disabled flag in .devin/mcp_config.local.json."""
        daemon = AizeeDaemon(daemon_root)
        mcp_settings = {"aizee": {"enabled": True}, "upwork": {"enabled": False}}
        daemon._sync_devin_local(mcp_settings)
        local_path = daemon_root / ".devin" / "mcp_config.local.json"
        assert local_path.exists()
        local = json.loads(local_path.read_text(encoding="utf-8"))
        assert local["mcpServers"]["upwork"]["disabled"] is True
        assert "disabled" not in local["mcpServers"].get("aizee", {})

    def test_sync_devin_local_enabled_removes_flag(self, daemon_root: Path) -> None:
        """Re-enabling a server removes the disabled flag."""
        local_path = daemon_root / ".devin" / "mcp_config.local.json"
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(
            json.dumps({"mcpServers": {"upwork": {"disabled": True}}}),
            encoding="utf-8",
        )
        daemon = AizeeDaemon(daemon_root)
        daemon._sync_devin_local({"upwork": {"enabled": True}})
        local = json.loads(local_path.read_text(encoding="utf-8"))
        assert "disabled" not in local["mcpServers"].get("upwork", {})

    def test_sync_claude_removes_disabled(self, daemon_root: Path) -> None:
        """Disabled servers are removed from .claude/settings.json."""
        claude_dir = daemon_root / ".claude"
        claude_dir.mkdir()
        claude_path = claude_dir / "settings.json"
        claude_path.write_text(
            json.dumps({"mcpServers": {"aizee": {"command": "python"}, "upwork": {"command": "node"}}}),
            encoding="utf-8",
        )
        daemon = AizeeDaemon(daemon_root)
        daemon._sync_claude_settings({"aizee": {"enabled": True}, "upwork": {"enabled": False}})
        claude_cfg = json.loads(claude_path.read_text(encoding="utf-8"))
        assert "aizee" in claude_cfg["mcpServers"]
        assert "upwork" not in claude_cfg["mcpServers"]

    def test_sync_claude_restores_enabled(self, daemon_root: Path) -> None:
        """Re-enabled servers are restored from canonical config."""
        claude_dir = daemon_root / ".claude"
        claude_dir.mkdir()
        claude_path = claude_dir / "settings.json"
        claude_path.write_text(
            json.dumps({"mcpServers": {}}),
            encoding="utf-8",
        )
        daemon = AizeeDaemon(daemon_root)
        daemon._sync_claude_settings({"aizee": {"enabled": True}})
        claude_cfg = json.loads(claude_path.read_text(encoding="utf-8"))
        assert "aizee" in claude_cfg["mcpServers"]

    def test_full_sync_creates_all_configs(self, daemon_root: Path) -> None:
        """_sync_ide_configs creates all IDE config files."""
        daemon = AizeeDaemon(daemon_root)
        daemon._sync_ide_configs()
        # Devin local should exist
        assert (daemon_root / ".devin" / "mcp_config.local.json").exists()
        # Health should have sync count
        assert daemon._sync_count >= 1


class TestDaemonPID:
    """Test PID file management."""

    def test_pid_file_lifecycle(self, daemon_root: Path) -> None:
        daemon = AizeeDaemon(daemon_root)
        daemon._write_pid()
        pid = daemon._read_pid()
        assert pid == os.getpid()
        daemon._cleanup_pid_file()
        assert not (daemon_root / "state" / "daemon.pid").exists()


class TestDaemonHeartbeat:
    """Test heartbeat file writing."""

    def test_heartbeat_written(self, daemon_root: Path) -> None:
        daemon = AizeeDaemon(daemon_root)
        daemon._started_at = time.time()
        daemon._write_heartbeat()
        health_path = daemon_root / "state" / "daemon.health"
        assert health_path.exists()
        health = json.loads(health_path.read_text(encoding="utf-8"))
        assert "timestamp" in health
        assert "pid" in health
        assert health["pid"] == os.getpid()


class TestDaemonCheckAndSync:
    """Test the file watcher change detection."""

    def test_detects_settings_change(self, daemon_root: Path) -> None:
        daemon = AizeeDaemon(daemon_root)
        # First check — should detect (mtime is 0 initially)
        synced = daemon._check_and_sync()
        assert synced is True
        # Second check — no change
        synced = daemon._check_and_sync()
        assert synced is False
        # Modify settings
        time.sleep(0.1)
        settings_path = daemon_root / "state" / "settings.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        settings["mcp_servers"]["aizee"]["enabled"] = False
        settings_path.write_text(json.dumps(settings), encoding="utf-8")
        # Third check — should detect change
        synced = daemon._check_and_sync()
        assert synced is True
