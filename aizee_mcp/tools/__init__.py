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

from .ads_tools import register_ads_tools
from .analytics_tools import register_analytics_tools
from .context_tools import register_context_tools
from .cro_tools import register_cro_tools
from .email_tools import register_email_tools
from .freelance_tools import register_freelance_tools
from .memory_tools import register_memory_tools
from .policy_tools import register_policy_tools
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
from .seo_tools import register_seo_tools
from .social_tools import register_social_tools
from .workflow_tools import register_workflow_tools

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
