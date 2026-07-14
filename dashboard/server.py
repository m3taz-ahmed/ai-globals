#!/usr/bin/env python3
"""AI Global OS dashboard server."""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import config
from runtime.kernel import Kernel


class DashboardHandler(BaseHTTPRequestHandler):
    root: Path = config.discover_root()
    kernel = Kernel(root)

    def _auth(self) -> bool:
        token = os.environ.get("AGENT_OS_DASHBOARD_TOKEN")
        if not token:
            return True
        header = self.headers.get("Authorization", "")
        return header == f"Bearer {token}"

    def _send(self, code: int, body: bytes, content_type: str = "text/plain") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send(200, b"ok")

    def do_GET(self) -> None:
        if not self._auth():
            self._send(401, b"Unauthorized")
            return
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/status":
            self._send(200, json.dumps(self.kernel.status(), default=str).encode("utf-8"), "application/json")
        elif parsed.path == "/api/check":
            qs = urllib.parse.parse_qs(parsed.query)
            action = qs.get("action", [""])[0]
            if not action or not action.isalnum():
                self._send(400, b"Invalid action format")
                return
            self._send(200, json.dumps(self.kernel.act(action), default=str).encode("utf-8"), "application/json")
        elif parsed.path == "/api/audit":
            self._send_audit()
        elif parsed.path == "/" or parsed.path == "/index.html":
            self._serve_file(self.root / "dashboard" / "index.html")
        else:
            self._send(404, b"Not found")

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
        self._send(200, path.read_bytes(), mimetypes.guess_type(str(path))[0] or "text/plain")

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    host = os.environ.get("AGENT_OS_HOST", "127.0.0.1")
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"AI Global OS dashboard: http://{host}:{port}")
    server.serve_forever()
