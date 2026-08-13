import json
import os
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from dashboard.server import DashboardHandler, ThreadingHTTPServer

pytestmark = pytest.mark.slow


def _serve(tmp_root: Path):
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_root / sub).mkdir(parents=True, exist_ok=True)
    (tmp_root / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    os.environ["AGENT_OS_ROOT"] = str(tmp_root)
    os.environ.setdefault("AGENT_OS_DASHBOARD_ALLOW_NO_TOKEN", "1")
    server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, port


def test_dashboard_status():
    tmp = Path(tempfile.mkdtemp(prefix="aios_dash_"))
    server, port = _serve(tmp)
    try:
        time.sleep(0.1)
        with urlopen(f"http://127.0.0.1:{port}/api/status") as resp:
            body = resp.read().decode()
            data = json.loads(body)
            assert data["version"] == "5.0.0"
    finally:
        server.shutdown()


def test_dashboard_health():
    tmp = Path(tempfile.mkdtemp(prefix="aios_dash_health_"))
    server, port = _serve(tmp)
    try:
        time.sleep(0.1)
        with urlopen(f"http://127.0.0.1:{port}/api/health") as resp:
            data = json.loads(resp.read().decode())
            assert data["ok"] is True
            assert data["version"] == "5.0.0"
    finally:
        server.shutdown()


def test_dashboard_cors_preflight():
    tmp = Path(tempfile.mkdtemp(prefix="aios_dash_cors_"))
    os.environ["AGENT_OS_DASHBOARD_ORIGIN"] = "http://example.com"
    server, port = _serve(tmp)
    try:
        time.sleep(0.1)
        req = Request(f"http://127.0.0.1:{port}/api/policy/test", method="OPTIONS")
        req.add_header("Origin", "http://example.com")
        req.add_header("Access-Control-Request-Method", "POST")
        with urlopen(req) as resp:
            assert resp.headers.get("Access-Control-Allow-Origin") == "http://example.com"
            assert "POST" in resp.headers.get("Access-Control-Allow-Methods", "")
    finally:
        server.shutdown()
        os.environ.pop("AGENT_OS_DASHBOARD_ORIGIN", None)


def test_dashboard_memory_search():
    tmp = Path(tempfile.mkdtemp(prefix="aios_dash_mem_"))
    server, port = _serve(tmp)
    try:
        time.sleep(0.1)
        with urlopen(f"http://127.0.0.1:{port}/api/memory/search?q=dashboard") as resp:
            data = json.loads(resp.read().decode())
            assert data == []
    finally:
        server.shutdown()


def test_dashboard_policy_test():
    tmp = Path(tempfile.mkdtemp(prefix="aios_dash_pol_"))
    server, port = _serve(tmp)
    try:
        time.sleep(0.1)
        req = Request(
            f"http://127.0.0.1:{port}/api/policy/test",
            data=json.dumps({"action": "Read", "args": {"path": "foo"}}).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Requested-With": "AIOS-Dashboard"},
            method="POST",
        )
        with urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            assert data["ok"] is True
            assert data["decision"]["decision"] == "allow"
    finally:
        server.shutdown()


def test_dashboard_post_requires_csrf_header():
    tmp = Path(tempfile.mkdtemp(prefix="aios_dash_csrf_"))
    server, port = _serve(tmp)
    try:
        time.sleep(0.1)
        req = Request(
            f"http://127.0.0.1:{port}/api/policy/test",
            data=json.dumps({"action": "Read"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urlopen(req)
        assert exc.value.code == 403
    finally:
        server.shutdown()


def test_dashboard_denies_untrusted_origin():
    tmp = Path(tempfile.mkdtemp(prefix="aios_dash_origin_"))
    server, port = _serve(tmp)
    try:
        time.sleep(0.1)
        req = Request(f"http://127.0.0.1:{port}/api/status", method="GET")
        req.add_header("Origin", "http://evil.com")
        with urlopen(req) as resp:
            assert "Access-Control-Allow-Origin" not in resp.headers
    finally:
        server.shutdown()


def test_dashboard_enforces_bearer_token():
    tmp = Path(tempfile.mkdtemp(prefix="aios_dash_auth_"))
    os.environ["AGENT_OS_DASHBOARD_TOKEN"] = "secret-token"
    server, port = _serve(tmp)
    try:
        time.sleep(0.1)
        req = Request(f"http://127.0.0.1:{port}/api/status", method="GET")
        with pytest.raises(urllib.error.HTTPError) as exc:
            urlopen(req)
        assert exc.value.code == 401

        req = Request(f"http://127.0.0.1:{port}/api/status", method="GET")
        req.add_header("Authorization", "Bearer secret-token")
        with urlopen(req) as resp:
            assert resp.status == 200
    finally:
        server.shutdown()
        os.environ.pop("AGENT_OS_DASHBOARD_TOKEN", None)


def test_dashboard_payload_size_limit():
    tmp = Path(tempfile.mkdtemp(prefix="aios_dash_size_"))
    import dashboard.server as dash_server
    original_max = dash_server._MAX_BODY_SIZE
    dash_server._MAX_BODY_SIZE = 64
    try:
        server, port = _serve(tmp)
        try:
            time.sleep(0.1)
            body = json.dumps({"action": "Read", "args": {"x": "y" * 100}}).encode("utf-8")
            req = Request(
                f"http://127.0.0.1:{port}/api/policy/test",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Requested-With": "AIOS-Dashboard",
                    "Content-Length": str(len(body)),
                },
                method="POST",
            )
            with pytest.raises(urllib.error.HTTPError) as exc:
                urlopen(req)
            assert exc.value.code == 413
        finally:
            server.shutdown()
    finally:
        dash_server._MAX_BODY_SIZE = original_max
