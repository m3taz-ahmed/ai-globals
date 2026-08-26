#!/usr/bin/env python3
"""Policy engine for aiZee."""

from __future__ import annotations

import ast
import functools
import operator
import warnings
from collections.abc import Callable
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
#
# ``READ_ACTIONS`` is the SINGLE source of truth for read-only action
# classification; PolicyManager derives its guardian-skip set from it.
READ_ACTIONS: frozenset[str] = frozenset({
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
    if at in READ_ACTIONS:
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
    priority: int = 0  # Higher priority wins; tie → file order (GATE-B3)


def _safe_priority(raw: Any) -> int:
    """Parse priority value safely, defaulting to 0 on invalid input."""
    try:
        return int(raw)
    except (TypeError, ValueError):
        warnings.warn(f"Invalid priority value {raw!r}, defaulting to 0", stacklevel=2)
        return 0


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

    # YAML-style literals used in policy conditions. Without this mapping,
    # `flag == true` resolved BOTH sides to None when the attribute was
    # missing (None == None -> True), silently matching every action that
    # lacked the attribute — a privilege-escalation hole for allow rules.
    _yaml_literals: ClassVar[dict[str, Any]] = {
        "true": True,
        "false": False,
        "null": None,
        "none": None,
    }

    # Sentinel for missing attributes. When an action lacks a referenced
    # attribute, we return _MISSING (not None) so that comparisons like
    # `env != "prod"` fail-closed instead of matching (None != "prod" -> True).
    # This prevents allow-by-absence: a rule requiring env != "prod" must NOT
    # match actions that have no env attribute at all.
    _MISSING: ClassVar[object] = object()

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
            if node.id in self._yaml_literals:
                return self._yaml_literals[node.id]
            # Return _MISSING sentinel for absent attributes so comparisons
            # fail-closed (see _MISSING docstring).
            if node.id in self.action:
                return self.action[node.id]
            return self._MISSING
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
                # Fail-closed: if either operand is a missing attribute,
                # the comparison must NOT match (prevents allow-by-absence).
                if left is self._MISSING or right is self._MISSING:
                    return False
                try:
                    if not op(left, right):
                        return False
                except TypeError:
                    # e.g. `'x' in missing_attr` (None is not iterable).
                    # A non-evaluable comparison must NOT match.
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
            # guardian.yaml and probity.yaml use separate schemas loaded by
            # Guardian.from_yaml / Guardrails (see PolicyManager). Exclude them
            # from the generic policy loader to avoid spurious "invalid action"
            # warnings.
            _excluded = {"default.yaml", "guardian.yaml", "probity.yaml", "mcp_firewall.yaml"}
            others = sorted(
                p
                for p in policy_dir.rglob("*.yaml")
                if p.name not in _excluded and "examples" not in p.parts
            )
            if default.exists():
                self._load_file(default, is_default=True)
            for path in others:
                self._load_file(path)

    def _load_file(self, path: Path, *, is_default: bool = False) -> None:
        from runtime.schemas import PolicyRuleSchema

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        # Only default.yaml may set default_action (GATE-B3: prevents
        # alphabetically-last YAML from silently clobbering engine-wide default).
        if "default_action" in data:
            if is_default:
                default_action = data.get("default_action", self.default_action)
                if default_action not in ("allow", "ask", "deny"):
                    warnings.warn(f"Skipping malformed default_action in {path}", stacklevel=2)
                else:
                    self.default_action = cast(Action, default_action)
            else:
                warnings.warn(
                    f"Policy file {path.name} defines default_action but is not "
                    "default.yaml — ignored. Move default_action to default.yaml.",
                    stacklevel=2,
                )
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
                    priority=_safe_priority(r.get("priority", 0)),
                )
            )

    def evaluate(self, action: dict[str, Any]) -> dict[str, Any]:
        """Evaluate an action and return decision.

        Rules are evaluated in priority order (highest first); ties broken by
        file order (insertion order). This makes precedence deterministic and
        independent of filename sorting (GATE-B3).
        """
        # Sort by priority descending; stable sort preserves file order for ties.
        ordered = sorted(enumerate(self.rules), key=lambda pair: (-pair[1].priority, pair[0]))
        for _, rule in ordered:
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
        elif classified != "ask":
            fallback = classified
        else:
            # classified == "ask" (a genuine ask-type OR an unrecognized type).
            # Honor the configured default_action instead of always forcing
            # "ask" — this fixes `default_action: allow` having no effect (B6).
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


# ---------------------------------------------------------------------------
# Guardrail Tripwire pattern (adapted from OpenAI Agents SDK)
#
# Guardrails are functions wrapped via @input_guardrail / @output_guardrail
# decorators. They return a GuardrailResult with tripwire_triggered. If
# tripped, the guardrail chain halts immediately. This is an ADDITIONAL
# policy layer on top of the existing PolicyEngine — it does not replace
# PolicyManager.check() or the YAML rule engine.
# ---------------------------------------------------------------------------

GuardrailPhase = Literal["input", "output"]
GuardrailDecision = Literal["allow", "deny", "ask"]


@dataclass
class GuardrailResult:
    """Result of a guardrail evaluation.

    Adapted from OpenAI Agents SDK ``GuardrailFunctionOutput``:
    - ``tripwire_triggered`` halts the guardrail chain if True.
    - ``output_info`` carries structured audit data.
    - ``decision`` maps to aiZee's allow/deny/ask policy vocabulary.
    """

    tripwire_triggered: bool
    output_info: dict[str, Any] = field(default_factory=dict)
    decision: GuardrailDecision = "allow"


# A guardrail function takes a context dict and returns a GuardrailResult.
GuardrailFunction = Callable[[dict[str, Any]], GuardrailResult]


class GuardrailRegistry:
    """Stores guardrails by name and phase (input/output).

    ``run_guardrails`` runs all registered guardrails for a phase in
    registration order. The first guardrail with ``tripwire_triggered=True``
    halts the chain and its result is returned. If no tripwire triggers,
    an allow result is returned.
    """

    def __init__(self) -> None:
        self._guardrails: dict[GuardrailPhase, dict[str, GuardrailFunction]] = {
            "input": {},
            "output": {},
        }
        self._order: dict[GuardrailPhase, list[str]] = {"input": [], "output": []}

    def register(
        self,
        phase: GuardrailPhase,
        name: str,
        func: GuardrailFunction,
    ) -> None:
        """Register a guardrail function for a phase.

        Re-registering an existing name replaces the function but preserves
        its original position in the evaluation order.
        """
        if name not in self._guardrails[phase]:
            self._order[phase].append(name)
        self._guardrails[phase][name] = func

    def unregister(self, phase: GuardrailPhase, name: str) -> None:
        """Remove a guardrail by name."""
        self._guardrails[phase].pop(name, None)
        if name in self._order[phase]:
            self._order[phase].remove(name)

    def list_guardrails(self, phase: GuardrailPhase) -> list[str]:
        """Return the ordered list of guardrail names for a phase."""
        return list(self._order[phase])

    def run_guardrails(
        self,
        phase: GuardrailPhase,
        context: dict[str, Any],
    ) -> GuardrailResult:
        """Run all registered guardrails for a phase in order.

        Halts on the first ``tripwire_triggered=True`` result.
        Returns an allow result if no tripwire triggers.
        """
        for name in self._order[phase]:
            func = self._guardrails[phase][name]
            result = func(context)
            if result.tripwire_triggered:
                # Annotate output_info with the guardrail name for audit.
                if "guardrail" not in result.output_info:
                    result.output_info["guardrail"] = name
                return result
        return GuardrailResult(tripwire_triggered=False)

    def clear(self) -> None:
        """Remove all registered guardrails (useful for tests)."""
        self._guardrails = {"input": {}, "output": {}}
        self._order = {"input": [], "output": []}


# Module-level default registry used by the decorators and the Guardian.
default_guardrail_registry = GuardrailRegistry()


def input_guardrail(
    name: str | None = None,
    *,
    registry: GuardrailRegistry | None = None,
) -> Callable[[GuardrailFunction], GuardrailFunction]:
    """Decorator that registers a function as an input guardrail.

    Usage::

        @input_guardrail("no_destructive")
        def check_destructive(context: dict[str, Any]) -> GuardrailResult:
            ...

    The wrapped function remains directly callable. When ``name`` is
    omitted, the function's ``__name__`` is used.
    """

    def decorator(func: GuardrailFunction) -> GuardrailFunction:
        reg = registry if registry is not None else default_guardrail_registry
        reg.register("input", name or func.__name__, func)

        @functools.wraps(func)
        def wrapper(context: dict[str, Any]) -> GuardrailResult:
            return func(context)

        return wrapper

    return decorator


def output_guardrail(
    name: str | None = None,
    *,
    registry: GuardrailRegistry | None = None,
) -> Callable[[GuardrailFunction], GuardrailFunction]:
    """Decorator that registers a function as an output guardrail.

    Usage::

        @output_guardrail("no_secrets_in_output")
        def check_secrets(context: dict[str, Any]) -> GuardrailResult:
            ...

    The wrapped function remains directly callable. When ``name`` is
    omitted, the function's ``__name__`` is used.
    """

    def decorator(func: GuardrailFunction) -> GuardrailFunction:
        reg = registry if registry is not None else default_guardrail_registry
        reg.register("output", name or func.__name__, func)

        @functools.wraps(func)
        def wrapper(context: dict[str, Any]) -> GuardrailResult:
            return func(context)

        return wrapper

    return decorator
