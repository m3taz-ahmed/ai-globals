#!/usr/bin/env python3
"""MCP protocol version handling - dual-era support (2025-11-25 + 2026-07-28).

Implements the protocol floor from the mcp-architect doctrine:

- Era detection: ``protocolVersion`` decides the era. ``2026-07-28`` is the
  stateless era - no ``Mcp-Session-Id``, requests routed by
  ``Mcp-Method``/``Mcp-Name`` headers so proxies can rate-limit without
  parsing JSON bodies.
- Negotiation: the client advertises the newest version it supports and
  validates the server's negotiated version against the supported set
  (fail-closed on unknown versions).
- Header routing helpers for stateless-era HTTP transports.

The module is transport-agnostic: stdio callers only need version
negotiation; HTTP callers additionally use the header helpers.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity

# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

#: The stateless-era protocol version (spec 2026-07-28).
PROTOCOL_STATELESS = "2026-07-28"

#: The last session-oriented protocol version (still supported - dual era).
PROTOCOL_LEGACY = "2025-11-25"

#: Older versions tolerated on the client side for interop.
TOLERATED_LEGACY_VERSIONS: tuple[str, ...] = (
    "2024-11-05",
    "2025-03-26",
    "2025-06-18",
)

#: All protocol versions this build can negotiate.
SUPPORTED_PROTOCOL_VERSIONS: tuple[str, ...] = (
    PROTOCOL_STATELESS,
    PROTOCOL_LEGACY,
    *TOLERATED_LEGACY_VERSIONS,
)

#: Version the client advertises on initialize (newest first = spec default).
DEFAULT_CLIENT_VERSION: str = PROTOCOL_STATELESS


class McpEra(str, Enum):
    """Which protocol era a negotiated version belongs to."""

    STATELESS = "stateless"  # 2026-07-28+: no Mcp-Session-Id
    LEGACY = "legacy"  # <= 2025-11-25: session-oriented


class McpProtocolError(AizeeError):
    """Raised on protocol version negotiation/validation failures."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("MCP_PROTOCOL_ERROR", message, ErrorSeverity.HIGH, context)


# Header names (stateless era). ``Mcp-Session-Id`` is REMOVED in 2026-07-28.
HEADER_METHOD = "Mcp-Method"
HEADER_NAME = "Mcp-Name"
HEADER_SESSION_ID = "Mcp-Session-Id"  # legacy era only


def era_for_version(version: str) -> McpEra:
    """Map a protocol version string to its era.

    Versions newer than the stateless cutoff (by date ordering) are
    stateless; anything else is legacy.
    """
    return McpEra.STATELESS if version >= PROTOCOL_STATELESS else McpEra.LEGACY


def validate_protocol_version(
    version: str,
    *,
    allowed: tuple[str, ...] = SUPPORTED_PROTOCOL_VERSIONS,
) -> str:
    """Validate a negotiated ``protocolVersion`` against the supported set.

    Returns the version unchanged on success; raises
    :class:`McpProtocolError` (fail-closed) on an unsupported version.
    """
    if not isinstance(version, str) or not version:
        raise McpProtocolError("missing protocolVersion", {"version": repr(version)})
    if version not in allowed:
        raise McpProtocolError(
            f"unsupported MCP protocol version: {version}",
            {"version": version, "supported": list(allowed)},
        )
    return version


def extract_protocol_version(message: Mapping[str, Any]) -> str | None:
    """Pull ``protocolVersion`` out of a JSON-RPC message.

    Checks ``params.protocolVersion`` first (initialize request/result),
    then ``params._meta.protocolVersion`` (per-request era detection).
    """
    params = message.get("params")
    if isinstance(params, Mapping):
        v = params.get("protocolVersion")
        if isinstance(v, str) and v:
            return v
        meta = params.get("_meta")
        if isinstance(meta, Mapping):
            mv = meta.get("protocolVersion")
            if isinstance(mv, str) and mv:
                return mv
    # Result-side version (initialize response).
    result = message.get("result")
    if isinstance(result, Mapping):
        rv = result.get("protocolVersion")
        if isinstance(rv, str) and rv:
            return rv
    return None


def negotiate(server_version: str | None) -> str:
    """Validate the version a server reported during initialize.

    A missing version means a pre-versioning server: tolerated as LEGACY
    (interop), but callers should log the downgrade. An explicit but
    unsupported version raises - never silently downgrade to an unknown era.
    """
    if server_version is None:
        return PROTOCOL_LEGACY
    return validate_protocol_version(server_version)


def build_routing_headers(
    method: str,
    name: str | None = None,
    *,
    era: McpEra = McpEra.STATELESS,
    session_id: str | None = None,
) -> dict[str, str]:
    """Build request-routing headers for an outbound call.

    Stateless era: ``Mcp-Method`` + ``Mcp-Name`` only (``Mcp-Session-Id``
    is removed by spec - session state lives server-side, keyed
    externally). Legacy era additionally attaches ``Mcp-Session-Id`` when
    a session id was negotiated.
    """
    headers = {HEADER_METHOD: method}
    if name is not None:
        headers[HEADER_NAME] = name
    if era is McpEra.LEGACY and session_id:
        headers[HEADER_SESSION_ID] = session_id
    return headers


def route_from_headers(headers: Mapping[str, str]) -> tuple[str | None, str | None]:
    """Server-side: extract ``(method, name)`` routing info from headers.

    Header lookup is case-insensitive. Returns ``(None, None)`` when the
    routing headers are absent (caller falls back to JSON body routing).
    """
    lowered = {k.lower(): v for k, v in headers.items()}
    method = lowered.get(HEADER_METHOD.lower())
    name = lowered.get(HEADER_NAME.lower())
    return method, name


def is_stateless_request(headers: Mapping[str, str]) -> bool:
    """True when the request uses stateless-era routing (method/name headers
    present, no session id)."""
    method, _name = route_from_headers(headers)
    if method is None:
        return False
    lowered = {k.lower() for k in headers}
    return HEADER_SESSION_ID.lower() not in lowered


__all__ = [
    "DEFAULT_CLIENT_VERSION",
    "HEADER_METHOD",
    "HEADER_NAME",
    "HEADER_SESSION_ID",
    "PROTOCOL_LEGACY",
    "PROTOCOL_STATELESS",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "TOLERATED_LEGACY_VERSIONS",
    "McpEra",
    "McpProtocolError",
    "build_routing_headers",
    "era_for_version",
    "extract_protocol_version",
    "is_stateless_request",
    "negotiate",
    "route_from_headers",
    "validate_protocol_version",
]
