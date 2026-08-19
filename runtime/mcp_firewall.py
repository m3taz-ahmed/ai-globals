#!/usr/bin/env python3
"""MCP Firewall — per-tool-call access control for the aiZee MCP server.

Inspired by Preloop's ``ToolAccessRule`` model: every MCP tool call is
evaluated against a priority-ordered rule set before execution. Rules
support ``allow`` / ``deny`` / ``require_approval`` actions with optional
condition expressions evaluated against the call arguments.

Condition expressions use a restricted Python subset (comparisons, boolean
operators, attribute/index access, literals) evaluated via ``_safe_eval`` —
never ``eval()``. This keeps the firewall deterministic and injection-safe.

Rule sources (first match wins, highest priority first):
1. ``runtime/policies/mcp_firewall.yaml`` — OS-level defaults
2. Project-local ``.aizee/mcp_firewall.yaml`` — overrides
3. Programmatic rules added via ``McpFirewall.add_rule``

Usage::

    from runtime.mcp_firewall import McpFirewall, FirewallVerdict
    fw = McpFirewall.from_yaml(Path("runtime/policies/mcp_firewall.yaml"))
    verdict = fw.evaluate("search_memory", {"query": "secret"})
    if verdict.action is FirewallAction.DENY:
        raise PolicyDeniedError("MCP_TOOL_DENIED", verdict.reason)
"""

from __future__ import annotations

import ast
import logging
import operator as op
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from runtime.enums import Decision
from runtime.schemas import AizeeError, ErrorSeverity, PolicyDeniedError

logger = logging.getLogger(__name__)


class FirewallAction(str, Enum):
    """Action the firewall can take on a tool call."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(frozen=True)
class FirewallVerdict:
    """Result of evaluating a tool call against the firewall."""

    action: FirewallAction
    rule_name: str
    reason: str = ""
    matched_condition: str | None = None


@dataclass
class ToolAccessRule:
    """A single firewall rule.

    Attributes:
        name: Stable identifier for audit/metrics.
        tool: Tool name pattern (``*`` wildcard supported, e.g. ``search_*``).
        action: allow / deny / require_approval.
        condition: Optional restricted Python expression evaluated against
            the call arguments dict. Empty means unconditional.
        priority: Higher priority rules are evaluated first (default 0).
        description: Human-readable rationale.
    """

    name: str
    tool: str
    action: FirewallAction
    condition: str = ""
    priority: int = 0
    description: str = ""

    def matches_tool(self, tool_name: str) -> bool:
        """Match tool name with ``*`` wildcard support."""
        if self.tool == "*":
            return True
        if self.tool.endswith("*"):
            return tool_name.startswith(self.tool[:-1])
        if self.tool.startswith("*"):
            return tool_name.endswith(self.tool[1:])
        return self.tool == tool_name


# --- Restricted expression evaluator (no eval/exec) ----------------------

_ALLOWED_BINOPS: dict[type, Any] = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Mod: op.mod,
    ast.Eq: op.eq,
    ast.NotEq: op.ne,
    ast.Lt: op.lt,
    ast.LtE: op.le,
    ast.Gt: op.gt,
    ast.GtE: op.ge,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}
_ALLOWED_UNARYOPS: dict[type, Any] = {
    ast.Not: op.not_,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def _safe_eval(expr: str, env: dict[str, Any]) -> bool:
    """Evaluate a restricted Python expression to a boolean.

    Supports: literals, names, comparisons, boolean ops, attribute access,
    subscript, ``in``/``not in``. Rejects calls, imports, comprehensions,
    assignments, and anything that is not a plain expression.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        logger.warning("firewall condition syntax error: %s — %s", expr, exc)
        return False
    if tree.body is None:
        return False
    return bool(_eval_node(tree.body, env))


def _eval_node(node: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.Attribute):
        return getattr(_eval_node(node.value, env), node.attr, None)
    if isinstance(node, ast.Subscript):
        target = _eval_node(node.value, env)
        key = _eval_node(node.slice, env)
        if isinstance(target, dict):
            return target.get(key)
        return target[key]
    if isinstance(node, ast.BinOp):
        fn = _ALLOWED_BINOPS.get(type(node.op))
        if fn is None:
            raise ValueError(f"unsupported binop {type(node.op).__name__}")
        return fn(_eval_node(node.left, env), _eval_node(node.right, env))
    if isinstance(node, ast.UnaryOp):
        fn = _ALLOWED_UNARYOPS.get(type(node.op))
        if fn is None:
            raise ValueError(f"unsupported unaryop {type(node.op).__name__}")
        return fn(_eval_node(node.operand, env))
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, env)
        for op_node, right_node in zip(node.ops, node.comparators, strict=True):
            fn = _ALLOWED_BINOPS.get(type(op_node))
            if fn is None:
                raise ValueError(f"unsupported compare {type(op_node).__name__}")
            right = _eval_node(right_node, env)
            if not fn(left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.BoolOp):
        fn = _ALLOWED_BINOPS[type(node.op)]
        result = _eval_node(node.values[0], env)
        for v in node.values[1:]:
            result = fn(result, _eval_node(v, env))
        return result
    if isinstance(node, ast.List):
        return [_eval_node(e, env) for e in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_eval_node(e, env) for e in node.elts)
    if isinstance(node, ast.Set):
        return {_eval_node(e, env) for e in node.elts}
    if isinstance(node, ast.Dict):
        out: dict[Any, Any] = {}
        for k, v in zip(node.keys, node.values, strict=True):
            if k is not None:
                out[_eval_node(k, env)] = _eval_node(v, env)
        return out
    raise ValueError(f"unsupported expression node {type(node).__name__}")


class McpFirewall:
    """Priority-ordered firewall for MCP tool calls.

    Rules are sorted by descending priority on load. The first rule whose
    ``tool`` pattern matches and whose ``condition`` (if any) evaluates true
    wins. If no rule matches, the default action is applied (configurable,
    ``allow`` by default).
    """

    def __init__(
        self,
        rules: list[ToolAccessRule] | None = None,
        default_action: FirewallAction = FirewallAction.ALLOW,
    ) -> None:
        self._rules: list[ToolAccessRule] = sorted(
            rules or [], key=lambda r: (-r.priority, r.name)
        )
        self.default_action = default_action
        self._denials: dict[str, int] = {}

    def add_rule(self, rule: ToolAccessRule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda r: (-r.priority, r.name))

    def evaluate(self, tool_name: str, args: dict[str, Any]) -> FirewallVerdict:
        """Evaluate a tool call against the rule set. First match wins."""
        for rule in self._rules:
            if not rule.matches_tool(tool_name):
                continue
            if rule.condition:
                try:
                    if not _safe_eval(rule.condition, args):
                        continue
                except Exception as exc:
                    logger.warning(
                        "firewall rule %s condition error: %s", rule.name, exc
                    )
                    continue
            if rule.action is FirewallAction.DENY:
                self._denials[rule.name] = self._denials.get(rule.name, 0) + 1
            return FirewallVerdict(
                action=rule.action,
                rule_name=rule.name,
                reason=rule.description or f"matched rule {rule.name}",
                matched_condition=rule.condition or None,
            )
        return FirewallVerdict(
            action=self.default_action,
            rule_name="default",
            reason="no rule matched",
        )

    def check(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Kernel-compatible check returning an action dict.

        Maps ``allow``→allow, ``deny``→deny, ``require_approval``→ask so the
        existing policy/guardian pipeline can consume the verdict uniformly.
        """
        verdict = self.evaluate(tool_name, args)
        mapping = {
            FirewallAction.ALLOW: Decision.ALLOW.value,
            FirewallAction.DENY: Decision.DENY.value,
            FirewallAction.REQUIRE_APPROVAL: Decision.ASK.value,
        }
        return {
            "decision": mapping[verdict.action],
            "rule": verdict.rule_name,
            "reason": verdict.reason,
            "tool": tool_name,
        }

    @property
    def rules(self) -> list[ToolAccessRule]:
        return list(self._rules)

    @property
    def denials(self) -> dict[str, int]:
        return dict(self._denials)

    @classmethod
    def from_yaml(cls, path: Path) -> McpFirewall:
        """Load firewall rules from a YAML file.

        Expected schema::

            default_action: allow
            rules:
              - name: deny-secret-search
                tool: search_memory
                action: deny
                condition: 'query == "secret"'
                priority: 10
                description: Block searches for secrets
        """
        if not path.exists():
            return cls()
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        default = FirewallAction(data.get("default_action", "allow"))
        rules: list[ToolAccessRule] = []
        for entry in data.get("rules", []):
            try:
                rules.append(
                    ToolAccessRule(
                        name=entry["name"],
                        tool=entry["tool"],
                        action=FirewallAction(entry["action"]),
                        condition=entry.get("condition", ""),
                        priority=int(entry.get("priority", 0)),
                        description=entry.get("description", ""),
                    )
                )
            except (KeyError, ValueError) as exc:
                logger.warning("skipping malformed firewall rule: %s — %s", entry, exc)
        return cls(rules=rules, default_action=default)

    def to_policy_denied(self, verdict: FirewallVerdict) -> PolicyDeniedError:
        """Convert a deny verdict into a PolicyDeniedError."""
        return PolicyDeniedError(
            f"MCP tool blocked by firewall rule '{verdict.rule_name}': {verdict.reason}",
            context={"rule": verdict.rule_name, "reason": verdict.reason},
        )


class McpFirewallError(AizeeError):
    """Raised when the firewall itself is misconfigured (not on deny)."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            error_code="MCP_FIREWALL_ERROR",
            message=message,
            severity=ErrorSeverity.MEDIUM,
            context=context,
        )
