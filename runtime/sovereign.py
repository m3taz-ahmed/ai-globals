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
    """Capability set attached to an agent or session.

    By default, a standard set of capabilities is granted (read, write, exec,
    deploy, destructive) so that ``kernel.status()`` reports meaningful
    capabilities and agents can be constrained by revoking specific ones.
    """

    # Standard capability set granted on initialization.
    _DEFAULT_CAPABILITIES: tuple[Capability, ...] = (
        Capability("read", "*"),
        Capability("write", "*"),
        Capability("exec", "*"),
        Capability("deploy", "*"),
        Capability("destructive", "*"),
    )

    def __init__(self, store: CapabilityStore | None = None, defaults: bool = True) -> None:
        self.store = store or CapabilityStore()
        if defaults:
            for cap in self._DEFAULT_CAPABILITIES:
                self.store.grant(cap)

    def require(self, capability: Capability) -> None:
        if not self.store.has(capability):
            raise PermissionError(f"Missing capability: {capability!s}")

    def grant(self, capability: Capability) -> None:
        self.store.grant(capability)

    def revoke(self, capability: Capability) -> None:
        self.store.revoke(capability)

    def list(self) -> list[str]:
        return self.store.list()
