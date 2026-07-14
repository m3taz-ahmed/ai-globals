#!/usr/bin/env python3
"""Policy engine for AI Global OS."""

from __future__ import annotations

import ast
import operator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Literal

import yaml

Action = Literal["allow", "ask", "deny"]


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
            return False
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
        except Exception:
            return False


class PolicyEngine:
    """Evaluates agent actions against YAML policies."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.rules: list[PolicyRule] = []
        self.default_action: Action = "ask"
        self._load()

    def _load(self) -> None:
        default = self.root / "runtime" / "policies" / "default.yaml"
        if default.exists():
            self._load_file(default)

    def _load_file(self, path: Path) -> None:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        self.default_action = data.get("default_action", "ask")
        for r in data.get("rules", []):
            self.rules.append(
                PolicyRule(
                    name=r["name"],
                    condition=r["condition"],
                    action=r["action"],
                    description=r.get("description", ""),
                    approvers=r.get("approvers", []),
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
                }
        return {"decision": self.default_action, "rule": "default", "description": ""}

    def can(self, action_type: str, **kwargs: Any) -> dict[str, Any]:
        return self.evaluate({"type": action_type, **kwargs})
