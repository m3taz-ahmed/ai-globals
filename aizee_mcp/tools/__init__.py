"""MCP tool modules for aiZee server.

Organized by responsibility:
- memory_tools: memory search, ingest, graph
- workflow_tools: workflow, rules, MCP plan
- policy_tools: policy, budget, guardian, metrics
- context_tools: tech-stack, skills, changelog, active context
- seo_tools: SEO audit, CWV, schema, content, GEO, GSC, opportunities
- ads_tools: paid advertising (Google/Meta/TikTok/LinkedIn Ads)
- analytics_tools: GA4, Mixpanel, attribution, funnel, CAC/LTV
- cro_tools: conversion rate optimization, A/B testing, heatmaps
- email_tools: email marketing, sequences, campaigns, subscriptions
- freelance_tools: Arabic freelance platforms (Mostaql/Khamsat)
- social_tools: social media scheduling, analytics, listening
- schemas: JSON structure constants for MCP tool responses
"""

from __future__ import annotations

import logging
from typing import Any

from .schemas import (
    ALL_SCHEMAS,
    MemoryEntrySchema,
    PaginatedResultSchema,
    PluginSchema,
    PolicyDecisionSchema,
    RuleSchema,
    SeoAuditSchema,
    SeoCwvSchema,
    SeoSchemaSchema,
    SkillSchema,
    TechStackSchema,
    WorkflowSchema,
)

_logger = logging.getLogger(__name__)


def _optional_register(module_name: str, attr_name: str) -> Any:
    """Import one register callable; return None (with warning) on failure.

    A single broken tool module must not crash the whole ``aizee_mcp.tools``
    package — the server's per-module fault isolation only runs if this
    import succeeds first.
    """
    try:
        module = __import__(f"aizee_mcp.tools.{module_name}", fromlist=[attr_name])
        return getattr(module, attr_name)
    except Exception as exc:
        _logger.warning("MCP tool module %s unavailable: %s", module_name, exc)
        return None


register_ads_tools = _optional_register("ads_tools", "register_ads_tools")
register_analytics_tools = _optional_register("analytics_tools", "register_analytics_tools")
register_context_tools = _optional_register("context_tools", "register_context_tools")
register_cro_tools = _optional_register("cro_tools", "register_cro_tools")
register_email_tools = _optional_register("email_tools", "register_email_tools")
register_freelance_tools = _optional_register("freelance_tools", "register_freelance_tools")
register_memory_tools = _optional_register("memory_tools", "register_memory_tools")
register_policy_tools = _optional_register("policy_tools", "register_policy_tools")
register_seo_tools = _optional_register("seo_tools", "register_seo_tools")
register_social_tools = _optional_register("social_tools", "register_social_tools")
register_workflow_tools = _optional_register("workflow_tools", "register_workflow_tools")

__all__ = [
    "ALL_SCHEMAS",
    "MemoryEntrySchema",
    "PaginatedResultSchema",
    "PluginSchema",
    "PolicyDecisionSchema",
    "RuleSchema",
    "SeoAuditSchema",
    "SeoCwvSchema",
    "SeoSchemaSchema",
    "SkillSchema",
    "TechStackSchema",
    "WorkflowSchema",
    "register_ads_tools",
    "register_analytics_tools",
    "register_context_tools",
    "register_cro_tools",
    "register_email_tools",
    "register_freelance_tools",
    "register_memory_tools",
    "register_policy_tools",
    "register_seo_tools",
    "register_social_tools",
    "register_workflow_tools",
]
