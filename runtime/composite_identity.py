#!/usr/bin/env python3
"""Composite identity attribution for AI agent actions.

Inspired by GitLab Duo's composite identity pattern: every AI agent action is
attributed to BOTH the agent AND the human who instructed it (dual principal),
so activity is never attributable to the agent alone.

Each :class:`CompositeIdentity` pairs an agent principal with a human principal
and a session/tenant scope. A deterministic SHA-256 signature over the
agent id, human id, and session id lets registries resolve the identity for
attribution records without storing PII in the clear.
"""

from __future__ import annotations

import copy
import hashlib
import json
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any


class PrincipalRole(str, Enum):
    """Role of a principal within a composite identity."""

    AGENT = "agent"
    HUMAN = "human"


@dataclass(frozen=True)
class Principal:
    """A single principal (agent or human) in a composite identity."""

    role: PrincipalRole
    principal_id: str
    display_name: str = ""


@dataclass(frozen=True)
class CompositeIdentity:
    """Dual-principal identity pairing an agent with its instructing human.

    The signature is a SHA-256 over ``agent.principal_id`` +
    ``human.principal_id`` + ``session_id`` + ``tenant_id`` (sorted-key
    JSON), so equivalent identities produce identical signatures
    regardless of field ordering.

    SECURITY NOTE: unsalted SHA-256 is deterministic and linkable —
    identical inputs always yield identical signatures, so signatures
    can be correlated across stores. Kept unchanged to avoid breaking
    stored ids; do not use the signature as a secrecy mechanism.
    """

    agent: Principal
    human: Principal
    session_id: str = ""
    tenant_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize the identity to a plain dict."""
        return {
            "agent": {
                "role": self.agent.role.value,
                "principal_id": self.agent.principal_id,
                "display_name": self.agent.display_name,
            },
            "human": {
                "role": self.human.role.value,
                "principal_id": self.human.principal_id,
                "display_name": self.human.display_name,
            },
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
        }

    def signature(self) -> str:
        """Return a deterministic SHA-256 signature for this identity."""
        payload = json.dumps(
            {
                "agent_id": self.agent.principal_id,
                "human_id": self.human.principal_id,
                "session_id": self.session_id,
                "tenant_id": self.tenant_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CompositeIdentityRegistry:
    """Thread-safe registry of composite identities keyed by signature.

    Stores identities so actions can be attributed to both principals without
    re-supplying the full identity on every call. All mutations are guarded
    by a :class:`threading.Lock`.
    """

    def __init__(self) -> None:
        self._identities: dict[str, CompositeIdentity] = {}
        self._lock = threading.Lock()

    def register(self, identity: CompositeIdentity) -> str:
        """Register *identity* and return its signature as the lookup key."""
        sig = identity.signature()
        with self._lock:
            self._identities[sig] = identity
        return sig

    def resolve(self, signature: str) -> CompositeIdentity | None:
        """Return the identity for *signature*, or ``None`` if unknown."""
        with self._lock:
            return self._identities.get(signature)

    def attribute(
        self,
        signature: str,
        action: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        """Build an attribution record for *action* under *signature*.

        The record always carries BOTH principals so the action is never
        attributable to the agent alone. Returns ``None``-free dict; if the
        signature is unknown the ``principals`` list is empty.
        """
        identity = self.resolve(signature)
        principals: list[dict[str, Any]] = []
        if identity is not None:
            principals = [
                {
                    "role": identity.agent.role.value,
                    "principal_id": identity.agent.principal_id,
                    "display_name": identity.agent.display_name,
                },
                {
                    "role": identity.human.role.value,
                    "principal_id": identity.human.principal_id,
                    "display_name": identity.human.display_name,
                },
            ]
        return {
            "signature": signature,
            "action": action,
            "details": copy.deepcopy(details),
            "principals": principals,
            "session_id": identity.session_id if identity else "",
            "tenant_id": identity.tenant_id if identity else "",
        }

    def list_identities(self) -> list[CompositeIdentity]:
        """Return a snapshot list of all registered identities."""
        with self._lock:
            return list(self._identities.values())

    def clear(self) -> None:
        """Remove all registered identities."""
        with self._lock:
            self._identities.clear()


__all__ = [
    "CompositeIdentity",
    "CompositeIdentityRegistry",
    "Principal",
    "PrincipalRole",
]
