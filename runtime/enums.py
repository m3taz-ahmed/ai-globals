#!/usr/bin/env python3
"""Centralized enums for AI Global OS runtime.

Replaces magic strings with type-safe enums across workflow, saga, and
kernel modules. Existing enums (DecisionStatus, StepStatus) remain in their
original modules for backward compatibility.
"""

from __future__ import annotations

from enum import Enum


class StepType(str, Enum):
    """Workflow step types parsed from markdown rules."""

    REQ = "REQ"
    CMD = "CMD"
    PROHIBIT = "PROHIBIT"


class SagaStatus(str, Enum):
    """Saga orchestration lifecycle status."""

    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATED = "compensated"
    FAILED = "failed"


class Decision(str, Enum):
    """Policy decision values returned by PolicyEngine.evaluate().

    Matches the ``Action`` Literal in policy.py ("allow", "ask", "deny").
    """

    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


class ActionResultStatus(str, Enum):
    """Status of a workflow or kernel action execution."""

    OK = "ok"
    ALLOWED = "allowed"
    DENIED = "denied"
    PROHIBITED = "prohibited"
    BUDGET_BLOCKED = "budget_blocked"
    NOOP = "noop"
    ERROR = "error"
    MCP_PARSE_ERROR = "mcp_parse_error"
    MCP_NOT_CONFIGURED = "mcp_not_configured"
    MCP_CALL_FAILED = "mcp_call_failed"
    TIMEOUT = "timeout"


class ExceedAction(str, Enum):
    """Budget on-exceed actions."""

    WARN = "warn"
    FALLBACK = "fallback"
    BLOCK = "block"
