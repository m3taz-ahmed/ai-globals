"""Tests for runtime/mcp_protocol.py - dual-era version handling."""
from __future__ import annotations

import pytest

from runtime.mcp_protocol import (
    HEADER_METHOD,
    HEADER_NAME,
    HEADER_SESSION_ID,
    PROTOCOL_LEGACY,
    PROTOCOL_STATELESS,
    McpEra,
    McpProtocolError,
    build_routing_headers,
    era_for_version,
    extract_protocol_version,
    is_stateless_request,
    negotiate,
    route_from_headers,
    validate_protocol_version,
)


def test_supported_versions_validate():
    for v in ("2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"):
        assert validate_protocol_version(v) == v


def test_unknown_version_fail_closed():
    with pytest.raises(McpProtocolError):
        validate_protocol_version("1999-01-01")


def test_missing_version_raises():
    with pytest.raises(McpProtocolError):
        validate_protocol_version("")


def test_era_mapping():
    assert era_for_version(PROTOCOL_STATELESS) is McpEra.STATELESS
    assert era_for_version("2027-01-01") is McpEra.STATELESS
    assert era_for_version(PROTOCOL_LEGACY) is McpEra.LEGACY
    assert era_for_version("2024-11-05") is McpEra.LEGACY


def test_extract_from_params():
    msg = {"params": {"protocolVersion": "2026-07-28"}}
    assert extract_protocol_version(msg) == "2026-07-28"


def test_extract_from_meta():
    msg = {"params": {"_meta": {"protocolVersion": "2025-11-25"}}}
    assert extract_protocol_version(msg) == "2025-11-25"


def test_extract_from_result():
    msg = {"result": {"protocolVersion": "2025-06-18"}}
    assert extract_protocol_version(msg) == "2025-06-18"


def test_extract_missing():
    assert extract_protocol_version({"params": {}}) is None
    assert extract_protocol_version({}) is None


def test_negotiate_known():
    assert negotiate("2025-11-25") == "2025-11-25"


def test_negotiate_missing_is_legacy():
    assert negotiate(None) == PROTOCOL_LEGACY


def test_negotiate_unknown_raises():
    with pytest.raises(McpProtocolError):
        negotiate("0.0.1")


def test_stateless_headers_no_session():
    h = build_routing_headers("tools/call", "read_file", era=McpEra.STATELESS)
    assert h == {HEADER_METHOD: "tools/call", HEADER_NAME: "read_file"}
    assert HEADER_SESSION_ID not in h


def test_legacy_headers_include_session():
    h = build_routing_headers(
        "tools/call", "read_file", era=McpEra.LEGACY, session_id="abc"
    )
    assert h[HEADER_SESSION_ID] == "abc"


def test_route_from_headers_case_insensitive():
    m, n = route_from_headers({"mcp-method": "tools/call", "MCP-NAME": "x"})
    assert (m, n) == ("tools/call", "x")


def test_route_missing():
    assert route_from_headers({}) == (None, None)


def test_is_stateless_request():
    assert is_stateless_request({HEADER_METHOD: "tools/call"}) is True
    assert is_stateless_request(
        {HEADER_METHOD: "tools/call", HEADER_SESSION_ID: "s"}
    ) is False
    assert is_stateless_request({}) is False


def test_extract_non_str_meta_version():
    assert extract_protocol_version({"params": {"_meta": {"protocolVersion": 7}}}) is None


def test_extract_non_str_result_version():
    assert (
        extract_protocol_version({"result": {"protocolVersion": ["2026-07-28"]}})
        is None
    )


def test_headers_no_name():
    h = build_routing_headers("ping", None, era=McpEra.STATELESS)
    assert HEADER_NAME not in h and h[HEADER_METHOD] == "ping"
