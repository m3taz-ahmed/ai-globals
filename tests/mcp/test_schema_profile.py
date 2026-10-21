"""Tests for aizee_mcp/schema_profile.py (AIZEE_MCP_INPUT_SCHEMA_PROFILE)."""

from __future__ import annotations

from types import SimpleNamespace

from aizee_mcp.schema_profile import (
    apply_schema_profile,
    compact_schema_node,
    compact_tool_schema,
    schema_profile,
)


class TestCompactSchemaNode:
    def test_drops_guidance_keys(self):
        schema = {
            "type": "object",
            "title": "Tool input",
            "examples": [{"x": 1}],
            "$comment": "internal note",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path.\nExtra guidance line.",
                    "title": "Path",
                    "example": "a.py",
                }
            },
            "required": ["path"],
        }
        out = compact_schema_node(schema)
        assert "title" not in out and "examples" not in out and "$comment" not in out
        prop = out["properties"]["path"]
        assert prop == {"type": "string", "description": "File path."}
        assert out["required"] == ["path"]

    def test_description_keeps_first_nonempty_line_only(self):
        node = {"description": "  \nReal description.\nMore detail."}
        assert compact_schema_node(node) == {"description": "Real description."}

    def test_empty_description_removed(self):
        node = {"description": "   ", "type": "string"}
        assert compact_schema_node(node) == {"type": "string"}

    def test_nested_lists_compacted(self):
        node = {"anyOf": [{"title": "a", "type": "string"}, {"type": "null"}]}
        out = compact_schema_node(node)
        assert out == {"anyOf": [{"type": "string"}, {"type": "null"}]}

    def test_non_schema_values_passthrough(self):
        assert compact_schema_node(5) == 5
        assert compact_schema_node("x") == "x"
        assert compact_schema_node(None) is None


class TestCompactToolSchema:
    def test_compacts_tool_parameters_in_place(self):
        tool = SimpleNamespace(parameters={
            "type": "object",
            "title": "in",
            "properties": {"a": {"type": "string", "examples": ["1"]}},
        })
        compact_tool_schema(tool)
        assert "title" not in tool.parameters
        assert tool.parameters["properties"]["a"] == {"type": "string"}

    def test_tool_without_parameters_untouched(self):
        tool = SimpleNamespace()
        compact_tool_schema(tool)  # no crash
        tool2 = SimpleNamespace(parameters="not-a-dict")
        compact_tool_schema(tool2)
        assert tool2.parameters == "not-a-dict"


class TestApplySchemaProfile:
    def _manager(self, n: int = 2):
        tools = {
            f"t{i}": SimpleNamespace(parameters={"title": "x", "type": "object"})
            for i in range(n)
        }
        return SimpleNamespace(_tools=tools)

    def test_full_profile_is_noop(self):
        mgr = self._manager()
        assert apply_schema_profile(mgr, profile="full") == 0
        assert all("title" in t.parameters for t in mgr._tools.values())

    def test_compact_profile_compacts_all(self):
        mgr = self._manager(3)
        assert apply_schema_profile(mgr, profile="compact") == 3
        assert all("title" not in t.parameters for t in mgr._tools.values())

    def test_missing_tools_mapping_returns_zero(self):
        assert apply_schema_profile(SimpleNamespace(), profile="compact") == 0
        assert apply_schema_profile(SimpleNamespace(_tools=[]), profile="compact") == 0

    def test_env_default_full(self, monkeypatch):
        monkeypatch.delenv("AIZEE_MCP_INPUT_SCHEMA_PROFILE", raising=False)
        assert schema_profile() == "full"
        monkeypatch.setenv("AIZEE_MCP_INPUT_SCHEMA_PROFILE", "Compact")
        assert schema_profile() == "compact"
