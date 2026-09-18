"""Tests for runtime/daemon.py — background settings-sync daemon."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from runtime.daemon import AizeeDaemon, DaemonError, main


@pytest.fixture()
def root():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture()
def daemon(root):
    return AizeeDaemon(root)


def _write_settings(root: Path, servers: dict) -> None:
    state = root / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "settings.json").write_text(json.dumps({"mcp_servers": servers}))


class TestPidManagement:
    def test_write_read_pid(self, daemon):
        daemon._write_pid()
        assert daemon._read_pid() == os.getpid()

    def test_read_pid_missing(self, daemon):
        assert daemon._read_pid() is None

    def test_read_pid_invalid(self, daemon):
        daemon._state_dir.mkdir(parents=True, exist_ok=True)
        daemon._pid_file.write_text("not-a-pid")
        assert daemon._read_pid() is None

    def test_is_process_alive_self(self):
        assert AizeeDaemon._is_process_alive(os.getpid()) is True

    def test_is_process_alive_invalid(self):
        assert AizeeDaemon._is_process_alive(-1) is False
        assert AizeeDaemon._is_process_alive(0) is False

    def test_cleanup_pid_file(self, daemon):
        daemon._write_pid()
        daemon._cleanup_pid_file()
        assert not daemon._pid_file.exists()
        daemon._cleanup_pid_file()  # idempotent


class TestStatus:
    def test_status_not_running(self, root):
        s = AizeeDaemon.status(root)
        assert s["running"] is False
        assert s["pid"] is None
        assert s["root"] == str(root)

    def test_status_with_health(self, root):
        state = root / "state"
        state.mkdir(parents=True)
        (state / "daemon.health").write_text(json.dumps({
            "started_at": 100, "timestamp": 200, "uptime_seconds": 100,
            "syncs": 3, "last_sync": 190,
        }))
        s = AizeeDaemon.status(root)
        assert s["syncs"] == 3
        assert s["uptime_seconds"] == 100
        assert s["last_heartbeat"] == 200

    def test_status_corrupt_health(self, root):
        state = root / "state"
        state.mkdir(parents=True)
        (state / "daemon.health").write_text("{bad")
        s = AizeeDaemon.status(root)
        assert s["running"] is False
        assert s["last_heartbeat"] is None

    def test_status_live_pid(self, root):
        state = root / "state"
        state.mkdir(parents=True)
        (state / "daemon.pid").write_text(str(os.getpid()))
        s = AizeeDaemon.status(root)
        assert s["running"] is True
        assert s["pid"] == os.getpid()


class TestWatchAndSync:
    def test_check_no_settings(self, daemon):
        assert daemon._check_and_sync() is False

    def test_check_syncs_on_change(self, daemon, root):
        _write_settings(root, {"srv": {"enabled": False}})
        assert daemon._check_and_sync() is True
        # Second call: same mtime+hash -> no sync
        assert daemon._check_and_sync() is False

    def test_check_same_mtime(self, daemon, root):
        _write_settings(root, {})
        daemon._check_and_sync()
        assert daemon._check_and_sync() is False

    def test_check_same_content_new_mtime(self, daemon, root):
        _write_settings(root, {"srv": {"enabled": True}})
        daemon._check_and_sync()
        # Bump mtime without changing content
        p = root / "state" / "settings.json"
        os.utime(p, (p.stat().st_atime, p.stat().st_mtime + 5))
        assert daemon._check_and_sync() is False

    def test_devin_local_disable_enable(self, daemon, root):
        mcp = {"srv": {"enabled": False}}
        assert daemon._sync_devin_local(mcp) == 1
        local = json.loads((root / ".devin" / "mcp_config.local.json").read_text())
        assert local["mcpServers"]["srv"]["disabled"] is True
        # Enable again — empty entry is removed entirely
        assert daemon._sync_devin_local({"srv": {"enabled": True}}) == 1
        local = json.loads((root / ".devin" / "mcp_config.local.json").read_text())
        assert "disabled" not in local["mcpServers"].get("srv", {})

    def test_devin_local_no_change(self, daemon, root):
        assert daemon._sync_devin_local({}) == 0
        assert daemon._sync_devin_local({"srv": {"enabled": True}}) == 0

    def test_devin_local_corrupt_existing(self, daemon, root):
        p = root / ".devin" / "mcp_config.local.json"
        p.parent.mkdir(parents=True)
        p.write_text("{corrupt")
        daemon._sync_devin_local({"srv": {"enabled": False}})
        local = json.loads(p.read_text())
        assert local["mcpServers"]["srv"]["disabled"] is True

    def test_devin_local_non_dict_cfg(self, daemon, root):
        assert daemon._sync_devin_local({"srv": "not-a-dict"}) == 0

    def test_claude_settings_removes_disabled(self, daemon, root):
        claude = root / ".claude" / "settings.json"
        claude.parent.mkdir(parents=True)
        claude.write_text(json.dumps({
            "mcpServers": {"srv": {"command": "x"}, "keep": {"command": "y"}}
        }))
        assert daemon._sync_claude_settings({"srv": {"enabled": False}}) == 1
        cfg = json.loads(claude.read_text())
        assert "srv" not in cfg["mcpServers"]
        assert "keep" in cfg["mcpServers"]

    def test_claude_settings_restores_enabled(self, daemon, root):
        claude = root / ".claude" / "settings.json"
        claude.parent.mkdir(parents=True)
        claude.write_text(json.dumps({"mcpServers": {}}))
        # canonical config provides the definition
        canon = root / "aizee_mcp" / "config.json"
        canon.parent.mkdir(parents=True)
        canon.write_text(json.dumps({"mcpServers": {"srv": {"command": "x"}}}))
        assert daemon._sync_claude_settings({"srv": {"enabled": True}}) == 1
        cfg = json.loads(claude.read_text())
        assert cfg["mcpServers"]["srv"] == {"command": "x"}

    def test_claude_settings_missing(self, daemon, root):
        assert daemon._sync_claude_settings({"srv": {"enabled": False}}) == 0

    def test_claude_settings_corrupt(self, daemon, root):
        claude = root / ".claude" / "settings.json"
        claude.parent.mkdir(parents=True)
        claude.write_text("{bad")
        assert daemon._sync_claude_settings({"srv": {"enabled": False}}) == 0

    def test_cursor_removes_disabled(self, daemon, root):
        cur = root / ".cursor" / "mcp.json"
        cur.parent.mkdir(parents=True)
        cur.write_text(json.dumps({"mcpServers": {"srv": {}, "keep": {}}}))
        assert daemon._sync_cursor_mcp({"srv": {"enabled": False}}) == 1
        cfg = json.loads(cur.read_text())
        assert "srv" not in cfg["mcpServers"] and "keep" in cfg["mcpServers"]

    def test_cursor_enabled_noop(self, daemon, root):
        cur = root / ".cursor" / "mcp.json"
        cur.parent.mkdir(parents=True)
        cur.write_text(json.dumps({"mcpServers": {"srv": {}}}))
        assert daemon._sync_cursor_mcp({"srv": {"enabled": True}}) == 0

    def test_cursor_missing(self, daemon, root):
        assert daemon._sync_cursor_mcp({"srv": {"enabled": False}}) == 0

    def test_global_devin_disable_enable(self, daemon, root, monkeypatch):
        gdir = root / "appd"
        gdir.mkdir()
        gpath = gdir / "devin" / "mcp_config.json"
        gpath.parent.mkdir(parents=True)
        gpath.write_text(json.dumps({"mcpServers": {"srv": {"command": "x"}}}))
        if os.name == "nt":
            monkeypatch.setenv("APPDATA", str(gdir))
        else:
            monkeypatch.setattr(Path, "home", classmethod(lambda cls: gdir))
            # non-nt uses home/.config — skip global test there
            pytest.skip("global devin path differs on POSIX")
        assert daemon._sync_global_devin({"srv": {"enabled": False}}) == 1
        cfg = json.loads(gpath.read_text())
        assert cfg["mcpServers"]["srv"]["disabled"] is True
        assert daemon._sync_global_devin({"srv": {"enabled": True}}) == 1
        cfg = json.loads(gpath.read_text())
        assert "disabled" not in cfg["mcpServers"]["srv"]

    def test_global_devin_missing(self, daemon, monkeypatch):
        if os.name == "nt":
            monkeypatch.setenv("APPDATA", "Z:\\no\\such\\dir99")
        assert daemon._sync_global_devin({"s": {"enabled": False}}) == 0

    def test_sync_ide_configs_corrupt_settings(self, daemon, root):
        state = root / "state"
        state.mkdir(parents=True)
        (state / "settings.json").write_text("{corrupt")
        daemon._sync_ide_configs()  # warns, doesn't raise

    def test_sync_ide_configs_non_dict(self, daemon, root):
        _write_settings_raw(root, {"mcp_servers": ["not", "dict"]})
        daemon._sync_ide_configs()  # returns early

    def test_sync_increments_counter(self, daemon, root):
        _write_settings(root, {})
        daemon._sync_ide_configs()
        assert daemon._sync_count == 1
        daemon._sync_ide_configs()
        assert daemon._sync_count == 2


def _write_settings_raw(root: Path, data: dict) -> None:
    state = root / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "settings.json").write_text(json.dumps(data))


class TestHeartbeat:
    def test_write_heartbeat(self, daemon, root):
        daemon._state_dir.mkdir(parents=True, exist_ok=True)
        daemon._started_at = 1000.0
        daemon._write_heartbeat()
        health = json.loads(daemon._health_file.read_text())
        assert health["started_at"] == 1000.0
        assert health["pid"] == os.getpid()
        assert "platform" in health and "python" in health

    def test_heartbeat_before_start(self, daemon):
        daemon._state_dir.mkdir(parents=True, exist_ok=True)
        daemon._write_heartbeat()
        health = json.loads(daemon._health_file.read_text())
        assert health["uptime_seconds"] == 0


class TestLifecycle:
    def test_start_already_running(self, daemon):
        daemon._state_dir.mkdir(parents=True, exist_ok=True)
        daemon._pid_file.write_text(str(os.getpid()))  # live pid = us
        assert daemon.start() == 1  # refuses second instance

    def test_start_stale_pid_runs(self, daemon):
        daemon._state_dir.mkdir(parents=True, exist_ok=True)
        daemon._pid_file.write_text("99999999")  # dead pid
        with mock.patch.object(daemon, "_stop_event") as stop:
            stop.wait.side_effect = lambda *a: None
            rc = daemon.start()
        assert rc == 0
        assert not daemon._pid_file.exists()  # cleaned up

    def test_stop_no_pid(self, daemon):
        assert daemon.stop() is False

    def test_stop_dead_pid(self, daemon):
        daemon._state_dir.mkdir(parents=True, exist_ok=True)
        daemon._pid_file.write_text("99999999")
        assert daemon.stop() is False
        assert not daemon._pid_file.exists()

    def test_stop_live_pid_windows(self, daemon):
        daemon._state_dir.mkdir(parents=True, exist_ok=True)
        daemon._pid_file.write_text(str(os.getpid()))
        if os.name == "nt":
            with mock.patch.object(daemon, "_is_process_alive", return_value=True), \
                 mock.patch("runtime.daemon.subprocess.run") as run:
                assert daemon.stop() is True
                run.assert_called_once()
                assert "taskkill" in run.call_args[0][0][0]


class TestAutostart:
    def test_enable_windows(self, root):
        with mock.patch("runtime.daemon.platform.system", return_value="Windows"), \
             mock.patch("runtime.daemon.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
            r = AizeeDaemon.enable_autostart(root)
        assert r["platform"] == "windows" and r["enabled"] is True
        assert "schtasks" in run.call_args[0][0][0]

    def test_enable_windows_fails(self, root):
        with mock.patch("runtime.daemon.platform.system", return_value="Windows"), \
             mock.patch("runtime.daemon.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=1, stdout="", stderr="denied")
            r = AizeeDaemon.enable_autostart(root)
        assert r["enabled"] is False

    def test_disable_windows(self):
        with mock.patch("runtime.daemon.platform.system", return_value="Windows"), \
             mock.patch("runtime.daemon.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0, stdout="", stderr="")
            r = AizeeDaemon.disable_autostart()
        assert r["disabled"] is True

    def test_enable_linux(self, root, tmp_path):
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        with mock.patch("runtime.daemon.platform.system", return_value="Linux"), \
             mock.patch("runtime.daemon.Path.home", return_value=fake_home), \
             mock.patch("runtime.daemon.subprocess.run"):
            r = AizeeDaemon.enable_autostart(root)
        assert r["platform"] == "linux" and r["enabled"] is True
        svc = fake_home / ".config" / "systemd" / "user" / "aizee-daemon.service"
        assert svc.exists()
        assert "aiZee Background Daemon" in svc.read_text()

    def test_disable_linux(self, tmp_path):
        fake_home = tmp_path / "home"
        svc_dir = fake_home / ".config" / "systemd" / "user"
        svc_dir.mkdir(parents=True)
        (svc_dir / "aizee-daemon.service").write_text("[Unit]")
        with mock.patch("runtime.daemon.platform.system", return_value="Linux"), \
             mock.patch("runtime.daemon.Path.home", return_value=fake_home), \
             mock.patch("runtime.daemon.subprocess.run"):
            r = AizeeDaemon.disable_autostart()
        assert r["disabled"] is True
        assert not (svc_dir / "aizee-daemon.service").exists()

    def test_enable_macos(self, root, tmp_path):
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        with mock.patch("runtime.daemon.platform.system", return_value="Darwin"), \
             mock.patch("runtime.daemon.Path.home", return_value=fake_home), \
             mock.patch("runtime.daemon.subprocess.run"):
            r = AizeeDaemon.enable_autostart(root)
        assert r["platform"] == "macos" and r["enabled"] is True
        plist = fake_home / "Library" / "LaunchAgents" / "ai.aizee.daemon.plist"
        assert plist.exists()
        assert "ai.aizee.daemon" in plist.read_text()

    def test_disable_macos(self, tmp_path):
        fake_home = tmp_path / "home"
        plist = fake_home / "Library" / "LaunchAgents" / "ai.aizee.daemon.plist"
        plist.parent.mkdir(parents=True)
        plist.write_text("<plist/>")
        with mock.patch("runtime.daemon.platform.system", return_value="Darwin"), \
             mock.patch("runtime.daemon.Path.home", return_value=fake_home), \
             mock.patch("runtime.daemon.subprocess.run"):
            r = AizeeDaemon.disable_autostart()
        assert r["disabled"] is True
        assert not plist.exists()


class TestMain:
    def test_status_command(self, root, capsys):
        rc = main(["--root", str(root), "--status"])
        out = json.loads(capsys.readouterr().out)
        assert rc == 1 and out["running"] is False

    def test_stop_command(self, root, capsys):
        rc = main(["--root", str(root), "--stop"])
        assert rc == 1
        assert "No running daemon" in capsys.readouterr().out

    def test_bad_root(self, capsys):
        rc = main(["--root", "Z:\\no\\such\\root99", "--status"])
        assert rc == 1
        assert "ERROR" in capsys.readouterr().err

    def test_enable_autostart_cmd(self, root):
        with mock.patch("runtime.daemon.platform.system", return_value="Windows"), \
             mock.patch("runtime.daemon.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
            assert main(["--root", str(root), "--enable-autostart"]) == 0

    def test_disable_autostart_cmd(self, root):
        with mock.patch("runtime.daemon.platform.system", return_value="Windows"), \
             mock.patch("runtime.daemon.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0, stdout="", stderr="")
            assert main(["--root", str(root), "--disable-autostart"]) == 0

    def test_env_root(self, monkeypatch, root, capsys):
        monkeypatch.setenv("AIZEE_ROOT", str(root))
        rc = main(["--status"])
        assert rc == 1  # not running

    def test_daemon_error(self):
        err = DaemonError("x", {"k": 1})
        assert err.error_code == "DAEMON_ERROR"
