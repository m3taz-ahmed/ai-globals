#!/usr/bin/env python3
"""Policy, budget, guardian, and metrics MCP tools."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from runtime.astryx import AstryxLinter
from runtime.guardian import ActionRequest
from runtime.metrics import format_metrics

from .common import _MAX_INPUT_LENGTH, is_safe_name, kernel


def register_policy_tools(mcp: FastMCP) -> None:
    """Register policy, budget, guardian, and metrics tools."""

    @mcp.tool()
    def check_policy(action: str, args: dict[str, Any] | None = None) -> str:
        """Check if an action is allowed by policy and budget."""
        result = kernel().act(action, **(args or {}))
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def analyze_budget() -> str:
        """Analyze current token and cost consumption across all budgets and scopes."""
        k = kernel()
        return json.dumps(
            {
                "usage": k.budget.usage,
                "budgets": {key: val.__dict__ for key, val in k.budget.budgets.items()},
            },
            indent=2,
            default=str,
        )

    @mcp.tool()
    def run_guardian_check(tool: str, attributes: dict[str, Any] | None = None) -> str:
        """Evaluate a tool request against guardian rules."""
        if not is_safe_name(tool):
            return json.dumps({"ok": False, "error": "Invalid tool name"})
        req = ActionRequest(tool=tool, attributes=attributes or {})
        k = kernel()
        decision = k.guardian.authorize(req)
        return json.dumps(
            {
                "ok": decision.status != k.guardian.config.default_decision,
                "status": decision.status,
                "rule": decision.rule_name,
                "reason": decision.reason,
            },
            indent=2,
        )

    @mcp.tool()
    def get_metrics() -> str:
        """Return Prometheus-compatible metrics for the OS."""
        return format_metrics(kernel())

    @mcp.tool()
    def get_os_status() -> str:
        """Return the runtime kernel status."""
        return json.dumps(kernel().status(), indent=2, default=str)

    @mcp.tool()
    def list_capabilities() -> str:
        """List the active sovereign capabilities."""
        return json.dumps(kernel().capabilities.list(), indent=2)

    @mcp.tool()
    def lint_python(code: str, max_lines: int = 50, max_params: int = 7) -> str:
        """Lint Python code using the Astryx AST linter."""
        if not isinstance(code, str) or not code or len(code) > _MAX_INPUT_LENGTH:
            return json.dumps({"ok": False, "error": "Invalid code"})
        linter = AstryxLinter(max_lines=max_lines, max_params=max_params)
        findings = linter.lint_text(code)
        return json.dumps({"ok": True, "findings": [finding.__dict__ for finding in findings]}, indent=2)
