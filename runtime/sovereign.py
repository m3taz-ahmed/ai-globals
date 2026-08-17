#!/usr/bin/env python3
"""Sovereign capability model for aiZee.

Re-implements the Sovereign-OS pattern: pluggable capabilities define what an
agent is allowed to do. Capabilities are granted, revoked, and checked at
runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Capability:
    """A single capability with an optional resource scope."""

    name: str
    resource: str = "*"
    params: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.name}:{self.resource}"


class CapabilityStore:
    """Store and query capabilities."""

    def __init__(self) -> None:
        self._capabilities: set[str] = set()

    def grant(self, capability: Capability) -> None:
        self._capabilities.add(str(capability))

    def revoke(self, capability: Capability) -> None:
        self._capabilities.discard(str(capability))

    def has(self, capability: Capability) -> bool:
        return str(Capability(capability.name, "*")) in self._capabilities or str(capability) in self._capabilities

    def list(self) -> list[str]:
        return sorted(self._capabilities)


class AgentCapabilities:
    """Capability set attached to an agent or session."""

    def __init__(self, store: CapabilityStore | None = None) -> None:
        self.store = store or CapabilityStore()

    def require(self, capability: Capability) -> None:
        if not self.store.has(capability):
            raise PermissionError(f"Missing capability: {capability!s}")

    def grant(self, capability: Capability) -> None:
        self.store.grant(capability)

    def list(self) -> list[str]:
        return self.store.list()
