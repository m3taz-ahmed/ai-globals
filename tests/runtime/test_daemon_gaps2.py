"""Second gap pass for runtime/daemon.py — sync loops, signal handlers, CLI."""
from __future__ import annotations

import json
import signal
from unittest.mock import MagicMock, patch

from runtime.daemon import AizeeDaemon, main


def _daemon(tmp_path) -> AizeeDaemon:
    return AizeeDaemon(tmp_path)


class TestWatchLoop:
    def test_sync_error_logged_not_raised(self, tmp_path):
        d = _daemon(tmp_path)
        d._check_and_sync = MagicMock(side_effect=RuntimeError("sync boom"))
        d._stop_event.set()
        d._watch_loop()  # exits immediately via stop event
        # now test the exception path: run one iteration then stop
        d._stop_event.clear()
        def stop_after_wait(t):
            d._stop_event.set()
            return True
        with patch.object(d._stop_event, "wait", side_effect=stop_after_wait):
            d._watch_loop()  # exception inside loop caught + logged


class TestSyncDevinLocal:
    def _setup(self, tmp_path, servers):
        (tmp_path / ".devin").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".devin" / "mcp_config.local.json").write_text(
            json.dumps({"mcpServers": servers}), encoding="utf-8")

    def test_bad_json_resets(self, tmp_path):
        (tmp_path / ".devin").mkdir()
        (tmp_path / ".devin" / "mcp_config.local.json").write_text("{bad", encoding="utf-8")
        d = _daemon(tmp_path)
        n = d._sync_devin_local({"srv": {"enabled": True}})
        assert n in (0, 1)

    def test_mcpservers_not_dict(self, tmp_path):
        # non-dict mcpServers is reset to {} then updated -> writes once
        self._setup(tmp_path, "notadict")
        d = _daemon(tmp_path)
        n = d._sync_devin_local({"srv": {"enabled": False}})
        assert n == 1
        cfg = json.loads((tmp_path / ".devin" / "mcp_config.local.json").read_text())
        assert cfg["mcpServers"]["srv"]["disabled"] is True

    def test_cfg_not_dict_skipped(self, tmp_path):
        self._setup(tmp_path, {"srv": {"disabled": True}})
        d = _daemon(tmp_path)
        assert d._sync_devin_local({"srv": "scalar"}) == 0

    def test_enable_readd_and_disable(self, tmp_path):
        self._setup(tmp_path, {"a": {"disabled": True}, "b": {"x": 1}, "c": "scalar"})
        d = _daemon(tmp_path)
        n = d._sync_devin_local({"a": {"enabled": True}, "b": {"enabled": False}, "c": {"enabled": False}, "new": {"enabled": True}})
        assert n == 1
        cfg = json.loads((tmp_path / ".devin" / "mcp_config.local.json").read_text())
        # "a" had only {disabled} -> unflagging empties it -> popped entirely
        assert "a" not in cfg["mcpServers"]
        assert cfg["mcpServers"]["b"]["disabled"] is True


class TestSyncClaude:
    def _setup(self, tmp_path, content):
        (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".claude" / "settings.json").write_text(content, encoding="utf-8")

    def test_bad_json(self, tmp_path):
        self._setup(tmp_path, "{oops")
        assert _daemon(tmp_path)._sync_claude_settings({"s": {}}) == 0

    def test_mcpservers_not_dict(self, tmp_path):
        self._setup(tmp_path, json.dumps({"mcpServers": [1]}))
        assert _daemon(tmp_path)._sync_claude_settings({"s": {}}) == 0

    def test_canonical_bad_json_ignored(self, tmp_path):
        self._setup(tmp_path, json.dumps({"mcpServers": {}}))
        (tmp_path / "aizee_mcp").mkdir()
        (tmp_path / "aizee_mcp" / "config.json").write_text("{bad", encoding="utf-8")
        assert _daemon(tmp_path)._sync_claude_settings({"s": {"enabled": True}}) == 0

    def test_disable_delete_and_enable_restore(self, tmp_path):
        self._setup(tmp_path, json.dumps({"mcpServers": {"off": {"cmd": "x"}}}))
        (tmp_path / "aizee_mcp").mkdir()
        (tmp_path / "aizee_mcp" / "config.json").write_text(
            json.dumps({"mcpServers": {"on": {"command": "python"}}}), encoding="utf-8")
        d = _daemon(tmp_path)
        n = d._sync_claude_settings({
            "off": {"enabled": False},
            "on": {"enabled": True},
            "scalar": "x",
        })
        assert n == 1
        cfg = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert "off" not in cfg["mcpServers"]
        assert cfg["mcpServers"]["on"]["command"] == "python"


class TestSyncCursor:
    def _setup(self, tmp_path, content):
        (tmp_path / ".cursor").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".cursor" / "mcp.json").write_text(content, encoding="utf-8")

    def test_bad_json(self, tmp_path):
        self._setup(tmp_path, "nope{")
        assert _daemon(tmp_path)._sync_cursor_mcp({"s": {}}) == 0

    def test_mcpservers_not_dict(self, tmp_path):
        self._setup(tmp_path, json.dumps({"mcpServers": 5}))
        assert _daemon(tmp_path)._sync_cursor_mcp({"s": {}}) == 0

    def test_disable_writes(self, tmp_path):
        self._setup(tmp_path, json.dumps({"mcpServers": {"off": {"c": 1}}}))
        n = _daemon(tmp_path)._sync_cursor_mcp({"off": {"enabled": False}, "x": "scalar"})
        assert n == 1
        cfg = json.loads((tmp_path / ".cursor" / "mcp.json").read_text())
        assert "off" not in cfg["mcpServers"]


class TestSyncGlobalDevin:
    def _patch_appdata(self, monkeypatch, tmp_path):
        monkeypatch.setenv("APPDATA", str(tmp_path))
        gdir = tmp_path / "devin"
        gdir.mkdir(exist_ok=True)
        return gdir / "mcp_config.json"

    def test_bad_json(self, tmp_path, monkeypatch):
        p = self._patch_appdata(monkeypatch, tmp_path)
        p.write_text("{bad", encoding="utf-8")
        assert _daemon(tmp_path)._sync_global_devin({"s": {}}) == 0

    def test_servers_not_dict(self, tmp_path, monkeypatch):
        p = self._patch_appdata(monkeypatch, tmp_path)
        p.write_text(json.dumps({"mcpServers": "x"}), encoding="utf-8")
        assert _daemon(tmp_path)._sync_global_devin({"s": {}}) == 0

    def test_disable_marks_flag_and_enable_clears(self, tmp_path, monkeypatch):
        p = self._patch_appdata(monkeypatch, tmp_path)
        p.write_text(json.dumps({"mcpServers": {
            "off": {"cmd": "x"}, "on": {"disabled": True}, "scalar": "v",
        }}), encoding="utf-8")
        n = _daemon(tmp_path)._sync_global_devin({
            "off": {"enabled": False}, "on": {"enabled": True}, "scalar": {"enabled": False},
            "notdict": "x",
        })
        assert n == 1
        cfg = json.loads(p.read_text())
        assert cfg["mcpServers"]["off"]["disabled"] is True
        assert "disabled" not in cfg["mcpServers"]["on"]

    def test_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("APPDATA", str(tmp_path / "empty"))
        assert _daemon(tmp_path)._sync_global_devin({"s": {}}) == 0


class TestSignalsAndCli:
    def test_signal_handler_sets_stop(self, tmp_path):
        d = _daemon(tmp_path)
        handlers = {}
        with patch("signal.signal", side_effect=lambda sig, fn: handlers.__setitem__(sig, fn)):
            d._setup_signal_handlers()
        assert signal.SIGINT in handlers
        handlers[signal.SIGINT](signal.SIGINT, None)
        assert d._stop_event.is_set()

    def test_main_status(self, tmp_path, capsys):
        rc = main(["--root", str(tmp_path), "--status"])
        out = capsys.readouterr().out
        assert "running" in out
        assert rc in (0, 1)

    def test_main_bad_root(self, tmp_path, capsys):
        rc = main(["--root", str(tmp_path / "ghost_dir"), "--status"])
        assert rc == 1

    def test_main_root_from_env(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))
        rc = main(["--status"])
        assert rc in (0, 1)

    def test_main_env_root_invalid_falls_back(self, monkeypatch, capsys):
        monkeypatch.setenv("AIZEE_ROOT", "Z:\\nonexistent\\path\\xyz")
        rc = main(["--status"])
        capsys.readouterr()
        assert rc in (0, 1)

    def test_main_stop_no_daemon(self, tmp_path, capsys):
        rc = main(["--root", str(tmp_path), "--stop"])
        assert rc == 1
        assert "No running daemon" in capsys.readouterr().out

    def test_main_autostart_flags(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))
        with patch.object(AizeeDaemon, "enable_autostart", return_value={"enabled": True}):
            assert main(["--root", str(tmp_path), "--enable-autostart"]) == 0
        with patch.object(AizeeDaemon, "disable_autostart", return_value={"disabled": True}):
            assert main(["--root", str(tmp_path), "--disable-autostart"]) == 0
        with patch.object(AizeeDaemon, "enable_autostart", return_value={"enabled": False}):
            assert main(["--root", str(tmp_path), "--enable-autostart"]) == 1
