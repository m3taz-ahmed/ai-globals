"""Gap-coverage tests round 3 for dashboard/server.py — remaining branches."""
from __future__ import annotations

import json
import os
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
        with urlopen(req) as resp:
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
        with urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


class TestDevinSyncBranches:
    def test_enable_unknown_server_skipped(self, tmp_path):
        # enabled server not in local config -> existing {} -> elif False -> 173
        _sync_devin_mcp_local(tmp_path, {"ghost": {"enabled": True}})
        data = json.loads(
            (tmp_path / ".devin" / "mcp_config.local.json").read_text())
        assert data["mcpServers"] == {}


class TestClaudeSyncBranches:
    def _setup(self, root: Path):
        (root / ".claude").mkdir(parents=True)
        (root / ".claude" / "settings.json").write_text(
            json.dumps({"mcpServers": {"s1": {"cmd": "x"}}}))

    def test_duplicate_canonical_names(self, tmp_path):
        # same server in both canonical sources -> second file's defn skipped
        self._setup(tmp_path)
        (tmp_path / "aizee_mcp").mkdir()
        (tmp_path / ".devin").mkdir()
        (tmp_path / "aizee_mcp" / "config.json").write_text(
            json.dumps({"mcpServers": {"dup": {"v": 1}}}))
        (tmp_path / ".devin" / "mcp_config.json").write_text(
            json.dumps({"mcpServers": {"dup": {"v": 2}}}))
        _sync_claude_mcp_settings(tmp_path, {"dup": {"enabled": True}})
        cfg = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert cfg["mcpServers"]["dup"] == {"v": 1}

    def test_disable_absent_server(self, tmp_path):
        # disabling a server not in claude config -> 242 False -> 230
        self._setup(tmp_path)
        _sync_claude_mcp_settings(tmp_path, {"ghost": {"enabled": False}})
        cfg = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert "ghost" not in cfg["mcpServers"]


class TestRateEviction:
    @pytest.fixture(autouse=True)
    def _reset(self, monkeypatch):
        monkeypatch.setattr(srv, "_rate_max_entries", 10)
        srv._rate_state.clear()
        yield
        srv._rate_state.clear()

    def test_under_threshold_returns(self):
        srv._rate_state["ip"] = (1, time.time())
        _evict_stale_entries(time.time())  # 274 early return
        assert "ip" in srv._rate_state

    def test_no_stale_goes_to_lru(self):
        now = time.time()
        for i in range(10):  # > 9 (0.9*10)
            srv._rate_state[f"fresh{i}"] = (1, now)
        _evict_stale_entries(now)  # stale_ips empty -> 285 -> LRU evicts
        assert len(srv._rate_state) <= 10

    def test_shrinks_between_checks(self, monkeypatch):
        now = time.time()
        state = {f"s{i}": (1, now - 99999) for i in range(8)}
        state["fresh"] = (1, now)
        calls = {"n": 0}
        orig_len = dict.__len__

        class Shrink(dict):
            def __len__(self):
                calls["n"] += 1
                if calls["n"] >= 3:
                    return 0
                return orig_len(self)

        monkeypatch.setattr(srv, "_rate_state", Shrink(state))
        _evict_stale_entries(now)  # 283 False -> 286 True -> 287 return

    def test_stale_cleanup_sufficient(self):
        now = time.time()
        for i in range(10):
            srv._rate_state[f"old{i}"] = (1, now - 99999)
        _evict_stale_entries(now)  # all stale -> emptied -> 283 return
        assert not srv._rate_state


class TestClientIp:
    def test_xff_whitespace_only(self, monkeypatch):
        monkeypatch.setattr(srv, "_TRUSTED_PROXIES", {"10.0.0.1"})
        h = MagicMock()
        h.headers = {"X-Forwarded-For": "  ,  "}
        h.client_address = ("10.0.0.1", 1)
        assert _client_ip(h) == "10.0.0.1"

    def test_xff_all_trusted(self, monkeypatch):
        monkeypatch.setattr(srv, "_TRUSTED_PROXIES", {"10.0.0.1", "10.0.0.2"})
        h = MagicMock()
        h.headers = {"X-Forwarded-For": "10.0.0.2, 10.0.0.1"}
        h.client_address = ("10.0.0.1", 1)
        assert _client_ip(h) == "10.0.0.2"


class TestTokenFile:
    def test_posix_open_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(os, "name", "posix")
        p = _write_dashboard_token_file(tmp_path, "tok123")
        assert p.read_text() == "tok123"

    def test_posix_fdopen_failure(self, tmp_path, monkeypatch):
        monkeypatch.setattr(os, "name", "posix")
        with patch("os.fdopen", side_effect=OSError("disk")):
            with pytest.raises(OSError):
                _write_dashboard_token_file(tmp_path, "t")

    def test_chmod_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setattr(os, "name", "posix")
        import platform
        monkeypatch.setattr(platform, "system", MagicMock(side_effect=RuntimeError("x")))
        p = _write_dashboard_token_file(tmp_path, "tok")
        assert p.exists()


class TestSseAndHandlers:
    def test_sse_broken_pipe(self, monkeypatch):
        h = DashboardHandler.__new__(DashboardHandler)
        h.send_response = MagicMock()
        h.send_header = MagicMock()
        h.end_headers = MagicMock()
        h.wfile = MagicMock()
        h.wfile.write.side_effect = BrokenPipeError()
        h.headers = {}
        h.kernel = MagicMock()
        h.kernel.status.return_value = {}
        h._origin = MagicMock(return_value="")
        DashboardHandler._sse_clients = 0
        monkeypatch.setattr(time, "sleep", lambda s: None)
        h._send_sse_events()
        assert DashboardHandler._sse_clients == 0

    def test_sse_max_clients(self):
        h = DashboardHandler.__new__(DashboardHandler)
        sent = []
        h._send = lambda code, body, **k: sent.append(code)
        DashboardHandler._sse_clients = DashboardHandler._MAX_SSE_CLIENTS
        h._send_sse_events()
        assert sent == [503]
        DashboardHandler._sse_clients = 0


class TestHttpRemaining:
    def test_tracing_blank_lines(self, monkeypatch):
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="dash_trb_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            (tmp / "state" / "spans.jsonl").write_text(
                '{"s":1}\n\n   \n{"s":2}\n')
            status, body = _get(port, "/api/tracing")
            assert status == 200
            assert len(json.loads(body)) == 2
        finally:
            server.shutdown()

    def test_settings_reset_bad_body(self, monkeypatch):
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="dash_srb_"))
        server, port = _serve(tmp, monkeypatch)
        try:
            status, _ = _post(port, "/api/settings/reset",
                              raw_body=b"not json{")
            assert status == 400
        finally:
            server.shutdown()

    def test_settings_restart_with_caches(self, monkeypatch):
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="dash_rc_"))
        server, port = _serve(tmp, monkeypatch)
        kern = MagicMock()
        mem = MagicMock()
        monkeypatch.setattr(srv, "_kernel_cache", (tmp, kern))
        monkeypatch.setattr(srv, "_memory_cache", (tmp, mem))
        try:
            status, body = _post(port, "/api/settings/restart", b"{}")
            assert status == 200
            assert json.loads(body)["ok"] is True
            kern.save.assert_called_once()
            mem.close.assert_called_once()
        finally:
            server.shutdown()
