"""Tests for aizee_mcp/tools/mcp_output_schemas.py — MCP output schema validation.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

import json

import pytest

from aizee_mcp.tools.mcp_output_schemas import (
    TOOL_OUTPUT_SCHEMAS,
    OutputSchemaError,
    SeoAuditPageOutput,
    get_tool_schema,
    safe_model_dump,
    validate_json_output,
    validate_output,
    validate_tool_output,
)


class TestValidateOutput:
    def test_valid_output(self) -> None:
        data = {
            "url": "https://example.com",
            "status_code": 200,
            "issues": [],
            "health_score": 100,
        }
        result = validate_output(data, SeoAuditPageOutput, "seo_audit_page")
        assert result.url == "https://example.com"
        assert result.health_score == 100

    def test_invalid_output_strict(self) -> None:
        data = {"url": "https://example.com", "health_score": "not-an-int"}
        with pytest.raises(OutputSchemaError):
            validate_output(data, SeoAuditPageOutput, "seo_audit_page", strict=True)

    def test_invalid_output_non_strict(self) -> None:
        data = {"url": "https://example.com"}  # Missing required fields
        # Non-strict should not raise for missing fields (model_construct)
        result = validate_output(data, SeoAuditPageOutput, "seo_audit_page", strict=False)
        assert result.url == "https://example.com"


class TestValidateJsonOutput:
    def test_valid_json(self) -> None:
        json_str = json.dumps({
            "url": "https://example.com",
            "issues": [{"type": "missing-title"}],
            "health_score": 80,
        })
        result = validate_json_output(json_str, SeoAuditPageOutput, "seo_audit_page")
        assert result.health_score == 80

    def test_invalid_json(self) -> None:
        with pytest.raises(OutputSchemaError):
            validate_json_output("not json{", SeoAuditPageOutput, "seo_audit_page")


class TestValidateToolOutput:
    def test_registered_tool(self) -> None:
        data = {"url": "https://example.com", "health_score": 90}
        result = validate_tool_output("seo_audit_page", data)
        assert result is not None
        assert isinstance(result, SeoAuditPageOutput)
        assert result.health_score == 90

    def test_unregistered_tool_returns_none(self) -> None:
        result = validate_tool_output("unknown_tool", {"data": "x"})
        assert result is None


class TestGetToolSchema:
    def test_known_tool(self) -> None:
        schema = get_tool_schema("seo_audit_page")
        assert schema is SeoAuditPageOutput

    def test_unknown_tool(self) -> None:
        assert get_tool_schema("nonexistent") is None

    def test_all_registered(self) -> None:
        assert "seo_audit_page" in TOOL_OUTPUT_SCHEMAS
        assert "seo_audit_site" in TOOL_OUTPUT_SCHEMAS
        assert "seo_check_cwv" in TOOL_OUTPUT_SCHEMAS
        assert "memory_search" in TOOL_OUTPUT_SCHEMAS
        assert "policy_check" in TOOL_OUTPUT_SCHEMAS


class TestSafeModelDump:
    def test_dumps_to_dict(self) -> None:
        model = SeoAuditPageOutput(url="https://example.com", health_score=90)
        dumped = safe_model_dump(model)
        assert dumped["url"] == "https://example.com"
        assert dumped["health_score"] == 90
        # Should be JSON-serializable
        json.dumps(dumped)
