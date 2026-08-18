#!/usr/bin/env python3
"""Lightweight guardian policy SDK for aiZee.

Re-implements the core patterns from guardian-angel:
- ActionRequest with tool name and attributes.
- DecisionStatus: allow, deny, require_approval.
- YAML/JSON policies with first-match semantics.
- Predicate rules using key/op/value and all/any combinators.
- invoke/ainvoke decorators and ApprovalRequiredError.
"""

from __future__ import annotations

import functools
import inspect
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

import yaml

from runtime.schemas import AizeeError, ErrorSeverity


class DecisionStatus(str, Enum):
    """Possible policy decisions."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class ApprovalRequiredError(AizeeError):
    """Raised when an action requires explicit approval."""

    def __init__(self, rule_name: str, message: str = "") -> None:
        self.rule_name = rule_name
        self.message = message
        super().__init__(
            "APPROVAL_REQUIRED",
            message or f"Action requires approval by rule {rule_name!r}",
            ErrorSeverity.MEDIUM,
            {"rule_name": rule_name},
        )


class GuardConfig:
    """Configuration for the guardian."""

    def __init__(
        self,
        default_decision: DecisionStatus = DecisionStatus.ALLOW,
        on_evaluation_error: DecisionStatus = DecisionStatus.DENY,
    ) -> None:
        self.default_decision = default_decision
        self.on_evaluation_error = on_evaluation_error


@dataclass
class ActionRequest:
    """A request to be authorized by the guardian."""

    tool: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    """Result of a policy evaluation."""

    status: DecisionStatus
    rule_name: str
    reason: str = ""


class _PredicateEvaluator:
    """Evaluate guardian-style predicate rules."""

    _ops: ClassVar[dict[str, Callable[[Any, Any], bool]]] = {
        "eq": lambda a, b: a == b,
        "ne": lambda a, b: a != b,
        "gt": lambda a, b: a > b,
        "gte": lambda a, b: a >= b,
        "lt": lambda a, b: a < b,
        "lte": lambda a, b: a <= b,
        "in": lambda a, b: a in b,
        "nin": lambda a, b: a not in b,
        "contains": lambda a, b: b in a if isinstance(a, (str, list, tuple)) else False,
        "regex": lambda a, b: bool(re.search(b, str(a))) if a is not None else False,
    }

    def __init__(self, attributes: dict[str, Any]) -> None:
        self._attributes = attributes

    def _resolve(self, key: str) -> Any:
        parts = key.split(".")
        value: Any = self._attributes
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    def evaluate_predicate(self, predicate: dict[str, Any]) -> bool:
        key = predicate.get("key")
        op = predicate.get("op", "eq")
        expected = predicate.get("value")
        if key is None:
            return False
        actual = self._resolve(str(key))
        fn = self._ops.get(op)
        if fn is None:
            raise ValueError(f"Unsupported operator: {op!r}")
        return fn(actual, expected)

    def evaluate_all(self, predicates: list[dict[str, Any]]) -> bool:
        return all(self.evaluate_predicate(p) for p in predicates)

    def evaluate_any(self, predicates: list[dict[str, Any]]) -> bool:
        return any(self.evaluate_predicate(p) for p in predicates)


class Guardian:
    """Policy engine for agent tool execution."""

    def __init__(self, rules: list[dict[str, Any]], config: GuardConfig | None = None) -> None:
        self.rules = rules
        self.config = config or GuardConfig()

    @classmethod
    def from_yaml(cls, path: str | Path, config: GuardConfig | None = None) -> Guardian:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(data.get("rules", []), config)

    @classmethod
    def from_json(cls, path: str | Path, config: GuardConfig | None = None) -> Guardian:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data.get("rules", []), config)

    def _match_rule(self, request: ActionRequest) -> Decision | None:
        evaluator = _PredicateEvaluator(request.attributes)
        for rule in self.rules:
            name = rule.get("name", "unnamed")
            tool = rule.get("tool")
            if tool is not None and tool != request.tool:
                continue

            matched = False
            try:
                if "all" in rule:
                    matched = evaluator.evaluate_all(rule["all"])
                elif "any" in rule:
                    matched = evaluator.evaluate_any(rule["any"])
                elif "predicate" in rule:
                    matched = evaluator.evaluate_predicate(rule["predicate"])
                else:
                    matched = True
            except Exception:
                if self.config.on_evaluation_error == DecisionStatus.DENY:
                    return Decision(DecisionStatus.DENY, name, "evaluation error")
                if self.config.on_evaluation_error == DecisionStatus.REQUIRE_APPROVAL:
                    return Decision(DecisionStatus.REQUIRE_APPROVAL, name, "evaluation error")
                continue

            if matched:
                decision = rule.get("decision", self.config.default_decision.value)
                return Decision(DecisionStatus(decision), name, rule.get("description", ""))

        return None

    def authorize(self, request: ActionRequest) -> Decision:
        decision = self._match_rule(request)
        if decision is not None:
            return decision
        return Decision(self.config.default_decision, "default", "no matching rule")

    def check(self, request: ActionRequest) -> None:
        decision = self.authorize(request)
        if decision.status == DecisionStatus.DENY:
            raise PermissionError(f"Policy denied by rule {decision.rule_name!r}")
        if decision.status == DecisionStatus.REQUIRE_APPROVAL:
            raise ApprovalRequiredError(decision.rule_name, decision.reason)


def invoke(guardian: Guardian, tool: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to enforce guardian policy on a function."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        requested_tool = tool or fn.__name__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attributes = kwargs.copy()
            if args:
                signature = inspect.signature(fn)
                for i, param in enumerate(signature.parameters):
                    if i < len(args):
                        attributes[param] = args[i]
            request = ActionRequest(tool=requested_tool, attributes=attributes)
            guardian.check(request)
            return fn(*args, **kwargs)

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            attributes = kwargs.copy()
            if args:
                signature = inspect.signature(fn)
                for i, param in enumerate(signature.parameters):
                    if i < len(args):
                        attributes[param] = args[i]
            request = ActionRequest(tool=requested_tool, attributes=attributes)
            guardian.check(request)
            return await fn(*args, **kwargs)

        if inspect.iscoroutinefunction(fn):
            return async_wrapper
        return wrapper

    return decorator


def ainvoke(guardian: Guardian, tool: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Async alias for invoke."""
    return invoke(guardian, tool)
