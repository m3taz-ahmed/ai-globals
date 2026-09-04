#!/usr/bin/env python3
"""MCP execution adapter layer for aiZee.

Re-implements the orchestration-mcp adapter pattern: a stable MCP tool surface
with swappable execution backends (local, codex, claude_code, remote_a2a, etc.).
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import shutil
import ssl
import urllib.error
import urllib.parse
import urllib.request
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


def _is_loopback_ip(host: str) -> bool:
    """Return True if ``host`` is a loopback address (IPv4 127/8 or IPv6 ::1).

    Rejects look-alikes such as ``127.0.0.1.evil.com`` or ``127.0.0.256``
    which a naive ``startswith`` would accept (SSRF bypass).
    """
    if not host:
        return False
    clean = host.strip("[]")
    if clean == "::1":
        return True
    import ipaddress as _ipaddress

    try:
        ip = _ipaddress.ip_address(clean)
    except ValueError:
        return False
    return ip.is_loopback


def _is_private_or_reserved_ip(host: str) -> bool:
    """Return True if ``host`` is a private, loopback, link-local, or reserved IP.

    Blocks RFC 1918 (10/8, 172.16/12, 192.168/16), loopback (127/8, ::1),
    link-local (169.254/16, fe80::/10), CGNAT (100.64/10), IPv6 ULA (fc00::/7),
    and metadata endpoints. This prevents SSRF to internal services and cloud
    metadata (e.g. 169.254.169.254).
    """
    if not host:
        return False
    # Strip IPv6 brackets for parsing.
    clean = host.strip("[]")
    # Fast path: IPv6 loopback
    if clean == "::1":
        return True
    # Use ipaddress for robust IPv4 + IPv6 classification.
    import ipaddress as _ipaddress

    try:
        ip = _ipaddress.ip_address(clean)
    except ValueError:
        return False
    # is_private covers RFC 1918, loopback, link-local, ULA, reserved.
    # is_loopback covers 127/8 and ::1.
    # is_link_local covers 169.254/16 and fe80::/10.
    # is_reserved covers 0.0.0.0/8, 240.0.0.0/4, etc.
    # is_multicast covers 224.0.0.0/4, ff00::/8.
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )


class Backend(str, Enum):
    """Supported execution backends."""

    LOCAL = "local"
    CODEX = "codex"
    CLAUDE_CODE = "claude_code"
    REMOTE_A2A = "remote_a2a"


class AdapterError(Exception):
    """Raised when an adapter fails to execute or is misconfigured."""


class _A2ARedirectBlocker(urllib.request.HTTPRedirectHandler):
    """Block cross-origin redirects on A2A polling (SSRF guard)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        target = urllib.parse.urljoin(req.full_url, newurl)
        base = urllib.parse.urlparse(req.full_url)
        dest = urllib.parse.urlparse(target)
        if dest.scheme not in ("http", "https") or dest.netloc.lower() != base.netloc.lower():
            raise urllib.error.HTTPError(
                req.full_url, code, f"A2A redirect to {target!r} blocked", headers, fp,
            )
        # SSRF re-validation: redirect target must not resolve to private IP.
        dest_host = (dest.hostname or "").lower()
        if _is_private_or_reserved_ip(dest_host):
            raise urllib.error.HTTPError(
                req.full_url, code,
                f"A2A redirect to private/reserved IP {dest_host!r} blocked (SSRF)",
                headers, fp,
            )
        return super().redirect_request(req, fp, code, msg, headers, target)


def _a2a_open(url: str | urllib.request.Request, context: ssl.SSLContext, timeout: float):  # type: ignore[no-untyped-def]
    """Open an A2A URL/Request with redirect confinement (same-origin only)."""
    opener = urllib.request.build_opener(
        _A2ARedirectBlocker(), urllib.request.HTTPSHandler(context=context),
    )
    if isinstance(url, urllib.request.Request):
        return opener.open(url, timeout=timeout)
    return opener.open(urllib.request.Request(url), timeout=timeout)


def _positive_float(value: Any, default: float, maximum: float = 3600.0) -> float:
    """Coerce a timeout config to a positive finite float (fallback: default)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    import math
    if not math.isfinite(number) or number <= 0:
        return default
    return min(number, maximum)


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
            session_id=f"local-{uuid.uuid4().hex[:12]}",
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

    def public_session(self, session: Session) -> Session:
        """Return a copy without internal handles (never leaks _proc/_pid)."""
        public = copy.copy(session)
        public.artifacts = {k: v for k, v in session.artifacts.items() if not k.startswith("_")}
        return public


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
            session_id=f"{self.backend.value}-{uuid.uuid4().hex[:12]}",
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
        proc = session.artifacts.get("_proc")
        if proc is None or not hasattr(proc, "communicate"):
            session.status = "failed"
            self._store_artifact(session, "error", "No process handle")
            return session
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout
            )
        except (TimeoutError, asyncio.TimeoutError):
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
        self._timeout = _positive_float(cfg.get("timeout", self._timeout), self._timeout)
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
        self._timeout = _positive_float(cfg.get("timeout", self._timeout), self._timeout)
        super().__init__(cfg)

    def _backend(self) -> Backend:
        return Backend.CLAUDE_CODE

    def _build_args(self, task: str, profile: str | None) -> list[str]:
        args = ["--print", task]
        if profile and profile != "default":
            args.extend(["--profile", profile])
        return args


def _validate_endpoint(endpoint: str) -> None:
    """Validate an A2A endpoint URL for scheme, host, and SSRF safety.

    Checks:
    1. Scheme must be http or https.
    2. HTTP is only allowed for exact localhost / loopback.
    3. Private/reserved IPs are blocked (SSRF guard).
    4. DNS resolution re-check: hostnames resolving to private IPs are blocked.
    """
    parsed = urllib.parse.urlparse(endpoint)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    if scheme not in ("https", "http"):
        raise AdapterError(
            f"RemoteA2AAdapter endpoint must use http(s) scheme. Got: {endpoint}"
        )
    if scheme == "http" and (not host or not (host == "localhost" or _is_loopback_ip(host))):
        raise AdapterError(
            "RemoteA2AAdapter HTTP endpoint is only allowed for "
            f"localhost/loopback. Got host: {host!r}"
        )
    # SSRF guard: block private/reserved IPs for BOTH http and https.
    if _is_private_or_reserved_ip(host):
        raise AdapterError(
            "RemoteA2AAdapter endpoint resolves to a private/reserved IP "
            f"(SSRF blocked). Got host: {host!r}"
        )
    # DNS-based SSRF: hostnames that resolve to private IPs bypass the
    # literal-IP check above. Resolve and re-check.
    if host and host != "localhost" and not _is_loopback_ip(host) and not _is_private_or_reserved_ip(host):
        import socket as _socket

        try:
            resolved = _socket.getaddrinfo(host, None)
            for _family, _, _, _, sockaddr in resolved:
                ip = str(sockaddr[0])
                ip_clean = ip.strip("[]")
                if _is_private_or_reserved_ip(ip_clean) or _is_loopback_ip(ip_clean):
                    raise AdapterError(
                        f"RemoteA2AAdapter endpoint {host!r} resolves to "
                        f"private/reserved IP {ip!r} (DNS SSRF blocked)."
                    )
        except _socket.gaierror:
            pass


class RemoteA2AAdapter(AgentAdapter):
    """Adapter for remote A2A (Agent-to-Agent) servers.

    POSTs the task to the configured A2A endpoint (``config["endpoint"]``)
    and polls for completion. Uses stdlib ``urllib`` to avoid extra deps.
    Timeout configurable via ``config["timeout"]`` (default 300s).
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(Backend.REMOTE_A2A, config)
        self._endpoint = str(self.config.get("endpoint", "")).rstrip("/")
        self._poll_interval = _positive_float(self.config.get("poll_interval", 2.0), 2.0, maximum=300.0)
        self._timeout = _positive_float(self.config.get("timeout", 300.0), 300.0)
        self._request_timeout = _positive_float(self.config.get("request_timeout", 30.0), 30.0, maximum=300.0)
        self._verify_ssl = bool(self.config.get("verify_ssl", True))
        self._ssl_context: ssl.SSLContext | None = None
        if not self._verify_ssl:
            logger.warning(
                "RemoteA2AAdapter SSL verification is DISABLED for %s — "
                "use only in trusted dev environments",
                self._endpoint,
            )
        if not self._endpoint:
            raise AdapterError("RemoteA2AAdapter requires config['endpoint']")
        _validate_endpoint(self._endpoint)

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create (once) the SSL context for secure connections.

        When ``verify_ssl=False`` an explicitly unverified context is
        returned; passing ``context=None`` to ``urlopen`` would instead use
        the default *verified* context, silently ignoring the flag. The
        context is memoized — ``ssl.create_default_context()`` loads the
        system CA store, which is too expensive to repeat per poll tick.
        """
        if self._ssl_context is None:
            ctx = ssl.create_default_context()
            if not self._verify_ssl:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            self._ssl_context = ctx
        return self._ssl_context

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
                None,
                lambda: _a2a_open(  # nosec B310 - validated + redirect-blocked endpoint
                    req, ssl_ctx, self._request_timeout
                ),
            )
            raw = response.read(1_000_000)
            try:
                body = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as exc:
                raise AdapterError(f"A2A launch returned malformed JSON: {exc}") from exc
            if not isinstance(body, dict):
                raise AdapterError("A2A launch returned a non-object response")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise AdapterError(f"A2A launch failed: {exc}") from exc
        remote_id = body.get("session_id")
        if not isinstance(remote_id, str) or not remote_id or len(remote_id) > 256:
            remote_id = f"a2a-{uuid.uuid4().hex[:12]}"
        # Collision-safe local key: a hostile server must not overwrite an
        # existing session by returning a duplicate session_id.
        local_id = f"a2a-{uuid.uuid4().hex[:12]}"
        session = Session(
            session_id=local_id,
            backend=self.backend,
            profile=profile or "default",
        )
        session.status = "running"
        self._sessions[session.session_id] = session
        self._store_artifact(session, "task", task)
        self._store_artifact(session, "remote_session_id", remote_id)
        return session

    async def poll(self, session: Session) -> Session:
        remote_id = session.artifacts.get("remote_session_id", session.session_id)
        if not isinstance(remote_id, str) or not remote_id:
            session.status = "failed"
            self._store_artifact(session, "error", "Missing remote session id")
            return session
        quoted = urllib.parse.quote(remote_id, safe="")
        url = f"{self._endpoint}/tasks/{quoted}"
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout
        while True:
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: _a2a_open(url, self._create_ssl_context(), self._request_timeout),
                )
                raw = response.read(1_000_000)
                try:
                    body = json.loads(raw.decode("utf-8"))
                except (ValueError, UnicodeDecodeError) as exc:
                    session.status = "failed"
                    self._store_artifact(session, "error", f"A2A poll returned malformed JSON: {exc}")
                    return session
                if not isinstance(body, dict):
                    session.status = "failed"
                    self._store_artifact(session, "error", "A2A poll returned a non-object response")
                    return session
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                session.status = "failed"
                self._store_artifact(session, "error", str(exc))
                return session
            status = body.get("status", "running")
            if status in ("completed", "failed", "timeout"):
                session.status = status
                result = body.get("result", {})
                self._store_artifact(session, "result", result if isinstance(result, dict) else {"value": result})
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
        # Strip internal handles (_proc/_pid) — never leak process objects.
        artifacts = {k: v for k, v in session.artifacts.items() if not k.startswith("_")}
        if "_pid" in session.artifacts:
            artifacts["pid"] = session.artifacts["_pid"]
        return {
            "session_id": session.session_id,
            "backend": session.backend.value,
            "status": session.status,
            "profile": session.profile,
            "artifacts": artifacts,
        }


def default_registry() -> AdapterRegistry:
    """Return a registry with the built-in adapters."""
    registry = AdapterRegistry()
    registry.register(Backend.LOCAL, LocalAdapter())
    registry.register(Backend.CODEX, CodexAdapter())
    registry.register(Backend.CLAUDE_CODE, ClaudeCodeAdapter())
    # RemoteA2A requires endpoint config; register only if provided.
    return registry
