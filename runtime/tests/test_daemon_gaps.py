"""Gap coverage for runtime/daemon.py edge paths."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runtime.daemon import AizeeDaemon


@pytest.fixture
def daemon(tmp_path):
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    return AizeeDaemon(tmp_path, foreground=True)


class TestStop:
    def test_stop_no_pid(self, daemon):
        assert daemon.stop() is False

    def test_stop_dead_pid(self, daemon):
        daemon._pid_file.write_text("999999")
        with patch.object(AizeeDaemon, "_is_process_alive", return_value=False):
            assert daemon.stop() is False
        assert not daemon._pid_file.exists()

    def test_stop_windows(self, daemon):
        daemon._pid_file.write_text("1234")
        with patch.object(AizeeDaemon, "_is_process_alive", return_value=True), \
             patch("platform.system", return_value="Windows"), \
             patch("subprocess.run") as run:
            assert daemon.stop() is True
            run.assert_called_once()
            assert "taskkill" in run.call_args[0][0]

    def test_stop_posix(self, daemon):
        daemon._pid_file.write_text("1234")
        with patch.object(AizeeDaemon, "_is_process_alive", return_value=True), \
             patch("platform.system", return_value="Linux"), \
             patch("os.kill") as kill:
            assert daemon.stop() is True
            kill.assert_called_once()

    def test_stop_process_gone(self, daemon):
        daemon._pid_file.write_text("1234")
        with patch.object(AizeeDaemon, "_is_process_alive", return_value=True), \
             patch("platform.system", return_value="Linux"), \
             patch("os.kill", side_effect=ProcessLookupError):
            assert daemon.stop() is False
        assert not daemon._pid_file.exists()

    def test_stop_permission(self, daemon):
        daemon._pid_file.write_text("1234")
        with patch.object(AizeeDaemon, "_is_process_alive", return_value=True), \
             patch("platform.system", return_value="Linux"), \
             patch("os.kill", side_effect=PermissionError):
            assert daemon.stop() is False


class TestWatchHeartbeat:
    def test_watch_loop_exception(self, daemon):
        daemon._stop_event.set()  # exit after first iteration attempt
        with patch.object(daemon, "_check_and_sync", side_effect=RuntimeError("x")):
            daemon._watch_loop()  # logs, doesn't crash

    def test_heartbeat_loop_once(self, daemon):
        calls = []

        def hb():
            calls.append(1)
            daemon._stop_event.set()

        daemon._write_heartbeat = hb
        daemon._heartbeat_loop()
        assert calls

    def test_check_sync_no_file(self, daemon):
        assert daemon._check_and_sync() is False

    def test_check_sync_stat_error(self, daemon):
        daemon._settings_file.parent.mkdir(parents=True, exist_ok=True)
        daemon._settings_file.write_text("{}")
        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "stat", side_effect=OSError):
            assert daemon._check_and_sync() is False

    def test_check_sync_same_mtime(self, daemon):
        daemon._settings_file.parent.mkdir(parents=True, exist_ok=True)
        daemon._settings_file.write_text("{}")
        daemon._last_settings_mtime = daemon._settings_file.stat().st_mtime
        assert daemon._check_and_sync() is False

    def test_check_sync_read_error(self, daemon):
        daemon._settings_file.parent.mkdir(parents=True, exist_ok=True)
        daemon._settings_file.write_text("{}")
        with patch.object(Path, "read_bytes", side_effect=OSError):
            assert daemon._check_and_sync() is False

    def test_check_sync_same_content(self, daemon):
        daemon._settings_file.parent.mkdir(parents=True, exist_ok=True)
        daemon._settings_file.write_text("{}")
        content = daemon._settings_file.read_bytes()
        import hashlib

        daemon._last_settings_mtime = 0
        daemon._last_settings_hash = hashlib.sha256(content).hexdigest()
        assert daemon._check_and_sync() is False
        assert daemon._last_settings_mtime != 0

    def test_check_sync_changed(self, daemon):
        daemon._settings_file.parent.mkdir(parents=True, exist_ok=True)
        daemon._settings_file.write_text('{"mcp_servers": {}}')
        daemon._last_settings_mtime = 0
        daemon._last_settings_hash = "x"
        with patch.object(daemon, "_sync_ide_configs") as sync:
            assert daemon._check_and_sync() is True
            sync.assert_called_once()

    def test_heartbeat_write_error(self, daemon):
        with patch.object(Path, "write_text", side_effect=OSError("disk")):
            daemon._write_heartbeat()  # warns, no raise


class TestSyncCursor:
    def test_no_cursor_file(self, daemon):
        assert daemon._sync_cursor_mcp({"s": {"enabled": False}}) == 0

    def test_corrupt_cursor(self, daemon):
        cp = daemon.root / ".cursor" / "mcp.json"
        cp.parent.mkdir(parents=True)
        cp.write_text("{bad")
        assert daemon._sync_cursor_mcp({"s": {"enabled": False}}) == 0

    def test_no_mcpservers_key(self, daemon):
        cp = daemon.root / ".cursor" / "mcp.json"
        cp.parent.mkdir(parents=True)
        cp.write_text('{"x": 1}')
        assert daemon._sync_cursor_mcp({"s": {"enabled": False}}) == 0

    def test_removes_disabled(self, daemon):
        cp = daemon.root / ".cursor" / "mcp.json"
        cp.parent.mkdir(parents=True)
        cp.write_text(json.dumps({"mcpServers": {"srv": {}, "keep": {}}}))
        assert daemon._sync_cursor_mcp({"srv": {"enabled": False}}) == 1
        data = json.loads(cp.read_text())
        assert "srv" not in data["mcpServers"]

    def test_no_change(self, daemon):
        cp = daemon.root / ".cursor" / "mcp.json"
        cp.parent.mkdir(parents=True)
        cp.write_text(json.dumps({"mcpServers": {"srv": {}}}))
        assert daemon._sync_cursor_mcp({"other": {"enabled": False}}) == 0


class TestSyncGlobalDevin:
    def test_missing_file(self, daemon, tmp_path, monkeypatch):
        monkeypatch.setenv("APPDATA", str(tmp_path / "noexist"))
        assert daemon._sync_global_devin({"s": {"enabled": False}}) == 0

    def test_disables_server(self, daemon, tmp_path, monkeypatch):
        gp = tmp_path / "app" / "devin" / "mcp_config.json"
        gp.parent.mkdir(parents=True)
        gp.write_text(json.dumps({"mcpServers": {"srv": {}}}))
        monkeypatch.setenv("APPDATA", str(tmp_path / "app"))
        assert daemon._sync_global_devin({"srv": {"enabled": False}}) == 1
        data = json.loads(gp.read_text())
        assert data["mcpServers"]["srv"]["disabled"] is True

    def test_reenables_server(self, daemon, tmp_path, monkeypatch):
        gp = tmp_path / "app" / "devin" / "mcp_config.json"
        gp.parent.mkdir(parents=True)
        gp.write_text(json.dumps({"mcpServers": {"srv": {"disabled": True}}}))
        monkeypatch.setenv("APPDATA", str(tmp_path / "app"))
        assert daemon._sync_global_devin({"srv": {"enabled": True}}) == 1
        data = json.loads(gp.read_text())
        assert "disabled" not in data["mcpServers"]["srv"]

    def test_corrupt_file(self, daemon, tmp_path, monkeypatch):
        gp = tmp_path / "app" / "devin" / "mcp_config.json"
        gp.parent.mkdir(parents=True)
        gp.write_text("{bad")
        monkeypatch.setenv("APPDATA", str(tmp_path / "app"))
        assert daemon._sync_global_devin({"srv": {"enabled": False}}) == 0

    def test_bad_servers_type(self, daemon, tmp_path, monkeypatch):
        gp = tmp_path / "app" / "devin" / "mcp_config.json"
        gp.parent.mkdir(parents=True)
        gp.write_text('{"mcpServers": "nope"}')
        monkeypatch.setenv("APPDATA", str(tmp_path / "app"))
        assert daemon._sync_global_devin({"s": {"enabled": False}}) == 0


class TestProcessAlive:
    def test_negative_pid(self):
        assert AizeeDaemon._is_process_alive_static(-1) is False

    def test_posix_alive(self):
        with patch("platform.system", return_value="Linux"), \
             patch("os.kill"):
            assert AizeeDaemon._is_process_alive_static(123) is True

    def test_posix_dead(self):
        with patch("platform.system", return_value="Linux"), \
             patch("os.kill", side_effect=ProcessLookupError):
            assert AizeeDaemon._is_process_alive_static(123) is False

    def test_windows_dead(self):
        m = MagicMock()
        m.stdout = "no tasks"
        with patch("platform.system", return_value="Windows"), \
             patch("subprocess.run", return_value=m):
            assert AizeeDaemon._is_process_alive_static(123) is False

    def test_windows_timeout(self):
        import subprocess

        with patch("platform.system", return_value="Windows"), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("x", 1)):
            assert AizeeDaemon._is_process_alive_static(123) is False


class TestSignals:
    def test_signal_handlers(self, daemon):
        with patch("signal.signal") as sig:
            daemon._setup_signal_handlers()
            assert sig.call_count >= 2


class TestStatus:
    def test_status_no_daemon(self, tmp_path):
        (tmp_path / "state").mkdir(parents=True, exist_ok=True)
        st = AizeeDaemon.status(tmp_path)
        assert st["running"] is False

    def test_status_corrupt_health(self, tmp_path):
        sd = tmp_path / "state"
        sd.mkdir(parents=True)
        (sd / "health.json").write_text("{bad")
        st = AizeeDaemon.status(tmp_path)
        assert st["running"] is False
