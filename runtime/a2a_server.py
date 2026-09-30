#!/usr/bin/env python3
"""A2A (agent-to-agent) server-side exposure for aiZee.

Exposes the local aiZee agent as an A2A peer:

- ``GET /.well-known/agent-card.json`` — agent card metadata (name,
  version, skills, capabilities, auth scheme).
- ``POST /`` — JSON-RPC 2.0 task lifecycle: ``tasks/send``,
  ``tasks/get``, ``tasks/cancel``.

Security (SEC-14): binds loopback only by default and requires
``Authorization: Bearer <token>`` when a token is configured. Task
execution is delegated to a ``task_handler`` callback — the default
handler routes the message through ``Kernel.chat_message`` so every task
passes the full governance pipeline (gateway, policy, budget, audit).
"""

from __future__ import annotations

import json
import secrets
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


TERMINAL_STATES = {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED}


@dataclass
class A2ATask:
    id: str
    state: TaskState
    message: str
    result: str = ""
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "state": self.state.value,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AgentCard:
    """A2A agent card served at ``/.well-known/agent-card.json``."""

    name: str
    description: str
    url: str
    version: str
    skills: list[dict[str, str]] = field(default_factory=list)
    capabilities: dict[str, bool] = field(
        default_factory=lambda: {"streaming": False, "pushNotifications": False}
    )
    authentication: dict[str, Any] = field(
        default_factory=lambda: {"schemes": ["bearer"]}
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "skills": self.skills,
            "capabilities": self.capabilities,
            "authentication": self.authentication,
        }


class A2ATaskStore:
    """In-memory task store with JSONL persistence in ``state/a2a_tasks.jsonl``."""

    def __init__(self, project_root: Path) -> None:
        self._tasks: dict[str, A2ATask] = {}
        self._lock = threading.RLock()
        self._log = project_root / "state" / "a2a_tasks.jsonl"

    def create(self, message: str) -> A2ATask:
        with self._lock:
            task = A2ATask(id=f"task_{uuid.uuid4().hex[:12]}", state=TaskState.SUBMITTED, message=message)
            self._tasks[task.id] = task
            self._persist(task)
            return task

    def get(self, task_id: str) -> A2ATask | None:
        with self._lock:
            return self._tasks.get(task_id)

    def update(
        self,
        task_id: str,
        state: TaskState,
        result: str = "",
        error: str = "",
    ) -> A2ATask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.state in TERMINAL_STATES:
                return task
            task.state = state
            task.result = result or task.result
            task.error = error or task.error
            task.updated_at = datetime.now(timezone.utc).isoformat()
            self._persist(task)
            return task

    def _persist(self, task: A2ATask) -> None:
        try:
            self._log.parent.mkdir(parents=True, exist_ok=True)
            with self._log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(task.to_dict()) + "\n")
        except OSError:
            pass


TaskHandler = Callable[[str], str]


class A2AServer:
    """Loopback A2A HTTP server. Stdlib-only."""

    def __init__(
        self,
        project_root: Path,
        task_handler: TaskHandler,
        host: str = "127.0.0.1",
        port: int = 0,
        token: str | None = None,
        card: AgentCard | None = None,
    ) -> None:
        self.project_root = project_root
        self.task_handler = task_handler
        self.host = host
        self.token = token if token is not None else secrets.token_hex(16)
        self.store = A2ATaskStore(project_root)
        self._httpd = ThreadingHTTPServer((host, port), self._make_handler())
        self.port = self._httpd.server_address[1]
        self.card = card or self._default_card()
        self._thread: threading.Thread | None = None

    def _default_card(self) -> AgentCard:
        import config

        return AgentCard(
            name="aiZee",
            description="Sovereign AI engineering control plane — governed agent peer",
            url=f"http://{self.host}:{self.port}",
            version=config.VERSION,
            skills=[
                {"id": "governed-task", "name": "Governed task execution"},
                {"id": "memory-query", "name": "Persistent memory query"},
            ],
            authentication={"schemes": ["bearer"] if self.token else ["none"]},
        )

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        server = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args: Any) -> None:  # silence
                return

            def _authed(self) -> bool:
                if not server.token:
                    return True
                return self.headers.get("Authorization") == f"Bearer {server.token}"

            def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                if not self._authed():
                    self._send_json({"error": "unauthorized"}, 401)
                    return
                if self.path == "/.well-known/agent-card.json":
                    self._send_json(server.card.to_dict())
                    return
                self._send_json({"error": "not found"}, 404)

            def do_POST(self) -> None:
                if not self._authed():
                    self._send_json({"error": "unauthorized"}, 401)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    req = json.loads(self.rfile.read(length) or b"{}")
                except (ValueError, json.JSONDecodeError):
                    self._send_json({"error": "bad request"}, 400)
                    return
                self._send_json(server._dispatch(req))

        return _Handler

    def _dispatch(self, req: dict[str, Any]) -> dict[str, Any]:
        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params") or {}

        def err(code: int, msg: str) -> dict[str, Any]:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": msg}}

        if method == "tasks/send":
            message = str(params.get("message") or params.get("text") or "")
            if not message:
                return err(-32602, "tasks/send requires 'message'")
            task = self.store.create(message)
            self._run_task(task)
            return {"jsonrpc": "2.0", "id": req_id, "result": task.to_dict()}

        if method == "tasks/get":
            found = self.store.get(str(params.get("id", "")))
            if found is None:
                return err(-32602, "unknown task id")
            return {"jsonrpc": "2.0", "id": req_id, "result": found.to_dict()}

        if method == "tasks/cancel":
            canceled = self.store.update(str(params.get("id", "")), TaskState.CANCELED)
            if canceled is None:
                return err(-32602, "unknown task id")
            return {"jsonrpc": "2.0", "id": req_id, "result": canceled.to_dict()}

        return err(-32601, f"unknown method {method!r}")

    def _run_task(self, task: A2ATask) -> None:
        def work() -> None:
            self.store.update(task.id, TaskState.WORKING)
            try:
                result = self.task_handler(task.message)
                self.store.update(task.id, TaskState.COMPLETED, result=str(result))
            except Exception as exc:
                self.store.update(task.id, TaskState.FAILED, error=str(exc))

        threading.Thread(target=work, daemon=True).start()

    def serve_forever(self) -> None:
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def shutdown(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()


def default_task_handler(kernel: Any) -> TaskHandler:
    """Route A2A tasks through the governed kernel chat path."""

    def handle(message: str) -> str:
        result = kernel.chat_message(message)
        return json.dumps(result, default=str)

    return handle


__all__ = [
    "TERMINAL_STATES",
    "A2AServer",
    "A2ATask",
    "A2ATaskStore",
    "AgentCard",
    "TaskState",
    "default_task_handler",
]
