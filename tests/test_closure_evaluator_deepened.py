"""Tests for deepened GuardianClosureEvaluator DI (more param names)."""
from __future__ import annotations

from typing import Any

from runtime.closure_evaluator import GuardianClosureEvaluator


def _eval(
    closure: Any,
    *,
    action: str | None = None,
    attributes: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    request: Any = None,
    decision: str | None = None,
    rule_name: str | None = None,
    reason: str | None = None,
    phase: str | None = None,
) -> Any:
    ev = GuardianClosureEvaluator(
        action=action,
        attributes=attributes,
        context=context,
        request=request,
        decision=decision,
        rule_name=rule_name,
        reason=reason,
        phase=phase,
    )
    return ev.evaluate(closure)


def test_resolves_action() -> None:
    assert _eval(lambda action: action, action="Write") == "Write"


def test_resolves_tool_alias() -> None:
    assert _eval(lambda tool: tool, action="Read") == "Read"


def test_resolves_attributes() -> None:
    assert _eval(lambda attributes: attributes, attributes={"path": "/x"}) == {"path": "/x"}


def test_resolves_context() -> None:
    assert _eval(lambda context: context, context={"k": "v"}) == {"k": "v"}


def test_resolves_request() -> None:
    req = object()
    assert _eval(lambda request: request, request=req) is req


def test_resolves_decision() -> None:
    assert _eval(lambda decision: decision, decision="allow") == "allow"


def test_resolves_rule_name() -> None:
    assert _eval(lambda rule_name: rule_name, rule_name="admin_only") == "admin_only"


def test_resolves_reason() -> None:
    assert _eval(lambda reason: reason, reason="no match") == "no match"


def test_resolves_phase() -> None:
    assert _eval(lambda phase: phase, phase="pre_validation") == "pre_validation"


def test_resolves_user_from_attributes() -> None:
    assert _eval(lambda user: user, attributes={"user": "alice"}) == "alice"


def test_resolves_tenant_from_context() -> None:
    assert _eval(lambda tenant: tenant, context={"tenant": "acme"}) == "acme"


def test_resolves_session_from_attributes() -> None:
    assert _eval(lambda session: session, attributes={"session": "s123"}) == "s123"


def test_resolves_user_id_from_attributes() -> None:
    assert _eval(lambda user_id: user_id, attributes={"user_id": 42}) == 42


def test_resolves_tenant_id_from_context() -> None:
    assert _eval(lambda tenant_id: tenant_id, context={"tenant_id": 7}) == 7


def test_named_injection_overrides_default() -> None:
    ev = GuardianClosureEvaluator(action="default")
    result = ev.evaluate(lambda action: action, named_injections={"action": "override"})
    assert result == "override"


def test_none_value_when_not_provided() -> None:
    # user not in attributes or context -> resolves to None via default value
    assert _eval(lambda user=None: user) is None
