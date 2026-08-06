#!/usr/bin/env python3
"""MCP execution adapter layer for AI Global OS.

Re-implements the orchestration-mcp adapter pattern: a stable MCP tool surface
with swappable execution backends (local, codex, claude_code, remote_a2a, etc.).
"""

from __future__ import annotations

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
    """Adapter for local execution within the AI Global OS kernel."""

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


class CodexAdapter(AgentAdapter):
    """Adapter for OpenAI Codex CLI."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(Backend.CODEX, config)

    async def launch(self, task: str, profile: str | None = None) -> Session:
        session = Session(
            session_id=f"codex-{len(self._sessions) + 1}",
            backend=self.backend,
            profile=profile or "default",
        )
        self._sessions[session.session_id] = session
        self._store_artifact(session, "task", task)
        return session

    async def poll(self, session: Session) -> Session:
        # Placeholder: real implementation would invoke `codex` CLI and parse output.
        session.status = "completed"
        self._store_artifact(session, "result", {"backend": "codex", "task": session.artifacts.get("task", "")})
        return session


class ClaudeCodeAdapter(AgentAdapter):
    """Adapter for Anthropic Claude Code."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(Backend.CLAUDE_CODE, config)

    async def launch(self, task: str, profile: str | None = None) -> Session:
        session = Session(
            session_id=f"claude-{len(self._sessions) + 1}",
            backend=self.backend,
            profile=profile or "default",
        )
        self._sessions[session.session_id] = session
        self._store_artifact(session, "task", task)
        return session

    async def poll(self, session: Session) -> Session:
        session.status = "completed"
        self._store_artifact(session, "result", {"backend": "claude_code", "task": session.artifacts.get("task", "")})
        return session


class RemoteA2AAdapter(AgentAdapter):
    """Adapter for remote A2A agent servers."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(Backend.REMOTE_A2A, config)

    async def launch(self, task: str, profile: str | None = None) -> Session:
        session = Session(
            session_id=f"a2a-{len(self._sessions) + 1}",
            backend=self.backend,
            profile=profile or "default",
        )
        self._sessions[session.session_id] = session
        self._store_artifact(session, "task", task)
        return session

    async def poll(self, session: Session) -> Session:
        session.status = "completed"
        self._store_artifact(session, "result", {"backend": "remote_a2a", "task": session.artifacts.get("task", "")})
        return session


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
    registry.register(Backend.REMOTE_A2A, RemoteA2AAdapter())
    return registry
