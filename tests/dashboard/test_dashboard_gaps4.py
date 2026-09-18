"""Gap-coverage tests round 4 for dashboard/server.py — remaining branches."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import dashboard.server as srv
from dashboard.server import (
    DashboardHandler,
    ThreadingHTTPServer,
    _client_ip,
    _evict_stale_entries,
    _sync_claude_mcp_settings,
    _sync_devin_mcp_local,
    _write_dashboard_token_file,
)

pytestmark = pytest.mark.slow


def _serve(tmp_root: Path, monkeypatch: pytest.MonkeyPatch):
    import threading
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


def _get(port: int, path: str):
    import urllib.error
    from urllib.request import Request, urlopen
    req = Request(f"http://127.0.0.1:{port}{path}")
    try:
        with urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def _post(port: int, path: str, raw_body: bytes | None = None,
          extra_headers: dict | None = None):
    import urllib.error
    from urllib.request import Request, urlopen
    headers = {"Content-Type": "application/json", "X-Requested-With": "AIOS-Dashboard"}
    headers.update(extra_headers or {})
    req = Request(f"http://127.0.0.1:{port}{path}", data=raw_body or b"{}",
                  headers=headers, method="POST")
    try:
        with urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


class TestDevinSync:
    def test_reenabled_server_popped_when_empty(self, tmp_path):
        (tmp_path / ".devin").mkdir()
        (tmp_path / ".devin" / "mcp_config.local.json").write_text(
            json.dumps({"mcpServers": {"s1": {"disabled": True}}}))
        _sync_devin_mcp_local(tmp_path, {"s1": {"enabled": True}})
        data = json.loads(
            (tmp_path / ".devin" / "mcp_config.local.json").read_text())
        assert "s1" not in data["mcpServers"]


class TestClaudeSync:
    def test_canonical_dedup_across_config_files(self, tmp_path):
        (tmp_path / "aizee_mcp").mkdir()
        (tmp_path / ".devin").mkdir()
        (tmp_path / "aizee_mcp" / "config.json").write_text(
            json.dumps({"mcpServers": {"s1": {"command": "a"}}}))
        (tmp_path / ".devin" / "mcp_config.json").write_text(
            json.dumps({"mcpServers": {"s1": {"command": "dup"}}}))
        claude = tmp_path / ".claude"
        claude.mkdir()
        (claude / "settings.json").write_text(json.dumps({"mcpServers": {}}))
        _sync_claude_mcp_settings(tmp_path, {"s1": {"enabled": True}})
        out = json.loads((claude / "settings.json").read_text())
        assert out["mcpServers"]["s1"] == {"command": "a"}

    def test_disabled_server_absent_from_claude(self, tmp_path):
        claude = tmp_path / ".claude"
        claude.mkdir()
        (claude / "settings.json").write_text(
            json.dumps({"mcpServers": {"other": {"c": 1}}}))
        _sync_claude_mcp_settings(tmp_path, {"ghost": {"enabled": False}})
        out = json.loads((claude / "settings.json").read_text())
        assert "ghost" not in out["mcpServers"]


class TestRateLimitEviction:
    def test_evict_early_return_below_threshold(self):
        srv._rate_state.clear()
        srv._rate_state["1.1.1.1"] = (1, time.time())
        with patch.object(srv, "_rate_max_entries", 10_000):
            _evict_stale_entries(time.time())
        assert "1.1.1.1" in srv._rate_state

    def test_evict_stale_then_below_threshold(self):
        srv._rate_state.clear()
        old = time.time() - 10_000
        n = int(srv._rate_max_entries * 0.95)
        for i in range(n):
            srv._rate_state[f"10.0.{i // 256}.{i % 256}"] = (1, old)
        _evict_stale_entries(time.time())
        assert len(srv._rate_state) == 0


class TestClientIp:
    def test_trusted_proxy_empty_xff_returns_direct(self):
        handler = MagicMock()
        handler.client_address = ("1.2.3.4", 0)
        handler.headers.get.return_value = ""
        with patch.object(srv, "_TRUSTED_PROXIES", {"1.2.3.4"}):
            assert _client_ip(handler) == "1.2.3.4"


class TestTokenFile:
    def test_platform_error_falls_back_to_chmod(self, tmp_path):
        target = tmp_path / "tok" / "token.txt"
        with patch("platform.system", side_effect=RuntimeError("no platform")):
            out = _write_dashboard_token_file(target, "abc")
        assert out.read_text() == "abc"


class TestEndpoints:
    def test_tracing_skips_blank_lines(self, tmp_path, monkeypatch):
        server, port = _serve(tmp_path, monkeypatch)
        try:
            spans = tmp_path / "state" / "spans.jsonl"
            spans.write_text('\n{"a": 1}\n\n{"b": 2}\n', encoding="utf-8")
            status, body = _get(port, "/api/tracing")
            data = json.loads(body)
            assert status == 200
            assert data == [{"a": 1}, {"b": 2}]
        finally:
            server.shutdown()

    def test_settings_reset_bad_body(self, tmp_path, monkeypatch):
        server, port = _serve(tmp_path, monkeypatch)
        try:
            status, _ = _post(port, "/api/settings/reset", raw_body=b"{{{")
            assert status == 400
        finally:
            server.shutdown()

    def test_restart_suppresses_cache_errors(self, tmp_path, monkeypatch):
        server, port = _serve(tmp_path, monkeypatch)
        kcache = MagicMock()
        kcache.save.side_effect = RuntimeError("save fail")
        mcache = MagicMock()
        mcache.close.side_effect = RuntimeError("close fail")
        srv._kernel_cache = (None, kcache)
        srv._memory_cache = (None, mcache)
        try:
            status, _ = _post(port, "/api/settings/restart")
            assert status == 200
        finally:
            srv._kernel_cache = None
            srv._memory_cache = None
            server.shutdown()

    def test_sse_client_disconnect(self, tmp_path, monkeypatch):
        import http.client
        server, port = _serve(tmp_path, monkeypatch)
        try:
            with patch("time.sleep", lambda _s: None):
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                conn.request("GET", "/api/events")
                resp = conn.getresponse()
                resp.read(200)  # read headers + first event chunk
                conn.close()
                time.sleep(0.3)  # let server hit the broken pipe
        except (OSError, http.client.HTTPException):
            pass  # client-side close may raise locally - fine
        finally:
            server.shutdown()
