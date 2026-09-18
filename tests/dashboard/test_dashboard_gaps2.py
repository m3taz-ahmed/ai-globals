"""Gap-coverage tests round 2 for dashboard/server.py — HTTP edges, rate limit, SSE."""

from __future__ import annotations

import json
import socket
import tempfile
import threading
import time
import types
import urllib.error
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

import dashboard.server as srv
from dashboard.server import (
    DashboardHandler,
    ThreadingHTTPServer,
    _check_rate_limit,
    _client_ip,
    _dashboard_token,
    _env_float,
    _env_int,
    _sync_claude_mcp_settings,
    _sync_devin_mcp_local,
    _valid_action,
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
    monkeypatch.chdir(tmp_root)
    server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    return server, port


def _get(port: int, path: str, headers: dict | None = None):
    req = Request(f"http://127.0.0.1:{port}{path}", headers=headers or {})
    try:
        with urlopen(req) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace"), dict(e.headers)


def _post(port: int, path: str, payload, raw_body: bytes | None = None,
          extra_headers: dict | None = None):
    data = raw_body if raw_body is not None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Requested-With": "AIOS-Dashboard"}
    headers.update(extra_headers or {})
    req = Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers, method="POST")
    try:
        with urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


class TestEnvHelpers:
    def test_env_int_garbage(self, monkeypatch):
        monkeypatch.setenv("X_INT", "notanint")
        assert _env_int("X_INT", default=7) == 7

    def test_env_int_clamped(self, monkeypatch):
        monkeypatch.setenv("X_INT", "999999")
        assert _env_int("X_INT", default=5, maximum=100) == 100

    def test_env_float_garbage(self, monkeypatch):
        monkeypatch.setenv("X_F", "abc")
        assert _env_float("X_F", default=2.5) == 2.5

    def test_env_float_minimum(self, monkeypatch):
        monkeypatch.setenv("X_F", "0")
        assert _env_float("X_F", default=2.5, minimum=0.5) == 0.5

    def test_valid_action(self):
        assert _valid_action("run_workflow")
        assert _valid_action("graphify query")
        assert not _valid_action("bad;action")
        assert not _valid_action(123)


class TestRateLimit:
    def test_disabled_when_zero(self, monkeypatch):
        monkeypatch.setattr(srv, "_rate_limit", 0)
        assert _check_rate_limit("9.9.9.9") is True

    def test_exceeded(self, monkeypatch):
        monkeypatch.setattr(srv, "_rate_limit", 2)
        srv._rate_state.clear()
        assert _check_rate_limit("1.1.1.1")
        assert _check_rate_limit("1.1.1.1")
        assert not _check_rate_limit("1.1.1.1")

    def test_window_reset(self, monkeypatch):
        monkeypatch.setattr(srv, "_rate_limit", 1)
        srv._rate_state.clear()
        # Seed a stale window — next call resets count and is allowed again.
        srv._rate_state["2.2.2.2"] = (99, time.time() - 9999)
        assert _check_rate_limit("2.2.2.2")

    def test_eviction(self, monkeypatch):
        monkeypatch.setattr(srv, "_rate_limit", 5)
        monkeypatch.setattr(srv, "_rate_max_entries", 2)
        monkeypatch.setattr(srv, "_rate_window", 60.0)
        srv._rate_state.clear()
        for i in range(5):
            _check_rate_limit(f"10.0.0.{i}")
        # eviction should have trimmed the state map
        assert len(srv._rate_state) <= 5

    def test_eviction_stale_entries(self, monkeypatch):
        monkeypatch.setattr(srv, "_rate_limit", 5)
        monkeypatch.setattr(srv, "_rate_max_entries", 2)
        monkeypatch.setattr(srv, "_rate_window", 60.0)
        srv._rate_state.clear()
        # Pre-seed stale entries (window_start far in the past)
        srv._rate_state["old1"] = (5, 0.0)
        srv._rate_state["old2"] = (5, 0.0)
        _check_rate_limit("new-ip")
        assert "old1" not in srv._rate_state


class TestClientIp:
    def _handler(self, ip: str, xff: str = ""):
        h = types.SimpleNamespace()
        h.client_address = (ip, 1234)
        h.headers = {"X-Forwarded-For": xff} if xff else {}
        return h

    def test_direct(self, monkeypatch):
        monkeypatch.setattr(srv, "_TRUSTED_PROXIES", {"10.0.0.1"})
        assert _client_ip(self._handler("8.8.8.8")) == "8.8.8.8"

    def test_via_proxy(self, monkeypatch):
        monkeypatch.setattr(srv, "_TRUSTED_PROXIES", {"10.0.0.1"})
        h = self._handler("10.0.0.1", "1.2.3.4, 10.0.0.1")
        assert _client_ip(h) == "1.2.3.4"

    def test_via_proxy_invalid_candidate(self, monkeypatch):
        monkeypatch.setattr(srv, "_TRUSTED_PROXIES", {"10.0.0.1"})
        h = self._handler("10.0.0.1", "5.6.7.8, garbage, 10.0.0.1")
        assert _client_ip(h) == "5.6.7.8"

    def test_all_proxies_fallback(self, monkeypatch):
        monkeypatch.setattr(srv, "_TRUSTED_PROXIES", {"10.0.0.1", "10.0.0.2"})
        h = self._handler("10.0.0.1", "10.0.0.2, 10.0.0.1")
        assert _client_ip(h) == "10.0.0.2"

    def test_all_proxies_invalid_first(self, monkeypatch):
        monkeypatch.setattr(srv, "_TRUSTED_PROXIES", {"10.0.0.1"})
        h = self._handler("10.0.0.1", "not-an-ip")
        assert _client_ip(h) == "10.0.0.1"


class TestDashboardToken:
    def test_env_token(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIZEE_DASHBOARD_TOKEN", "tok123")
        assert _dashboard_token(tmp_path) == "tok123"

    def test_legacy_env(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AIZEE_DASHBOARD_TOKEN", raising=False)
        monkeypatch.setenv("AGENT_OS_DASHBOARD_TOKEN", "legacy")
        assert _dashboard_token(tmp_path) == "legacy"

    def test_stored_token(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AIZEE_DASHBOARD_TOKEN", raising=False)
        monkeypatch.delenv("AGENT_OS_DASHBOARD_TOKEN", raising=False)
        (tmp_path / "state").mkdir()
        (tmp_path / "state" / "dashboard.token").write_text("stored-tok\n")
        assert _dashboard_token(tmp_path) == "stored-tok"

    def test_empty_stored(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AIZEE_DASHBOARD_TOKEN", raising=False)
        monkeypatch.delenv("AGENT_OS_DASHBOARD_TOKEN", raising=False)
        (tmp_path / "state").mkdir()
        (tmp_path / "state" / "dashboard.token").write_text("  \n")
        assert _dashboard_token(tmp_path) is None

    def test_write_token_file(self, tmp_path):
        p = _write_dashboard_token_file(tmp_path, "abc123")
        assert p.read_text() == "abc123"

    def test_write_token_getlogin_fallback(self, monkeypatch, tmp_path):
        import os as _os
        monkeypatch.setattr(_os, "getlogin", lambda: (_ for _ in ()).throw(OSError("no login")))
        p = _write_dashboard_token_file(tmp_path, "xyz")
        assert p.exists()


class TestSyncHelpers:
    def test_devin_non_dict_cfg(self, tmp_path):
        _sync_devin_mcp_local(tmp_path, {"s1": "notdict"})
        data = json.loads((tmp_path / ".devin/mcp_config.local.json").read_text())
        assert data["mcpServers"] == {}

    def test_devin_bad_existing_json(self, tmp_path):
        d = tmp_path / ".devin"
        d.mkdir()
        (d / "mcp_config.local.json").write_text("{bad json")
        _sync_devin_mcp_local(tmp_path, {"s1": {"enabled": False}})
        data = json.loads((d / "mcp_config.local.json").read_text())
        assert data["mcpServers"]["s1"]["disabled"] is True

    def test_devin_mcp_servers_not_dict(self, tmp_path):
        d = tmp_path / ".devin"
        d.mkdir()
        (d / "mcp_config.local.json").write_text(json.dumps({"mcpServers": "nope"}))
        _sync_devin_mcp_local(tmp_path, {"s1": {"enabled": False}})
        data = json.loads((d / "mcp_config.local.json").read_text())
        assert data["mcpServers"]["s1"]["disabled"] is True

    def test_devin_existing_non_dict_entry(self, tmp_path):
        d = tmp_path / ".devin"
        d.mkdir()
        (d / "mcp_config.local.json").write_text(
            json.dumps({"mcpServers": {"s1": "str"}}))
        _sync_devin_mcp_local(tmp_path, {"s1": {"enabled": False}})
        data = json.loads((d / "mcp_config.local.json").read_text())
        assert data["mcpServers"]["s1"]["disabled"] is True

    def test_claude_missing_file(self, tmp_path):
        _sync_claude_mcp_settings(tmp_path, {"s": {"enabled": False}})

    def test_claude_bad_json(self, tmp_path):
        d = tmp_path / ".claude"
        d.mkdir()
        (d / "settings.json").write_text("{bad")
        _sync_claude_mcp_settings(tmp_path, {"s": {"enabled": False}})

    def test_claude_no_mcp_servers(self, tmp_path):
        d = tmp_path / ".claude"
        d.mkdir()
        (d / "settings.json").write_text(json.dumps({"other": 1}))
        _sync_claude_mcp_settings(tmp_path, {"s": {"enabled": False}})

    def test_claude_disable_and_restore(self, tmp_path):
        d = tmp_path / ".claude"
        d.mkdir()
        (d / "settings.json").write_text(json.dumps(
            {"mcpServers": {"srv": {"command": "x"}, "keep": {"command": "y"}}}))
        # canonical source for restore
        mcpd = tmp_path / "aizee_mcp"
        mcpd.mkdir()
        (mcpd / "config.json").write_text(json.dumps(
            {"mcpServers": {"srv": {"command": "x"}, "new": {"command": "z"}}}))
        _sync_claude_mcp_settings(tmp_path, {"srv": {"enabled": False}})
        data = json.loads((d / "settings.json").read_text())
        assert "srv" not in data["mcpServers"]
        assert "keep" in data["mcpServers"]
        # re-enable + restore "new" from canonical
        _sync_claude_mcp_settings(tmp_path, {"srv": {"enabled": True}, "new": {"enabled": True}})
        data = json.loads((d / "settings.json").read_text())
        assert data["mcpServers"]["srv"]["command"] == "x"
        assert data["mcpServers"]["new"]["command"] == "z"

    def test_claude_canonical_from_devin(self, tmp_path):
        d = tmp_path / ".claude"
        d.mkdir()
        (d / "settings.json").write_text(json.dumps({"mcpServers": {}}))
        dd = tmp_path / ".devin"
        dd.mkdir()
        (dd / "mcp_config.json").write_text(json.dumps(
            {"mcpServers": {"devinonly": {"command": "d"}}}))
        _sync_claude_mcp_settings(tmp_path, {"devinonly": {"enabled": True}})
        data = json.loads((d / "settings.json").read_text())
        assert data["mcpServers"]["devinonly"]["command"] == "d"

    def test_claude_bad_canonical(self, tmp_path):
        d = tmp_path / ".claude"
        d.mkdir()
        (d / "settings.json").write_text(json.dumps({"mcpServers": {}}))
        mcpd = tmp_path / "aizee_mcp"
        mcpd.mkdir()
        (mcpd / "config.json").write_text("{bad")
        _sync_claude_mcp_settings(tmp_path, {"s": {"enabled": True}})

    def test_claude_non_dict_cfg(self, tmp_path):
        d = tmp_path / ".claude"
        d.mkdir()
        (d / "settings.json").write_text(json.dumps({"mcpServers": {}}))
        _sync_claude_mcp_settings(tmp_path, {"s": "str"})


class TestHttpEdges:
    def test_404(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_404_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _, _ = _get(port, "/api/nonexistent")
            assert status == 404
        finally:
            server.shutdown()

    def test_options(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_opt_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            req = Request(f"http://127.0.0.1:{port}/api/status", method="OPTIONS")
            with urlopen(req) as resp:
                assert resp.status == 204
        finally:
            server.shutdown()

    def test_csrf_fail(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_csrf_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            req = Request(
                f"http://127.0.0.1:{port}/api/settings",
                data=b'{"section":"telemetry","data":{}}',
                headers={"Content-Type": "application/json"}, method="POST")
            with pytest.raises(urllib.error.HTTPError) as exc:
                urlopen(req)
            assert exc.value.code == 403
        finally:
            server.shutdown()

    def test_bad_content_length(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_cl_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=5)
            s.sendall(b"POST /api/settings HTTP/1.1\r\nHost: x\r\n"
                      b"X-Requested-With: AIOS-Dashboard\r\n"
                      b"Content-Length: abc\r\n\r\n")
            resp = s.recv(4096).decode()
            s.close()
            assert "400" in resp.split("\r\n")[0]
        finally:
            server.shutdown()

    def test_oversized_body(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_big_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=5)
            s.sendall(b"POST /api/settings HTTP/1.1\r\nHost: x\r\n"
                      b"X-Requested-With: AIOS-Dashboard\r\n"
                      b"Content-Length: 99999999\r\n\r\n")
            resp = s.recv(4096).decode()
            s.close()
            assert "413" in resp.split("\r\n")[0]
        finally:
            server.shutdown()

    def test_bad_json_body(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_bj_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _ = _post(port, "/api/settings", None, raw_body=b"{not json")
            assert status == 400
        finally:
            server.shutdown()

    def test_non_dict_body(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_nd_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _ = _post(port, "/api/settings", None, raw_body=b"[1,2,3]")
            assert status == 400
        finally:
            server.shutdown()

    def test_check_invalid_action(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_chk_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _, _ = _get(port, "/api/check?action=bad;cmd")
            assert status == 400
        finally:
            server.shutdown()

    def test_check_approve_rejected(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_appr_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, body, _ = _get(port, "/api/check?action=run_x&approve=1")
            assert status == 400
            assert "not allowed" in body
        finally:
            server.shutdown()

    def test_check_ok(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_chk2_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, body, _ = _get(port, "/api/check?action=Read")
            assert status == 200
            assert json.loads(body)
        finally:
            server.shutdown()

    def test_memory_search_bad_limit(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_ms_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, body, _ = _get(port, "/api/memory/search?q=x&limit=abc")
            assert status == 200
            assert json.loads(body) == []
        finally:
            server.shutdown()

    def test_policy_test_bad_action(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_pt_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _ = _post(port, "/api/policy/test", {"action": "bad;act"})
            assert status == 400
        finally:
            server.shutdown()

    def test_policy_test_ok(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_pt2_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, body = _post(port, "/api/policy/test", {"action": "Read", "args": "non-dict"})
            assert status == 200
            assert json.loads(body)
        finally:
            server.shutdown()

    def test_workflow_run_missing_id(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_wf_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _ = _post(port, "/api/workflow/run", {})
            assert status == 400
        finally:
            server.shutdown()

    def test_saga_run_missing_id(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_sr_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _ = _post(port, "/api/saga/run", {})
            assert status == 400
        finally:
            server.shutdown()

    def test_saga_run_bad_steps(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_srs_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _ = _post(port, "/api/saga/run", {"saga_id": "s1", "steps": "nope"})
            assert status == 400
        finally:
            server.shutdown()

    def test_saga_get_invalid_id(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_sg_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _, _ = _get(port, "/api/saga/%2E%2E%2Fetc")
            assert status == 400
        finally:
            server.shutdown()

    def test_saga_get_too_long(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_sgl_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _, _ = _get(port, "/api/saga/" + "a" * 300)
            assert status == 400
        finally:
            server.shutdown()

    def test_saga_get_not_found(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_sgn_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _, _ = _get(port, "/api/saga/nope123")
            assert status == 404
        finally:
            server.shutdown()

    def test_chat_missing_message(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_cm_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _ = _post(port, "/api/chat", {"message": 5})
            assert status == 400
        finally:
            server.shutdown()

    def test_chat_bad_session_id(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_cs_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _ = _post(port, "/api/chat", {"message": "hi", "session_id": 9})
            assert status == 400
        finally:
            server.shutdown()

    def test_telemetry_bad_limit(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_tl_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _, _ = _get(port, "/api/telemetry?limit=abc")
            assert status == 400
        finally:
            server.shutdown()

    def test_audit_bad_limit_and_corrupt(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_al_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            (tmp / "state" / "audit.log").write_text(
                '{"a":1}\nnot-json\n\n{"b":2}\n')
            status, body, _ = _get(port, "/api/audit?limit=abc")
            assert status == 200
            data = json.loads(body)
            assert len(data) == 2
        finally:
            server.shutdown()

    def test_tracing_bad_limit_and_corrupt(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_tr_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            (tmp / "state" / "spans.jsonl").write_text(
                '{"s":1}\nbad-line\n{"s":2}\n')
            status, body, _ = _get(port, "/api/tracing?limit=abc")
            assert status == 200
            data = json.loads(body)
            assert len(data) == 2
        finally:
            server.shutdown()

    def test_lint_bad_code_type(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_lc_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _ = _post(port, "/api/lint", {"code": 123})
            assert status == 400
        finally:
            server.shutdown()

    def test_lint_bad_params(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_lp_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, body = _post(port, "/api/lint",
                                 {"code": "x = 1", "max_lines": "abc", "max_params": "xyz"})
            assert status == 200
            assert json.loads(body)["ok"] is True
        finally:
            server.shutdown()

    def test_lint_ok(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_lok_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, body = _post(port, "/api/lint", {"code": "def f():\n    pass"})
            assert status == 200
            assert json.loads(body)["ok"] is True
        finally:
            server.shutdown()


class TestStaticAndSettings:
    def test_favicon_routes(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_fav_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            for p in ("/favicon.ico", "/favicon-32.png", "/favicon-16.png",
                      "/apple-touch-icon.png", "/logo.png", "/vendor/chart.umd.min.js"):
                status, _, _ = _get(port, p)
                assert status in (200, 404)
        finally:
            server.shutdown()

    def test_settings_defaults_bad_section(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_sd_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _, _ = _get(port, "/api/settings/defaults?section=nope")
            assert status == 400
        finally:
            server.shutdown()

    def test_settings_defaults_error(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_sde_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            bad = types.SimpleNamespace(
                defaults=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
            monkeypatch.setattr(srv, "_settings_instance", lambda: bad)
            status, body, _ = _get(port, "/api/settings/defaults?section=budget")
            assert status == 400
            assert "boom" in body
        finally:
            server.shutdown()

    def test_settings_reset_bad_section(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_rsb_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _ = _post(port, "/api/settings/reset", {"section": "nope"})
            assert status == 400
        finally:
            server.shutdown()

    def test_settings_reset_section(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_rs_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, body = _post(port, "/api/settings/reset", {"section": "telemetry"})
            assert status == 200
            assert json.loads(body)["ok"] is True
        finally:
            server.shutdown()

    def test_settings_reset_all(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_ra_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, body = _post(port, "/api/settings/reset", {})
            assert status == 200
            assert json.loads(body)["ok"] is True
        finally:
            server.shutdown()

    def test_settings_reset_error(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_rse_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            bad = types.SimpleNamespace(
                reset_section=lambda s: (_ for _ in ()).throw(ValueError("bad sec")),
                reset_all=lambda: {},
            )
            monkeypatch.setattr(srv, "_settings_instance", lambda: bad)
            status, body = _post(port, "/api/settings/reset", {"section": "telemetry"})
            assert status == 400
            assert "bad sec" in body
        finally:
            server.shutdown()

    def test_settings_mcp_status(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_mst_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, body, _ = _get(port, "/api/settings/mcp-status")
            assert status == 200
            assert "servers" in json.loads(body)
        finally:
            server.shutdown()

    def test_settings_restart(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_rst_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, body = _post(port, "/api/settings/restart", {})
            assert status == 200
            assert json.loads(body)["ok"] is True
        finally:
            server.shutdown()


class TestGraph:
    def _mk_graph(self, tmp: Path, content: str = '{"nodes":[],"links":[]}'):
        d = tmp / "graphify-out"
        d.mkdir(exist_ok=True)
        (d / "graph.json").write_text(content)

    def test_graph_missing(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_gm_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, body, _ = _get(port, "/api/graph")
            assert status == 200
            assert json.loads(body)["ok"] is False
        finally:
            server.shutdown()

    def test_graph_serve_cache_etag(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_g_"))
        self._mk_graph(tmp)
        server, port = _serve(tmp, monkeypatch)
        try:
            # First: full serve + populate cache
            status, body, hdrs = _get(port, "/api/graph")
            assert status == 200
            etag = hdrs.get("ETag")
            assert etag
            # Second: cache-hit branch
            status, body2, _ = _get(port, "/api/graph")
            assert status == 200
            assert body2 == body
            # Third: If-None-Match → 304
            req = Request(f"http://127.0.0.1:{port}/api/graph",
                          headers={"If-None-Match": etag})
            try:
                with urlopen(req) as resp:
                    assert resp.status == 304
            except urllib.error.HTTPError as e:
                assert e.code == 304
        finally:
            server.shutdown()
            srv.DashboardHandler._graph_cache.clear()

    def test_graph_too_large(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_gtl_"))
        self._mk_graph(tmp, " " * (2 * 1024 * 1024 + 10))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, body, _ = _get(port, "/api/graph")
            assert status == 200
            assert "too large" in json.loads(body)["error"]
        finally:
            server.shutdown()
            srv.DashboardHandler._graph_cache.clear()

    def test_graph_stat_oserror(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_gse_"))
        self._mk_graph(tmp)
        server, port = _serve(tmp, monkeypatch)
        try:
            orig_stat = Path.stat
            orig_exists = Path.exists
            def fake_stat(self, *a, **k):
                if self.name == "graph.json":
                    raise OSError("gone")
                return orig_stat(self, *a, **k)
            def fake_exists(self, *a, **k):
                if self.name == "graph.json":
                    return True  # exists() passes; explicit stat() then fails
                return orig_exists(self, *a, **k)
            monkeypatch.setattr(Path, "exists", fake_exists)
            monkeypatch.setattr(Path, "stat", fake_stat)
            status, body, _ = _get(port, "/api/graph")
            assert status == 200
            assert json.loads(body)["ok"] is False
        finally:
            server.shutdown()

    def test_graph_stats(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_gs_"))
        self._mk_graph(tmp, json.dumps({
            "nodes": [{"id": 1, "community": 2}, {"id": 2, "community": 2},
                      {"id": 3, "community": "x"}, "notdict"],
            "links": [{"a": 1}],
        }))
        server, port = _serve(tmp, monkeypatch)
        try:
            _status, body, _ = _get(port, "/api/graph/stats")
            data = json.loads(body)
            assert data["ok"] is True
            assert data["nodes"] == 4 and data["edges"] == 1
            assert data["communities"] == 1
        finally:
            server.shutdown()

    def test_graph_stats_missing(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_gsm_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            _status, body, _ = _get(port, "/api/graph/stats")
            assert json.loads(body)["ok"] is False
        finally:
            server.shutdown()

    def test_graph_stats_too_large(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_gstl_"))
        self._mk_graph(tmp, " " * (2 * 1024 * 1024 + 10))
        server, port = _serve(tmp, monkeypatch)
        try:
            _status, body, _ = _get(port, "/api/graph/stats")
            assert "too large" in json.loads(body)["error"]
        finally:
            server.shutdown()

    def test_graph_stats_corrupt(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_gsc_"))
        self._mk_graph(tmp, "{not json")
        server, port = _serve(tmp, monkeypatch)
        try:
            _status, body, _ = _get(port, "/api/graph/stats")
            assert json.loads(body)["ok"] is False
        finally:
            server.shutdown()


class TestSse:
    def test_max_clients(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_ssec_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            monkeypatch.setattr(DashboardHandler, "_sse_clients",
                                DashboardHandler._MAX_SSE_CLIENTS)
            status, _body, _ = _get(port, "/api/events")
            assert status == 503
        finally:
            monkeypatch.setattr(DashboardHandler, "_sse_clients", 0)
            server.shutdown()

    def test_stream_first_event(self, monkeypatch):
        tmp = Path(tempfile.mkdtemp(prefix="dash_sse_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=5)
            s.sendall(b"GET /api/events HTTP/1.1\r\nHost: x\r\n\r\n")
            s.settimeout(8)
            buf = b""
            while b"data:" not in buf:
                chunk = s.recv(8192)
                if not chunk:
                    break
                buf += chunk
            assert b"data:" in buf and b"version" in buf
            s.close()  # server hits BrokenPipeError on next write → covers except/finally
            time.sleep(0.2)
        finally:
            server.shutdown()


class TestLogMessage:
    def _handler_stub(self):
        return object.__new__(DashboardHandler)

    def test_error_logged(self, capsys):
        h = self._handler_stub()
        h.log_message('"%s" %s', "GET /x HTTP/1.1", "500 -")
        # status >= 400 → printed
        DashboardHandler.log_message(h, '"GET /x HTTP/1.1" 500 -')
        err = capsys.readouterr().err
        assert "500" in err

    def test_ok_silenced(self, capsys):
        h = self._handler_stub()
        DashboardHandler.log_message(h, '"GET /x HTTP/1.1" 200 -')
        err = capsys.readouterr().err
        assert "200" not in err

    def test_bad_format(self, capsys):
        h = self._handler_stub()
        DashboardHandler.log_message(h, "%d %d", "only-one")
        assert capsys.readouterr().err == ""
