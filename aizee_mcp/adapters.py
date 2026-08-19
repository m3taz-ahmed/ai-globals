#!/usr/bin/env python3
"""MCP execution adapter layer for aiZee.

Re-implements the orchestration-mcp adapter pattern: a stable MCP tool surface
with swappable execution backends (local, codex, claude_code, remote_a2a, etc.).
"""

from __future__ import annotations

import asyncio
import json
import shutil
import ssl
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Backend(str, Enum):
    """Supported execution backends."""

    LOCAL = "local"
    CODEX = "codex"
    CLAUDE_CODE = "claude_code"
    REMOTE_A2A = "remote_a2a"


class AdapterError(Exception):
    """Raised when an adapter fails to execute or is misconfigured."""


@dataclass
class Session:
    """Represents an external agent execution session."""

    session_id: str
    backend: Backend
    profile: str
    artifacts: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"


class AgentAdapter(ABC):
    """Abstract base for an agent execution backend adapter."""

    def __init__(self, backend: Backend, config: dict[str, Any] | None = None) -> None:
        self.backend = backend
        self.config = config or {}
        self._sessions: dict[str, Session] = {}

    @abstractmethod
    async def launch(self, task: str, profile: str | None = None) -> Session:
        """Launch a new execution session."""

    @abstractmethod
    async def poll(self, session: Session) -> Session:
        """Poll for session status and collect artifacts."""

    async def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def _store_artifact(self, session: Session, name: str, payload: Any) -> None:
        session.artifacts[name] = payload


class LocalAdapter(AgentAdapter):
    """Adapter for local execution within the aiZee kernel."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(Backend.LOCAL, config)

    async def launch(self, task: str, profile: str | None = None) -> Session:
        session = Session(
            session_id=f"local-{len(self._sessions) + 1}",
            backend=self.backend,
            profile=profile or "default",
        )
        session.status = "running"
        self._sessions[session.session_id] = session
        self._store_artifact(session, "task", task)
        return session

    async def poll(self, session: Session) -> Session:
        session.status = "completed"
        self._store_artifact(session, "result", {"local": True, "task": session.artifacts.get("task", "")})
        return session


class _CliAdapterBase(AgentAdapter):
    """Base for CLI-spawning adapters (codex, claude_code).

    Subclasses define ``_binary`` and ``_build_args``. Launch spawns the
    process via ``asyncio.create_subprocess_exec``; poll awaits completion
    with a configurable timeout and captures stdout/stderr.
    """

    _binary: str = ""
    _timeout: float = 300.0

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(self._backend(), config)

    @abstractmethod
    def _backend(self) -> Backend:
        """Return the Backend enum for this adapter."""

    @abstractmethod
    def _build_args(self, task: str, profile: str | None) -> list[str]:
        """Build CLI argument list for the task."""

    async def launch(self, task: str, profile: str | None = None) -> Session:
        if not shutil.which(self._binary):
            raise AdapterError(
                f"Binary {self._binary!r} not found on PATH for backend {self.backend.value!r}"
            )
        session = Session(
            session_id=f"{self.backend.value}-{len(self._sessions) + 1}",
            backend=self.backend,
            profile=profile or "default",
        )
        session.status = "running"
        self._sessions[session.session_id] = session
        self._store_artifact(session, "task", task)
        args = self._build_args(task, profile)
        self._store_artifact(session, "command", [self._binary, *args])
        try:
            proc = await asyncio.create_subprocess_exec(
                self._binary,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            session.status = "failed"
            self._store_artifact(session, "error", str(exc))
            raise AdapterError(f"Failed to spawn {self._binary}: {exc}") from exc
        self._store_artifact(session, "_pid", proc.pid)
        self._store_artifact(session, "_proc", proc)
        return session

    async def poll(self, session: Session) -> Session:
        proc: asyncio.subprocess.Process = session.artifacts.get("_proc")  # type: ignore[assignment]
        if proc is None:
            session.status = "failed"
            self._store_artifact(session, "error", "No process handle")
            return session
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout
            )
        except (TimeoutError, asyncio.TimeoutError):  # noqa: UP041
            proc.kill()
            session.status = "timeout"
            self._store_artifact(session, "error", f"Timed out after {self._timeout}s")
            return session
        stdout = stdout_b.decode("utf-8", errors="replace") if stdout_b else ""
        stderr = stderr_b.decode("utf-8", errors="replace") if stderr_b else ""
        self._store_artifact(session, "stdout", stdout)
        self._store_artifact(session, "stderr", stderr)
        self._store_artifact(session, "returncode", proc.returncode)
        session.status = "completed" if proc.returncode == 0 else "failed"
        self._store_artifact(
            session,
            "result",
            {
                "backend": self.backend.value,
                "task": session.artifacts.get("task", ""),
                "stdout": stdout,
                "returncode": proc.returncode,
            },
        )
        session.artifacts.pop("_proc", None)
        return session


class CodexAdapter(_CliAdapterBase):
    """Adapter for OpenAI Codex CLI.

    Spawns ``codex exec <task>`` and captures stdout/stderr. Requires the
    ``codex`` binary on PATH. Timeout configurable via ``config["timeout"]``.
    """

    _binary = "codex"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self._timeout = float(cfg.get("timeout", self._timeout))
        super().__init__(cfg)

    def _backend(self) -> Backend:
        return Backend.CODEX

    def _build_args(self, task: str, profile: str | None) -> list[str]:
        args = ["exec", task]
        if profile and profile != "default":
            args.extend(["--profile", profile])
        return args


class ClaudeCodeAdapter(_CliAdapterBase):
    """Adapter for Anthropic Claude Code CLI.

    Spawns ``claude --print <task>`` and captures stdout/stderr. Requires
    the ``claude`` binary on PATH. Timeout configurable via ``config["timeout"]``.
    """

    _binary = "claude"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self._timeout = float(cfg.get("timeout", self._timeout))
        super().__init__(cfg)

    def _backend(self) -> Backend:
        return Backend.CLAUDE_CODE

    def _build_args(self, task: str, profile: str | None) -> list[str]:
        args = ["--print", task]
        if profile and profile != "default":
            args.extend(["--profile", profile])
        return args


class RemoteA2AAdapter(AgentAdapter):
    """Adapter for remote A2A (Agent-to-Agent) servers.

    POSTs the task to the configured A2A endpoint (``config["endpoint"]``)
    and polls for completion. Uses stdlib ``urllib`` to avoid extra deps.
    Timeout configurable via ``config["timeout"]`` (default 300s).
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(Backend.REMOTE_A2A, config)
        self._endpoint = str(self.config.get("endpoint", "")).rstrip("/")
        self._poll_interval = float(self.config.get("poll_interval", 2.0))
        self._timeout = float(self.config.get("timeout", 300.0))
        self._verify_ssl = bool(self.config.get("verify_ssl", True))
        if not self._endpoint:
            raise AdapterError("RemoteA2AAdapter requires config['endpoint']")
        # Validate endpoint URL scheme
        if not self._endpoint.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise AdapterError(
                "RemoteA2AAdapter endpoint must use HTTPS (or localhost for dev). "
                f"Got: {self._endpoint}"
            )

    def _create_ssl_context(self) -> ssl.SSLContext | None:
        """Create SSL context for secure connections."""
        if not self._verify_ssl:
            return None
        ctx = ssl.create_default_context()
        return ctx

    async def launch(self, task: str, profile: str | None = None) -> Session:
        payload = json.dumps({"task": task, "profile": profile or "default"}).encode("utf-8")
        req = urllib.request.Request(
            f"{self._endpoint}/tasks",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        ssl_ctx = self._create_ssl_context()
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, context=ssl_ctx)  # nosec B310 - validated HTTPS endpoint
            )
            body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise AdapterError(f"A2A launch failed: {exc}") from exc
        session = Session(
            session_id=body.get("session_id", f"a2a-{len(self._sessions) + 1}"),
            backend=self.backend,
            profile=profile or "default",
        )
        session.status = "running"
        self._sessions[session.session_id] = session
        self._store_artifact(session, "task", task)
        self._store_artifact(session, "remote_session_id", body.get("session_id"))
        return session

    async def poll(self, session: Session) -> Session:
        remote_id = session.artifacts.get("remote_session_id", session.session_id)
        url = f"{self._endpoint}/tasks/{remote_id}"
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout
        while True:
            try:
                response = await loop.run_in_executor(
                    None, urllib.request.urlopen, urllib.request.Request(url)
                )
                body = json.loads(response.read().decode("utf-8"))
            except urllib.error.URLError as exc:
                session.status = "failed"
                self._store_artifact(session, "error", str(exc))
                return session
            status = body.get("status", "running")
            if status in ("completed", "failed", "timeout"):
                session.status = status
                self._store_artifact(session, "result", body.get("result", {}))
                return session
            if loop.time() > deadline:
                session.status = "timeout"
                self._store_artifact(session, "error", "Polling timed out")
                return session
            await asyncio.sleep(self._poll_interval)


class AdapterRegistry:
    """Registry and router for execution adapters."""

    def __init__(self) -> None:
        self._adapters: dict[Backend, AgentAdapter] = {}

    def register(self, backend: Backend, adapter: AgentAdapter) -> None:
        self._adapters[backend] = adapter

    def get(self, backend: Backend) -> AgentAdapter:
        if backend not in self._adapters:
            raise AdapterError(f"No adapter registered for backend {backend.value!r}")
        return self._adapters[backend]

    async def run(self, backend: Backend, task: str, profile: str | None = None) -> dict[str, Any]:
        adapter = self.get(backend)
        session = await adapter.launch(task, profile)
        session = await adapter.poll(session)
        return {
            "session_id": session.session_id,
            "backend": session.backend.value,
            "status": session.status,
            "profile": session.profile,
            "artifacts": session.artifacts,
        }


def default_registry() -> AdapterRegistry:
    """Return a registry with the built-in adapters."""
    registry = AdapterRegistry()
    registry.register(Backend.LOCAL, LocalAdapter())
    registry.register(Backend.CODEX, CodexAdapter())
    registry.register(Backend.CLAUDE_CODE, ClaudeCodeAdapter())
    # RemoteA2A requires endpoint config; register only if provided.
    return registry
