#!/usr/bin/env python3
"""AI Global OS dashboard server."""

from __future__ import annotations

import json
import mimetypes
import os
import signal
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

import config
from memory.store import MemoryStore
from runtime.kernel import Kernel
from runtime.metrics import format_metrics
from runtime.telemetry import system_metrics

# Shared instances so state (budget, audit, chat) is consistent across requests.
_kernel_cache: tuple[Path, Kernel] | None = None
_memory_cache: tuple[Path, MemoryStore] | None = None
_cache_lock = threading.Lock()

# Simple per-IP fixed-window rate limiter.
_rate_limit = int(os.environ.get("AGENT_OS_DASHBOARD_RATE_LIMIT", "120"))
_rate_window = float(os.environ.get("AGENT_OS_DASHBOARD_RATE_WINDOW", "60"))
_rate_state: dict[str, tuple[int, float]] = {}
_rate_lock = threading.Lock()


def _kernel_instance() -> Kernel:
    global _kernel_cache
    root = config.discover_root()
    project_root = config.discover_project_root()
    with _cache_lock:
        if _kernel_cache is None or _kernel_cache[0] != root:
            _kernel_cache = (root, Kernel(root, project_root))
        return _kernel_cache[1]


def _memory_instance() -> MemoryStore:
    global _memory_cache
    project_root = config.discover_project_root()
    with _cache_lock:
        if _memory_cache is None or _memory_cache[0] != project_root:
            _memory_cache = (project_root, MemoryStore(project_root))
        return _memory_cache[1]


def _check_rate_limit(client_ip: str) -> bool:
    if _rate_limit <= 0:
        return True
    with _rate_lock:
        now = time.time()
        count, window_start = _rate_state.get(client_ip, (0, now))
        if now - window_start > _rate_window:
            count, window_start = 0, now
        count += 1
        _rate_state[client_ip] = (count, window_start)
        return count <= _rate_limit


def _client_ip(handler: DashboardHandler) -> str:
    forwarded = handler.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    return forwarded or handler.client_address[0]


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler with shared kernel/memory and per-IP rate limiting."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.root = config.discover_root()
        self.project_root = config.discover_project_root()
        self.kernel = _kernel_instance()
        self.memory = _memory_instance()
        super().__init__(*args, **kwargs)

    def _origin(self) -> str:
        configured = os.environ.get("AGENT_OS_DASHBOARD_ORIGIN")
        if configured:
            return configured
        return self.headers.get("Origin", "")

    def _cors_headers(self) -> None:
        origin = self._origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
        else:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")

    def _send(
        self, code: int, body: bytes, content_type: str = "text/plain", cors: bool = True
    ) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        if cors:
            self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _auth(self) -> bool:
        token = os.environ.get("AGENT_OS_DASHBOARD_TOKEN")
        if not token:
            return True
        header = self.headers.get("Authorization", "")
        return header == f"Bearer {token}"

    def do_OPTIONS(self) -> None:
        self._send(204, b"", cors=True)

    def _handle(self) -> None:
        if not _check_rate_limit(_client_ip(self)):
            self._send(429, b"Rate limit exceeded", cors=True)
            return
        if not self._auth():
            self._send(401, b"Unauthorized", cors=True)
            return
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/status":
            self._send_status()
        elif parsed.path == "/api/health":
            self._send_health()
        elif parsed.path == "/api/check":
            self._send_check(parsed.query)
        elif parsed.path == "/api/metrics":
            self._send_metrics()
        elif parsed.path == "/api/telemetry":
            self._send_telemetry()
        elif parsed.path == "/api/system":
            self._send_system()
        elif parsed.path == "/api/audit":
            self._send_audit()
        elif parsed.path == "/api/memory/search":
            self._send_memory_search(parsed.query)
        elif parsed.path == "/api/policy/test":
            self._send_policy_test()
        elif parsed.path == "/api/workflows":
            self._send_workflows()
        elif parsed.path == "/api/workflow/run":
            self._send_workflow_run()
        elif parsed.path == "/api/saga/run":
            self._send_saga_run()
        elif parsed.path.startswith("/api/saga/"):
            self._send_saga_get(parsed.path[10:])
        elif parsed.path == "/api/chat":
            self._send_chat()
        elif parsed.path == "/" or parsed.path == "/index.html":
            self._serve_file(self.root / "dashboard" / "index.html")
        elif parsed.path == "/index.css":
            self._serve_file(self.root / "dashboard" / "index.css")
        else:
            self._send(404, b"Not found")

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def _read_json_body(self) -> dict[str, Any] | None:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            return {}
        try:
            data = self.rfile.read(content_length)
            return cast(dict[str, Any], json.loads(data.decode("utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send(400, b"Invalid JSON body")
            return None

    def _send_status(self) -> None:
        self._send(200, json.dumps(self.kernel.status(), default=str).encode("utf-8"), "application/json")

    def _send_health(self) -> None:
        health = {"ok": True, "root": str(self.root), "version": config.VERSION}
        self._send(200, json.dumps(health).encode("utf-8"), "application/json")

    def _send_check(self, query: str) -> None:
        qs = urllib.parse.parse_qs(query)
        action = qs.get("action", [""])[0]
        if not action or not action.isalnum():
            self._send(400, b"Invalid action format")
            return
        action_args = {"approved": True} if qs.get("approve", [""])[0] == "1" else {}
        result = self.kernel.act(action, **action_args)
        self._send(200, json.dumps(result, default=str).encode("utf-8"), "application/json")

    def _send_memory_search(self, query: str) -> None:
        qs = urllib.parse.parse_qs(query)
        q = qs.get("q", [""])[0]
        kind = qs.get("kind", [""])[0] or None
        results = self.memory.search(q, kind)
        items = [{"id": r.id, "kind": r.kind, "source": r.source, "content": r.content} for r in results]
        self._send(200, json.dumps(items).encode("utf-8"), "application/json")

    def _send_policy_test(self) -> None:
        body = self._read_json_body()
        if body is None:
            return
        action = body.get("action", "")
        if not action or not action.isalnum():
            self._send(400, b"Invalid action format")
            return
        args = body.get("args", {}) if isinstance(body.get("args"), dict) else {}
        result = self.kernel.act(action, dry_run=True, **args)
        self._send(200, json.dumps(result, default=str).encode("utf-8"), "application/json")

    def _send_workflows(self) -> None:
        workflows = self.kernel.list_workflows()
        self._send(200, json.dumps(workflows, default=str).encode("utf-8"), "application/json")

    def _send_workflow_run(self) -> None:
        body = self._read_json_body()
        if body is None:
            return
        workflow_id = body.get("workflow_id", "")
        if not workflow_id or not isinstance(workflow_id, str):
            self._send(400, b"Missing or invalid workflow_id")
            return
        context = body.get("context", {}) if isinstance(body.get("context"), dict) else {}
        result = self.kernel.run_workflow(workflow_id, context)
        self._send(200, json.dumps(result, default=str).encode("utf-8"), "application/json")

    def _send_saga_run(self) -> None:
        body = self._read_json_body()
        if body is None:
            return
        saga_id = body.get("saga_id", "")
        if not saga_id or not isinstance(saga_id, str):
            self._send(400, b"Missing or invalid saga_id")
            return
        steps = body.get("steps", [])
        if not isinstance(steps, list):
            self._send(400, b"steps must be a list")
            return
        context = body.get("context", {}) if isinstance(body.get("context"), dict) else {}
        result = self.kernel.run_saga(saga_id, steps, context)
        self._send(200, json.dumps(result, default=str).encode("utf-8"), "application/json")

    def _send_saga_get(self, saga_id: str) -> None:
        result = self.kernel.saga.get_saga(saga_id)
        if result is None:
            self._send(404, b"Saga not found")
            return
        self._send(200, json.dumps(result, default=str).encode("utf-8"), "application/json")

    def _send_chat(self) -> None:
        body = self._read_json_body()
        if body is None:
            return
        message = body.get("message", "")
        if not message or not isinstance(message, str):
            self._send(400, b"Missing or invalid message")
            return
        session_id = body.get("session_id")
        if session_id is not None and not isinstance(session_id, str):
            self._send(400, b"Invalid session_id")
            return
        result = self.kernel.chat_message(message, session_id=session_id)
        self._send(200, json.dumps(result, default=str).encode("utf-8"), "application/json")

    def _send_metrics(self) -> None:
        body = format_metrics(self.kernel).encode("utf-8")
        self._send(200, body, "text/plain; version=0.0.4; charset=utf-8", cors=False)

    def _send_telemetry(self) -> None:
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        limit = int(qs.get("limit", ["100"])[0])
        event_type = qs.get("type", [""])[0] or None
        events = self.kernel.telemetry.query(limit=limit, event_type=event_type)
        self._send(200, json.dumps(events, default=str).encode("utf-8"), "application/json")

    def _send_system(self) -> None:
        data = system_metrics()
        data["root"] = str(self.root)
        data["project_root"] = str(self.project_root)
        data["version"] = config.VERSION
        self._send(200, json.dumps(data, default=str).encode("utf-8"), "application/json")

    def _send_audit(self) -> None:
        audit_file = self.root / "state" / "audit.log"
        lines = []
        if audit_file.exists():
            with audit_file.open("r", encoding="utf-8") as f:
                lines = [json.loads(line) for line in f if line.strip()]
        self._send(200, json.dumps(lines[-100:], default=str).encode("utf-8"), "application/json")

    def _serve_file(self, path: Path) -> None:
        if not path.exists():
            self._send(404, b"Not found")
            return
        self._send(200, path.read_bytes(), mimetypes.guess_type(str(path))[0] or "text/plain", cors=False)

    def log_message(self, format: str, *args: object) -> None:
        return


def _shutdown(_signum: int, _frame: Any) -> None:  # pragma: no cover
    sys.exit(0)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    host = os.environ.get("AGENT_OS_HOST", "127.0.0.1")
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"AI Global OS dashboard: http://{host}:{port}")
    server.serve_forever()
