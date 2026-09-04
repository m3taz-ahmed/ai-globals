#!/usr/bin/env python3
"""JSON structure constants for MCP tool responses.

Inspired by Koel's ``SongResource::JSON_STRUCTURE`` pattern: each API
resource declares its response shape as a class-level constant, enabling
structured response validation and documentation.

Usage in MCP tools::

    from aizee_mcp.tools.schemas import RuleSchema, PaginatedRulesSchema

    def query_rules(...) -> dict[str, Any]:
        rules = [...]
        return {
            "data": [RuleSchema.to_dict(r) for r in rules],
            "meta": {"total": len(rules), "page": 1},
        }

Test against structure::

    assert set(response["data"][0].keys()) == set(RuleSchema.JSON_STRUCTURE)
"""

from __future__ import annotations

from typing import Any, ClassVar


class RuleSchema:
    """JSON structure for a single rule response (MCP tool: query_rules)."""

    JSON_STRUCTURE: ClassVar[list[str]] = [
        "rule",
        "file",
        "line",
        "severity",
        "code",
        "description",
    ]

    @staticmethod
    def to_dict(rule: Any) -> dict[str, Any]:
        """Convert a rule object to a dict matching JSON_STRUCTURE."""
        return {
            "rule": getattr(rule, "rule", ""),
            "file": getattr(rule, "file", ""),
            "line": getattr(rule, "line", 0),
            "severity": getattr(rule, "severity", "info"),
            "code": getattr(rule, "code", ""),
            "description": getattr(rule, "description", ""),
        }


class SkillSchema:
    """JSON structure for a single skill response (MCP tool: query_skills)."""

    JSON_STRUCTURE: ClassVar[list[str]] = [
        "name",
        "path",
        "persona",
        "triggers",
        "tech_stack",
    ]

    @staticmethod
    def to_dict(skill: Any) -> dict[str, Any]:
        return {
            "name": getattr(skill, "name", ""),
            "path": str(getattr(skill, "path", "")),
            "persona": getattr(skill, "persona", ""),
            "triggers": getattr(skill, "triggers", []),
            "tech_stack": getattr(skill, "tech_stack", []),
        }


class WorkflowSchema:
    """JSON structure for a single workflow response (MCP tool: query_workflows)."""

    JSON_STRUCTURE: ClassVar[list[str]] = [
        "id",
        "name",
        "trigger",
        "objective",
        "step_count",
    ]

    @staticmethod
    def to_dict(workflow: Any) -> dict[str, Any]:
        return {
            "id": getattr(workflow, "id", ""),
            "name": getattr(workflow, "name", ""),
            "trigger": getattr(workflow, "trigger", ""),
            "objective": getattr(workflow, "objective", ""),
            "step_count": getattr(workflow, "step_count", 0),
        }


class TechStackSchema:
    """JSON structure for a single tech-stack entry (MCP tool: query_tech_stack)."""

    JSON_STRUCTURE: ClassVar[list[str]] = [
        "name",
        "version",
        "objective",
        "rule_count",
    ]

    @staticmethod
    def to_dict(tech: Any) -> dict[str, Any]:
        return {
            "name": getattr(tech, "name", ""),
            "version": getattr(tech, "version", ""),
            "objective": getattr(tech, "objective", ""),
            "rule_count": getattr(tech, "rule_count", 0),
        }


class PolicyDecisionSchema:
    """JSON structure for a policy decision (MCP tool: check_policy)."""

    JSON_STRUCTURE: ClassVar[list[str]] = [
        "status",
        "rule_name",
        "reason",
        "tool",
    ]

    @staticmethod
    def to_dict(decision: Any) -> dict[str, Any]:
        return {
            "status": str(getattr(decision, "status", "allow")),
            "rule_name": getattr(decision, "rule_name", ""),
            "reason": getattr(decision, "reason", ""),
            "tool": getattr(decision, "tool", ""),
        }


class PaginatedResultSchema:
    """JSON structure for paginated list responses.

    Inspired by Koel's ``PAGINATION_JSON_STRUCTURE`` and
    ``CURSOR_PAGINATION_JSON_STRUCTURE`` constants.
    """

    PAGINATION_JSON_STRUCTURE: ClassVar[dict[str, Any]] = {
        "data": [],
        "links": ["first", "last", "prev", "next"],
        "meta": ["current_page", "from", "to", "per_page", "total"],
    }

    CURSOR_PAGINATION_JSON_STRUCTURE: ClassVar[dict[str, Any]] = {
        "data": [],
        "links": ["first", "last", "prev", "next"],
        "meta": ["path", "per_page", "next_cursor", "prev_cursor"],
    }

    @staticmethod
    def to_dict(
        items: list[dict[str, Any]],
        total: int | None = None,
        next_cursor: str | None = None,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """Build a paginated response dict matching the declared structures."""
        result: dict[str, Any] = {"data": items}
        if next_cursor is not None:
            result["links"] = ["first", "next"]
            result["meta"] = {
                "path": "",
                "per_page": per_page,
                "next_cursor": next_cursor,
                "prev_cursor": None,
            }
        else:
            count = total if total is not None else len(items)
            result["links"] = ["first", "last", "prev", "next"]
            result["meta"] = {
                "current_page": 1,
                "from": 1 if count else 0,
                "to": count,
                "per_page": per_page,
                "total": count,
            }
        return result


class PluginSchema:
    """JSON structure for a single plugin response (MCP tool: list_plugins)."""

    JSON_STRUCTURE: ClassVar[list[str]] = [
        "name",
        "version",
        "status",
    ]

    @staticmethod
    def to_dict(plugin: Any) -> dict[str, Any]:
        return {
            "name": getattr(plugin, "name", ""),
            "version": getattr(plugin, "version", "0.1.0"),
            "status": getattr(plugin, "status", "loaded"),
        }


class MemoryEntrySchema:
    """JSON structure for a memory entry (MCP tool: query_memory)."""

    JSON_STRUCTURE: ClassVar[list[str]] = [
        "id",
        "content",
        "category",
        "timestamp",
        "metadata",
    ]

    @staticmethod
    def to_dict(entry: Any) -> dict[str, Any]:
        return {
            "id": getattr(entry, "id", ""),
            "content": getattr(entry, "content", ""),
            "category": getattr(entry, "category", ""),
            "timestamp": getattr(entry, "timestamp", ""),
            "metadata": getattr(entry, "metadata", {}),
        }


class SeoAuditSchema:
    """JSON structure for an SEO audit page response (MCP tool: seo_audit_page)."""

    JSON_STRUCTURE: ClassVar[list[str]] = [
        "ok",
        "url",
        "status",
        "score",
        "title",
        "description",
        "canonical",
        "h1_count",
        "h1s",
        "h2_count",
        "word_count",
        "content_hash",
        "image_count",
        "link_count",
        "json_ld_count",
        "og_tags",
        "issues",
        "issue_count",
    ]


class SeoCwvSchema:
    """JSON structure for a Core Web Vitals response (MCP tool: seo_check_cwv)."""

    JSON_STRUCTURE: ClassVar[list[str]] = [
        "ok",
        "url",
        "strategy",
        "metrics",
        "all_good",
        "note",
    ]


class SeoSchemaSchema:
    """JSON structure for a schema validation response (MCP tool: seo_validate_schema)."""

    JSON_STRUCTURE: ClassVar[list[str]] = [
        "ok",
        "url",
        "schema_count",
        "active",
        "deprecated",
        "schemas",
        "note",
    ]


ALL_SCHEMAS: dict[str, list[str]] = {
    "rule": RuleSchema.JSON_STRUCTURE,
    "skill": SkillSchema.JSON_STRUCTURE,
    "workflow": WorkflowSchema.JSON_STRUCTURE,
    "tech_stack": TechStackSchema.JSON_STRUCTURE,
    "policy_decision": PolicyDecisionSchema.JSON_STRUCTURE,
    "plugin": PluginSchema.JSON_STRUCTURE,
    "memory_entry": MemoryEntrySchema.JSON_STRUCTURE,
    "seo_audit": SeoAuditSchema.JSON_STRUCTURE,
    "seo_cwv": SeoCwvSchema.JSON_STRUCTURE,
    "seo_schema": SeoSchemaSchema.JSON_STRUCTURE,
    "pagination": PaginatedResultSchema.PAGINATION_JSON_STRUCTURE["meta"],
    "cursor_pagination": PaginatedResultSchema.CURSOR_PAGINATION_JSON_STRUCTURE["meta"],
}




