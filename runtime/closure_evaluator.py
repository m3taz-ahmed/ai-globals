#!/usr/bin/env python3
"""Closure evaluator with automatic dependency injection.

Inspired by Filament's ``EvaluatesClosures`` trait: evaluates callable values
with automatic parameter resolution by name, type, default value, or
evaluation identifier. Enables writing policy/guardian rules as closures
with typed parameters without manual dependency injection.

Example::

    evaluator = ClosureEvaluator(evaluation_identifier="action")
    result = evaluator.evaluate(
        my_closure,
        named_injections={"action": "Write", "path": "/src/main.py"},
        typed_injections={Budget: budget_instance},
    )

Resolution order for each closure parameter:
1. Named injection (exact parameter name match)
2. Typed injection (exact parameter annotation match)
3. Default dependency by name (subclass override)
4. Default dependency by type (subclass override)
5. Evaluation identifier (if parameter name matches)
6. Parameter default value (if available)
7. None (if parameter is optional)
8. Raise BindingResolutionError otherwise
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity


class _MISSING:
    """Sentinel class distinguishing "no value" from explicit ``None``.

    Identity-compared (``is _MISSING``); never instantiated.
    """


class ClosureResolutionError(AizeeError):
    """Raised when a closure parameter cannot be resolved."""

    def __init__(self, param_name: str, closure_name: str) -> None:
        super().__init__(
            "CLOSURE_RESOLUTION_ERROR",
            f"Unable to resolve dependency '{param_name}' for closure '{closure_name}'",
            ErrorSeverity.MEDIUM,
            {"param_name": param_name, "closure_name": closure_name},
        )


class ClosureEvaluator:
    """Evaluate closures with automatic dependency injection.

    Inspired by Filament's ``EvaluatesClosures`` trait. Resolves closure
    parameters by name, type, default, or evaluation identifier.

    WARNING: ``evaluate`` invokes the given callable with resolved args.
    Only pass trusted closures — arbitrary callables execute with the
    caller's privileges (code-execution risk if closures come from
    untrusted input).

    Attributes:
        evaluation_identifier: Name that maps to ``self`` if a closure
            parameter has this name (e.g., "action", "component").
    """

    def __init__(self, evaluation_identifier: str | None = None) -> None:
        self.evaluation_identifier = evaluation_identifier

    def evaluate(
        self,
        value: Any,
        named_injections: dict[str, Any] | None = None,
        typed_injections: dict[Any, Any] | None = None,
    ) -> Any:
        """Evaluate a value, injecting dependencies if it's a callable.

        Non-callable values are returned as-is. Callables have their
        parameters resolved and are invoked with the resolved dependencies.
        """
        if not callable(value) or isinstance(value, type):
            return value

        named = named_injections or {}
        typed = typed_injections or {}
        dependencies = self._resolve_dependencies(value, named, typed)
        return value(*dependencies)

    def _resolve_dependencies(
        self,
        closure: Callable[..., Any],
        named: dict[str, Any],
        typed: dict[Any, Any],
    ) -> list[Any]:
        """Resolve all parameters of a closure to concrete values.

        VAR_KEYWORD (``**kwargs``) parameters are skipped — keyword args
        are passed via ``evaluate``'s ``named_injections`` and handled
        by the caller if needed. VAR_POSITIONAL (``*args``) resolves to
        nothing (empty), so the closure receives no positional args.
        """
        sig = inspect.signature(closure)
        closure_name = getattr(closure, "__name__", "<anonymous>")
        dependencies: list[Any] = []

        for param in sig.parameters.values():
            if param.kind == param.VAR_KEYWORD:
                continue
            if param.kind == param.VAR_POSITIONAL:
                continue
            dep = self._resolve_single_param(param, named, typed, closure_name)
            dependencies.append(dep)

        return dependencies

    def _try_named(self, param_name: str, named: dict[str, Any]) -> Any:
        """Step 1: Named injection (exact parameter name match)."""
        return named.get(param_name, _MISSING)

    def _try_typed(self, annotation: Any, typed: dict[Any, Any]) -> Any:
        """Step 2: Typed injection (exact annotation match)."""
        if annotation is not inspect.Parameter.empty and annotation in typed:
            return typed[annotation]
        return _MISSING

    def _try_default_by_name(self, param_name: str) -> Any:
        """Step 3: Default dependency by name (subclass override)."""
        return self.resolve_default_by_name(param_name)

    def _try_default_by_type(self, annotation: Any) -> Any:
        """Step 4: Default dependency by type (subclass override)."""
        if annotation is not inspect.Parameter.empty:
            return self.resolve_default_by_type(annotation)
        return _MISSING

    def _try_evaluation_identifier(self, param_name: str) -> Any:
        """Step 5: Evaluation identifier (if parameter name matches)."""
        if self.evaluation_identifier and param_name == self.evaluation_identifier:
            return self
        return _MISSING

    def _resolve_single_param(
        self,
        param: inspect.Parameter,
        named: dict[str, Any],
        typed: dict[Any, Any],
        closure_name: str,
    ) -> Any:
        """Resolve a single closure parameter using the resolution order."""
        param_name = param.name
        annotation = param.annotation

        # Steps 1-5: try each resolution strategy in order
        for value in (
            self._try_named(param_name, named),
            self._try_typed(annotation, typed),
            self._try_default_by_name(param_name),
            self._try_default_by_type(annotation),
            self._try_evaluation_identifier(param_name),
        ):
            if value is not _MISSING:
                return value

        # Step 6: Parameter default value (if available)
        if param.default is not inspect.Parameter.empty:
            return param.default

        # Step 7: Raise resolution error (VAR_* kinds are skipped in
        # _resolve_dependencies, so no VAR fallback is reachable here).
        raise ClosureResolutionError(param_name, closure_name)

    def resolve_default_by_name(self, param_name: str) -> Any:
        """Override in subclass to provide default dependencies by name.

        Return ``_MISSING`` to indicate no default found (not a valid dependency).
        Explicit ``None`` is a valid dependency and is returned as-is.
        """
        return _MISSING

    def resolve_default_by_type(self, param_type: type) -> Any:
        """Override in subclass to provide default dependencies by type.

        Return ``_MISSING`` to indicate no default found (not a valid dependency).
        Explicit ``None`` is a valid dependency and is returned as-is.
        """
        return _MISSING


class GuardianClosureEvaluator(ClosureEvaluator):
    """Closure evaluator specialized for guardian/policy rule evaluation.

    Provides default injections for common guardian parameters:
    - ``action``: the action name string
    - ``attributes``: the action attributes dict
    - ``context``: the runtime context dict
    - ``tool``: alias for action (Fastify-style hook param name)
    - ``request``: the ActionRequest dataclass instance
    - ``decision``: the current Decision status string
    - ``rule_name``: the matched rule name
    - ``reason``: the decision reason
    - ``user``: the acting user id (from attributes)
    - ``tenant``: the tenant id (from attributes)
    - ``session``: the session id (from attributes)
    - ``phase``: the current hook phase (pre_receive, pre_validation, etc.)
    """

    _SENTINEL: object = object()

    def __init__(
        self,
        action: str | None = None,
        attributes: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        *,
        request: Any = None,
        decision: str | None = None,
        rule_name: str | None = None,
        reason: str | None = None,
        phase: str | None = None,
    ) -> None:
        super().__init__(evaluation_identifier="guardian")
        self._action = action
        self._attributes = attributes
        self._context = context
        self._request = request
        self._decision = decision
        self._rule_name = rule_name
        self._reason = reason
        self._phase = phase

    def resolve_default_by_name(self, param_name: str) -> Any:
        attrs = self._attributes or {}
        ctx = self._context or {}
        defaults: dict[str, Any] = {
            "action": self._action,
            "attributes": self._attributes,
            "context": self._context,
            "tool": self._action,  # Fastify-style alias
            "request": self._request,
            "decision": self._decision,
            "rule_name": self._rule_name,
            "reason": self._reason,
            "phase": self._phase,
            "user": attrs.get("user") or ctx.get("user"),
            "tenant": attrs.get("tenant") or ctx.get("tenant"),
            "session": attrs.get("session") or ctx.get("session"),
            "user_id": attrs.get("user_id") or ctx.get("user_id"),
            "tenant_id": attrs.get("tenant_id") or ctx.get("tenant_id"),
        }
        if param_name not in defaults:
            return _MISSING
        value = defaults[param_name]
        # Fall through on None so later strategies/defaults can still resolve.
        if value is None:
            return _MISSING
        return value
