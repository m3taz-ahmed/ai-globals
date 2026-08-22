#!/usr/bin/env python3
"""Tests for aizee_mcp.tools.schemas."""

from __future__ import annotations

from typing import ClassVar

from aizee_mcp.tools.schemas import (
    ALL_SCHEMAS,
    MemoryEntrySchema,
    PaginatedResultSchema,
    PluginSchema,
    PolicyDecisionSchema,
    RuleSchema,
    SkillSchema,
    TechStackSchema,
    WorkflowSchema,
)

# -- Mock objects ----------------------------------------------------------


class MockRule:
    rule = "no-unused-vars"
    file = "src/main.py"
    line = 42
    severity = "warning"
    code = "E001"
    description = "Variable is never used"


class MockSkill:
    name = "backend-api-expert"
    path = "/skills/backend-api-expert.md"
    persona = "API"
    triggers: ClassVar[list[str]] = ["/api-design", "REST API"]
    tech_stack: ClassVar[list[str]] = ["laravel-12", "filament-4"]


class MockWorkflow:
    id = "24"
    name = "laravel-architecture-setup"
    trigger = "/laravel-architecture"
    objective = "Scaffold Laravel architecture patterns"
    step_count = 22


class MockTechStack:
    name = "laravel"
    version = "12"
    objective = "Laravel 12 patterns and conventions"
    rule_count = 15


class MockDecision:
    status = "allow"
    rule_name = "allow-read"
    reason = "Read action permitted"
    tool = "Read"


class MockPlugin:
    name = "my-plugin"
    version = "1.0.0"
    status = "loaded"


class MockMemoryEntry:
    id = "mem-001"
    content = "Laravel 12 uses Repository pattern"
    category = "tech-stack"
    timestamp = "2026-08-19T10:00:00Z"
    metadata: ClassVar[dict[str, str]] = {"source": "github-study"}


# -- RuleSchema ------------------------------------------------------------


def test_rule_schema_to_dict():
    result = RuleSchema.to_dict(MockRule())
    assert set(result.keys()) == set(RuleSchema.JSON_STRUCTURE)
    assert result["rule"] == "no-unused-vars"
    assert result["file"] == "src/main.py"
    assert result["line"] == 42
    assert result["severity"] == "warning"
    assert result["code"] == "E001"
    assert result["description"] == "Variable is never used"


def test_rule_schema_to_dict_missing_attrs():
    """to_dict should handle objects with missing attributes gracefully."""
    class Empty:
        pass
    result = RuleSchema.to_dict(Empty())
    assert result["rule"] == ""
    assert result["line"] == 0


# -- SkillSchema -----------------------------------------------------------


def test_skill_schema_to_dict():
    result = SkillSchema.to_dict(MockSkill())
    assert set(result.keys()) == set(SkillSchema.JSON_STRUCTURE)
    assert result["name"] == "backend-api-expert"
    assert result["path"] == "/skills/backend-api-expert.md"
    assert result["persona"] == "API"
    assert result["triggers"] == ["/api-design", "REST API"]
    assert result["tech_stack"] == ["laravel-12", "filament-4"]


# -- WorkflowSchema --------------------------------------------------------


def test_workflow_schema_to_dict():
    result = WorkflowSchema.to_dict(MockWorkflow())
    assert set(result.keys()) == set(WorkflowSchema.JSON_STRUCTURE)
    assert result["id"] == "24"
    assert result["name"] == "laravel-architecture-setup"
    assert result["trigger"] == "/laravel-architecture"
    assert result["objective"] == "Scaffold Laravel architecture patterns"
    assert result["step_count"] == 22


# -- TechStackSchema -------------------------------------------------------


def test_tech_stack_schema_to_dict():
    result = TechStackSchema.to_dict(MockTechStack())
    assert set(result.keys()) == set(TechStackSchema.JSON_STRUCTURE)
    assert result["name"] == "laravel"
    assert result["version"] == "12"
    assert result["objective"] == "Laravel 12 patterns and conventions"
    assert result["rule_count"] == 15


# -- PolicyDecisionSchema --------------------------------------------------


def test_policy_decision_schema_to_dict():
    result = PolicyDecisionSchema.to_dict(MockDecision())
    assert set(result.keys()) == set(PolicyDecisionSchema.JSON_STRUCTURE)
    assert result["status"] == "allow"
    assert result["rule_name"] == "allow-read"
    assert result["reason"] == "Read action permitted"
    assert result["tool"] == "Read"


# -- PluginSchema ----------------------------------------------------------


def test_plugin_schema_to_dict():
    result = PluginSchema.to_dict(MockPlugin())
    assert set(result.keys()) == set(PluginSchema.JSON_STRUCTURE)
    assert result["name"] == "my-plugin"
    assert result["version"] == "1.0.0"
    assert result["status"] == "loaded"


# -- MemoryEntrySchema -----------------------------------------------------


def test_memory_entry_schema_to_dict():
    result = MemoryEntrySchema.to_dict(MockMemoryEntry())
    assert set(result.keys()) == set(MemoryEntrySchema.JSON_STRUCTURE)
    assert result["id"] == "mem-001"
    assert result["content"] == "Laravel 12 uses Repository pattern"
    assert result["category"] == "tech-stack"
    assert result["timestamp"] == "2026-08-19T10:00:00Z"
    assert result["metadata"] == {"source": "github-study"}


# -- PaginatedResultSchema -------------------------------------------------


def test_paginated_result_offset_pagination():
    items = [{"id": 1}, {"id": 2}]
    result = PaginatedResultSchema.to_dict(items, total=100, per_page=50)
    assert result["data"] == items
    assert result["meta"]["per_page"] == 50
    assert result["meta"]["total"] == 100
    assert "next_cursor" not in result["meta"]


def test_paginated_result_cursor_pagination():
    items = [{"id": 1}, {"id": 2}]
    result = PaginatedResultSchema.to_dict(items, next_cursor="abc123", per_page=25)
    assert result["data"] == items
    assert result["meta"]["per_page"] == 25
    assert result["meta"]["next_cursor"] == "abc123"
    assert "total" not in result["meta"]


def test_paginated_result_default_total():
    items = [{"id": 1}]
    result = PaginatedResultSchema.to_dict(items)
    assert result["meta"]["total"] == 1


# -- ALL_SCHEMAS registry --------------------------------------------------


def test_all_schemas_contains_all_keys():
    expected_keys = {
        "rule", "skill", "workflow", "tech_stack",
        "policy_decision", "plugin", "memory_entry",
        "seo_audit", "seo_cwv", "seo_schema",
    }
    assert set(ALL_SCHEMAS.keys()) == expected_keys


def test_all_schemas_values_match_class_constants():
    assert ALL_SCHEMAS["rule"] == RuleSchema.JSON_STRUCTURE
    assert ALL_SCHEMAS["skill"] == SkillSchema.JSON_STRUCTURE
    assert ALL_SCHEMAS["workflow"] == WorkflowSchema.JSON_STRUCTURE
    assert ALL_SCHEMAS["tech_stack"] == TechStackSchema.JSON_STRUCTURE
    assert ALL_SCHEMAS["policy_decision"] == PolicyDecisionSchema.JSON_STRUCTURE
    assert ALL_SCHEMAS["plugin"] == PluginSchema.JSON_STRUCTURE
    assert ALL_SCHEMAS["memory_entry"] == MemoryEntrySchema.JSON_STRUCTURE


# -- JSON_STRUCTURE completeness -------------------------------------------


def test_all_json_structures_are_non_empty():
    for name, structure in ALL_SCHEMAS.items():
        assert len(structure) > 0, f"{name} JSON_STRUCTURE is empty"
