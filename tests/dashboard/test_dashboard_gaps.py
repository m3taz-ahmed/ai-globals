"""Gap-coverage tests for dashboard/server.py — settings API + IDE sync helpers."""

from __future__ import annotations

import json
import tempfile
import threading
import time
import urllib.error
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from dashboard.server import (
    DashboardHandler,
    ThreadingHTTPServer,
    _dashboard_token,
    _sync_claude_mcp_settings,
    _sync_devin_mcp_local,
    _sync_ide_mcp_configs,
    _write_dashboard_token_file,
)

pytestmark = pytest.mark.slow


def _serve(tmp_root: Path, monkeypatch: pytest.MonkeyPatch):
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_root / sub).mkdir(parents=True, exist_ok=True)
    (tmp_root / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    monkeypatch.setenv("AIZEE_ROOT", str(tmp_root))
    monkeypatch.setenv("AGENT_OS_DASHBOARD_ALLOW_NO_TOKEN", "1")
    server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, port


def _post(port: int, path: str, payload: dict):
    req = Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Requested-With": "AIOS-Dashboard"},
        method="POST",
    )
    return urlopen(req)


def _post_raw(port: int, path: str, payload: dict):
    """POST that returns (status, body) even on HTTP errors."""
    req = Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Requested-With": "AIOS-Dashboard"},
        method="POST",
    )
    try:
        with urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


class TestSettingsApi:
    def test_settings_get_all(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_set_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            with urlopen(f"http://127.0.0.1:{port}/api/settings") as resp:
                data = json.loads(resp.read().decode())
            assert "version" in data or "budget" in data
        finally:
            server.shutdown()

    def test_settings_get_section(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_setsec_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            with urlopen(f"http://127.0.0.1:{port}/api/settings?section=budget") as resp:
                data = json.loads(resp.read().decode())
            assert isinstance(data, dict)
        finally:
            server.shutdown()

    def test_settings_get_bad_section(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_setbad_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            with pytest.raises(urllib.error.HTTPError) as exc:
                urlopen(f"http://127.0.0.1:{port}/api/settings?section=nope")
            assert exc.value.code == 400
        finally:
            server.shutdown()

    def test_settings_update(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_upd_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            with _post(port, "/api/settings",
                       {"section": "telemetry", "data": {"enabled": False}}) as resp:
                data = json.loads(resp.read().decode())
            assert data["ok"] is True and data["data"]["enabled"] is False
        finally:
            server.shutdown()

    def test_settings_update_bad_section(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_updbad_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            status, _ = _post_raw(port, "/api/settings",
                                  {"section": "nope", "data": {}})
            assert status == 400
        finally:
            server.shutdown()

    def test_settings_update_bad_data(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_updd_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            status, _ = _post_raw(port, "/api/settings",
                                  {"section": "telemetry", "data": "nope"})
            assert status == 400
        finally:
            server.shutdown()

    def test_settings_update_invalid(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_updi_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            status, _body = _post_raw(port, "/api/settings",
                                     {"section": "telemetry", "data": {"enabled": "x"}})
            assert status == 400
        finally:
            server.shutdown()

    def test_settings_update_mcp_syncs(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_mcp_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            with _post(port, "/api/settings",
                       {"section": "mcp_servers",
                        "data": {"srv1": {"enabled": False}}}) as resp:
                data = json.loads(resp.read().decode())
            assert data["ok"] is True
            # devin overlay written
            local = tmp / ".devin" / "mcp_config.local.json"
            assert local.exists()
            assert json.loads(local.read_text())["mcpServers"]["srv1"]["disabled"] is True
        finally:
            server.shutdown()

    def test_settings_defaults(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_def_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            with urlopen(f"http://127.0.0.1:{port}/api/settings/defaults") as resp:
                data = json.loads(resp.read().decode())
            assert data["ok"] is True
            with urlopen(f"http://127.0.0.1:{port}/api/settings/defaults?section=budget") as resp:
                d2 = json.loads(resp.read().decode())
            assert d2["ok"] is True
        finally:
            server.shutdown()

    def test_settings_defaults_bad_section(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_defb_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            with pytest.raises(urllib.error.HTTPError) as exc:
                urlopen(f"http://127.0.0.1:{port}/api/settings/defaults?section=nope")
            assert exc.value.code == 400
        finally:
            server.shutdown()

    def test_settings_reset_all(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_rst_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            _post(port, "/api/settings",
                  {"section": "telemetry", "data": {"enabled": False}}).read()
            with _post(port, "/api/settings/reset", {}) as resp:
                data = json.loads(resp.read().decode())
            assert data["ok"] is True
            # verify reset took effect
            with urlopen(f"http://127.0.0.1:{port}/api/settings?section=telemetry") as resp:
                d = json.loads(resp.read().decode())
            assert d["enabled"] is True
        finally:
            server.shutdown()

    def test_settings_reset_section(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_rsts_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            _post(port, "/api/settings",
                  {"section": "telemetry", "data": {"enabled": False}}).read()
            with _post(port, "/api/settings/reset", {"section": "telemetry"}) as resp:
                data = json.loads(resp.read().decode())
            assert data["ok"] is True
        finally:
            server.shutdown()

    def test_settings_reset_bad_section(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_rstb_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            status, _ = _post_raw(port, "/api/settings/reset", {"section": "nope"})
            assert status == 400
        finally:
            server.shutdown()

    def test_settings_mcp_status(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_mcps_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            with urlopen(f"http://127.0.0.1:{port}/api/settings/mcp-status") as resp:
                data = json.loads(resp.read().decode())
            assert "servers" in data and "categories" in data
        finally:
            server.shutdown()

    def test_settings_restart(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_restart_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            time.sleep(0.1)
            with _post(port, "/api/settings/restart", {}) as resp:
                data = json.loads(resp.read().decode())
            assert data["ok"] is True
        finally:
            server.shutdown()


class TestIdeSync:
    def test_devin_local_disabled_flag(self, tmp_path):
        _sync_devin_mcp_local(tmp_path, {"srv": {"enabled": False}})
        data = json.loads(
            (tmp_path / ".devin" / "mcp_config.local.json").read_text())
        assert data["mcpServers"]["srv"]["disabled"] is True

    def test_devin_local_reenable(self, tmp_path):
        lp = tmp_path / ".devin" / "mcp_config.local.json"
        lp.parent.mkdir(parents=True)
        lp.write_text(json.dumps({"mcpServers": {"srv": {"disabled": True}}}))
        _sync_devin_mcp_local(tmp_path, {"srv": {"enabled": True}})
        data = json.loads(lp.read_text())
        # Entry becomes empty after popping "disabled" → removed entirely
        assert "srv" not in data["mcpServers"]

    def test_devin_corrupt_overlay(self, tmp_path):
        lp = tmp_path / ".devin" / "mcp_config.local.json"
        lp.parent.mkdir(parents=True)
        lp.write_text("{corrupt")
        _sync_devin_mcp_local(tmp_path, {"srv": {"enabled": False}})
        assert json.loads(lp.read_text())["mcpServers"]["srv"]["disabled"] is True

    def test_devin_non_dict_cfg_skipped(self, tmp_path):
        _sync_devin_mcp_local(tmp_path, {"srv": "notdict"})
        data = json.loads(
            (tmp_path / ".devin" / "mcp_config.local.json").read_text())
        assert "srv" not in data["mcpServers"]

    def test_devin_empty_entry_removed(self, tmp_path):
        lp = tmp_path / ".devin" / "mcp_config.local.json"
        lp.parent.mkdir(parents=True)
        lp.write_text(json.dumps({"mcpServers": {"srv": {"disabled": True}}}))
        # Re-enable → existing becomes {} → removed
        _sync_devin_mcp_local(tmp_path, {"srv": {"enabled": True}})
        data = json.loads(lp.read_text())
        assert "srv" not in data["mcpServers"] or not data["mcpServers"]["srv"].get("disabled")

    def test_claude_no_file_noop(self, tmp_path):
        _sync_claude_mcp_settings(tmp_path, {"srv": {"enabled": False}})

    def test_claude_removes_disabled(self, tmp_path):
        cp = tmp_path / ".claude" / "settings.json"
        cp.parent.mkdir(parents=True)
        cp.write_text(json.dumps({"mcpServers": {"srv": {"x": 1}, "keep": {}}}))
        _sync_claude_mcp_settings(tmp_path, {"srv": {"enabled": False}})
        data = json.loads(cp.read_text())
        assert "srv" not in data["mcpServers"] and "keep" in data["mcpServers"]

    def test_claude_restores_enabled(self, tmp_path):
        cp = tmp_path / ".claude" / "settings.json"
        cp.parent.mkdir(parents=True)
        cp.write_text(json.dumps({"mcpServers": {}}))
        canon = tmp_path / "aizee_mcp" / "config.json"
        canon.parent.mkdir(parents=True)
        canon.write_text(json.dumps({"mcpServers": {"srv": {"cmd": "x"}}}))
        _sync_claude_mcp_settings(tmp_path, {"srv": {"enabled": True}})
        data = json.loads(cp.read_text())
        assert data["mcpServers"]["srv"] == {"cmd": "x"}

    def test_claude_corrupt_noop(self, tmp_path):
        cp = tmp_path / ".claude" / "settings.json"
        cp.parent.mkdir(parents=True)
        cp.write_text("{bad")
        _sync_claude_mcp_settings(tmp_path, {"srv": {"enabled": False}})

    def test_claude_no_mcpservers_key(self, tmp_path):
        cp = tmp_path / ".claude" / "settings.json"
        cp.parent.mkdir(parents=True)
        cp.write_text(json.dumps({"other": 1}))
        _sync_claude_mcp_settings(tmp_path, {"srv": {"enabled": False}})

    def test_sync_both(self, tmp_path):
        _sync_ide_mcp_configs(tmp_path, {"srv": {"enabled": False}})
        assert (tmp_path / ".devin" / "mcp_config.local.json").exists()


class TestDashboardToken:
    def test_env_token(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIZEE_DASHBOARD_TOKEN", "tok123")
        assert _dashboard_token(tmp_path) == "tok123"

    def test_legacy_env(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AIZEE_DASHBOARD_TOKEN", raising=False)
        monkeypatch.setenv("AGENT_OS_DASHBOARD_TOKEN", "legacy")
        assert _dashboard_token(tmp_path) == "legacy"

    def test_stored_token(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AIZEE_DASHBOARD_TOKEN", raising=False)
        monkeypatch.delenv("AGENT_OS_DASHBOARD_TOKEN", raising=False)
        sf = tmp_path / "state" / "dashboard.token"
        sf.parent.mkdir(parents=True)
        sf.write_text("stored-tok")
        assert _dashboard_token(tmp_path) == "stored-tok"

    def test_no_token(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AIZEE_DASHBOARD_TOKEN", raising=False)
        monkeypatch.delenv("AGENT_OS_DASHBOARD_TOKEN", raising=False)
        assert _dashboard_token(tmp_path) is None

    def test_write_token_file(self, tmp_path):
        p = _write_dashboard_token_file(tmp_path, "tok")
        assert p.read_text().strip() == "tok"
        assert p.parent.name == "state"


class TestLogMessage:
    def test_error_logged(self, capsys):
        DashboardHandler.log_message(None, '"GET /x" 500 -')
        assert "dashboard" in capsys.readouterr().err

    def test_ok_silenced(self, capsys):
        DashboardHandler.log_message(None, '"GET /x" 200 -')
        assert capsys.readouterr().err == ""

    def test_bad_format(self, capsys):
        DashboardHandler.log_message(None, "%d %d", "only-one")
        # format raises TypeError -> return, nothing printed
        assert capsys.readouterr().err == ""
