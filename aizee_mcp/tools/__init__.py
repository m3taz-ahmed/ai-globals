"""MCP tool modules for aiZee server.

Organized by responsibility:
- memory_tools: memory search, ingest, graph
- workflow_tools: workflow, rules, MCP plan
- policy_tools: policy, budget, guardian, metrics
- context_tools: tech-stack, skills, changelog, active context
- schemas: JSON structure constants for MCP tool responses
"""

from .context_tools import register_context_tools
from .memory_tools import register_memory_tools
from .policy_tools import register_policy_tools
from .schemas import (
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
from .workflow_tools import register_workflow_tools

__all__ = [
    "ALL_SCHEMAS",
    "MemoryEntrySchema",
    "PaginatedResultSchema",
    "PluginSchema",
    "PolicyDecisionSchema",
    "RuleSchema",
    "SkillSchema",
    "TechStackSchema",
    "WorkflowSchema",
    "register_context_tools",
    "register_memory_tools",
    "register_policy_tools",
    "register_workflow_tools",
]
