#!/usr/bin/env python3
"""Policy engine for aiZee."""

from __future__ import annotations

import ast
import operator
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Literal, cast

import yaml

Action = Literal["allow", "ask", "deny"]

# Action-type classification for smart fallback when no explicit rule matches.
# This prevents read-only operations from hitting the blanket "ask" default
# and ensures destructive operations are always denied even if a policy file
# forgets to cover them. The YAML `default_action` still wins as the final
# fallback for truly unclassified actions.
_READ_ACTIONS: frozenset[str] = frozenset({
    "view", "read", "Read", "grep", "Glob", "graphify query", "graphify explain",
    "graphify path", "search", "query", "list", "get", "status", "analyze_budget",
    "get_metrics", "get_os_status", "git status", "git diff", "git log", "ls",
    "pwd", "detect_persona", "list_workflows", "list_capabilities", "show", "cat",
    "find", "glob", "head", "tail", "which", "where", "test",
})
_WRITE_ACTIONS: frozenset[str] = frozenset({
    "edit", "write", "apply", "deploy", "Bash", "exec", "install", "pip",
    "npm", "yarn", "composer", "migrate", "seed",
})
_DESTRUCTIVE_ACTIONS: frozenset[str] = frozenset({
    "rm", "delete", "truncate", "drop", "destroy", "wipe", "purge",
    "kill", "terminate", "force",
})


def _classify_action(action_type: str) -> Action:
    """Classify an action type into a default decision (allow/ask/deny)."""
    at = action_type.strip()
    if at in _DESTRUCTIVE_ACTIONS or any(d in at for d in ("rm -rf", "drop", "truncate", "destroy")):
        return "deny"
    if at in _READ_ACTIONS:
        return "allow"
    if at in _WRITE_ACTIONS:
        return "ask"
    return "ask"  # unknown → conservative ask


@dataclass
class PolicyRule:
    name: str
    condition: str
    action: Action
    description: str = ""
    approvers: list[str] = field(default_factory=list)


class _SafeEvaluator(ast.NodeVisitor):
    """AST-based safe evaluator for policy conditions.

    Supports:
    - comparisons: ==, !=, <, <=, >, >=
    - membership: in / not in
    - boolean: and / or / not
    - constants: str, int, float, list
    - variables: looked up from the action dict
    """

    _allowed_ops: ClassVar[dict[type, Any]] = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
    }

    def __init__(self, action: dict[str, Any]) -> None:
        self.action = action

    def visit(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.List):
            return [self.visit(elt) for elt in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self.visit(elt) for elt in node.elts)
        if isinstance(node, ast.Set):
            return {self.visit(elt) for elt in node.elts}
        if isinstance(node, ast.Name):
            return self.action.get(node.id)
        if isinstance(node, ast.Subscript):
            value = self.visit(node.value)
            key = self.visit(node.slice)
            try:
                return value[key]
            except (KeyError, TypeError, IndexError):
                return None
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self.visit(v) for v in node.values)
            if isinstance(node.op, ast.Or):
                return any(self.visit(v) for v in node.values)
            return False  # pragma: no cover
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not self.visit(node.operand)
        if isinstance(node, ast.Compare):
            left = self.visit(node.left)
            for op_node, comparator in zip(node.ops, node.comparators, strict=True):
                op = self._allowed_ops.get(type(op_node))
                if op is None:
                    return False
                right = self.visit(comparator)
                if not op(left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return self.visit(node.left) + self.visit(node.right)
        raise ValueError(f"Unsupported node: {type(node).__name__}")

    def evaluate(self, expression: str) -> bool:
        try:
            tree = ast.parse(expression, mode="eval")
            return bool(self.visit(tree))
        except Exception as exc:
            warnings.warn(f"Policy condition evaluation failed for '{expression}': {exc}", stacklevel=2)
            return False


class PolicyEngine:
    """Evaluates agent actions against YAML policies."""

    def __init__(self, os_root: Path, project_root: Path | None = None) -> None:
        self.os_root = os_root
        self.project_root = project_root
        self.rules: list[PolicyRule] = []
        self.default_action: Action = "ask"
        self._load()

    def _load(self) -> None:
        roots = [self.os_root]
        if self.project_root and self.project_root != self.os_root:
            roots.append(self.project_root)
        for root in roots:
            policy_dir = root / "runtime" / "policies"
            if not policy_dir.exists():
                continue
            default = policy_dir / "default.yaml"
            others = sorted(p for p in policy_dir.rglob("*.yaml") if p.name != "default.yaml")
            if default.exists():
                self._load_file(default)
            for path in others:
                self._load_file(path)

    def _load_file(self, path: Path) -> None:
        from runtime.schemas import PolicyRuleSchema

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        default_action = data.get("default_action", self.default_action)
        if default_action not in ("allow", "ask", "deny"):
            warnings.warn(f"Skipping malformed policy file {path}: invalid default_action", stacklevel=2)
            return
        self.default_action = cast(Action, default_action)
        for r in data.get("rules", []):
            if not isinstance(r, dict):
                warnings.warn(f"Invalid rule in {path}: {r}", stacklevel=2)
                continue
            if r.get("action") not in ("allow", "ask", "deny"):
                warnings.warn(f"Skipping rule with invalid action in {path}: {r.get('action')}", stacklevel=2)
                continue
            try:
                validated = PolicyRuleSchema(**r)
            except Exception as exc:
                warnings.warn(f"Skipping malformed rule in {path}: {exc}", stacklevel=2)
                continue
            self.rules.append(
                PolicyRule(
                    name=validated.name,
                    condition=validated.condition,
                    action=cast(Action, validated.action),
                    description=validated.description,
                    approvers=validated.approvers,
                )
            )

    def evaluate(self, action: dict[str, Any]) -> dict[str, Any]:
        """Evaluate an action and return decision."""
        for rule in self.rules:
            if _SafeEvaluator(action).evaluate(rule.condition):
                return {
                    "decision": rule.action,
                    "rule": rule.name,
                    "description": rule.description,
                    "approvers": rule.approvers,
                    "requires_approval": rule.action == "ask",
                }
        # Smart fallback: classify by action type instead of blanket default.
        # The YAML `default_action` is the final fallback for unclassified types.
        action_type = str(action.get("type", ""))
        classified = _classify_action(action_type)
        # If the configured default is "deny" (strict mode), honor it over classification.
        # Otherwise, use the classified decision for known types, fall back to configured default.
        if self.default_action == "deny":
            fallback: Action = "deny"
        elif classified != "ask" or action_type:
            fallback = classified
        else:
            fallback = self.default_action
        return {
            "decision": fallback,
            "rule": "default-classified",
            "description": f"Auto-classified as {fallback} based on action type '{action_type}'",
            "approvers": [],
            "requires_approval": fallback == "ask",
        }

    def can(self, action_type: str, **kwargs: Any) -> dict[str, Any]:
        # Policies reference `command` in membership checks; ensure it is a
        # string to avoid `NoneType` iteration warnings when the action does
        # not carry a shell command (e.g. `write`, `edit`).
        if "command" not in kwargs or kwargs.get("command") is None:
            kwargs["command"] = ""
        return self.evaluate({"type": action_type, **kwargs})
