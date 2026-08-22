"""Tests for the Resource → Permission → Policy decomposition (from Keycloak).

Covers ProtectedResource registration, Permission binding, evaluate_access
with AND/OR/DENY_OVERRIDE aggregate logic, negative permission logic, and
backward compatibility with PolicyDecisionPoint.
"""

from __future__ import annotations

from typing import Literal

from runtime.authorization import (
    AuthorizationTuple,
    Permission,
    PolicyDecisionPoint,
    ProtectedResource,
    ResourceRegistry,
    _aggregate_decisions,
    _invert_decision,
)


def _make_tuple(operation_id: str = "read") -> AuthorizationTuple:
    return AuthorizationTuple(
        subject_id="u1",
        tenant_id="t1",
        workload_id="w1",
        operation_id=operation_id,
        target_id="doc1",
        delegated_scope=(operation_id,),
    )


# ---------------------------------------------------------------------------
# ProtectedResource registration
# ---------------------------------------------------------------------------


class TestProtectedResource:
    def test_construction_defaults(self) -> None:
        r = ProtectedResource(
            resource_id="res-1",
            resource_type="mcp_tool",
            name="git_commit",
        )
        assert r.resource_id == "res-1"
        assert r.resource_type == "mcp_tool"
        assert r.name == "git_commit"
        assert r.description == ""

    def test_construction_with_description(self) -> None:
        r = ProtectedResource(
            resource_id="res-2",
            resource_type="file",
            name="/etc/passwd",
            description="System password file",
        )
        assert r.description == "System password file"

    def test_register_and_lookup(self) -> None:
        registry = ResourceRegistry()
        r = ProtectedResource("res-1", "action", "deploy")
        registry.register_resource(r)
        assert registry.get_resource("res-1") is r

    def test_lookup_missing_returns_none(self) -> None:
        registry = ResourceRegistry()
        assert registry.get_resource("nonexistent") is None


# ---------------------------------------------------------------------------
# Permission binding
# ---------------------------------------------------------------------------


class TestPermissionBinding:
    def test_permission_defaults(self) -> None:
        p = Permission(permission_id="perm-1", resource_id="res-1")
        assert p.policy_ids == []
        assert p.logic == "positive"

    def test_bind_permission(self) -> None:
        registry = ResourceRegistry()
        registry.register_resource(ProtectedResource("res-1", "action", "deploy"))
        p = Permission(
            permission_id="perm-1",
            resource_id="res-1",
            policy_ids=["pol-a"],
        )
        registry.bind_permission(p)
        perms = registry.list_permissions_for_resource("res-1")
        assert len(perms) == 1
        assert perms[0].permission_id == "perm-1"

    def test_multiple_permissions_for_resource(self) -> None:
        registry = ResourceRegistry()
        registry.register_resource(ProtectedResource("res-1", "action", "deploy"))
        registry.bind_permission(Permission("perm-a", "res-1", ["pol-1"]))
        registry.bind_permission(Permission("perm-b", "res-1", ["pol-2"]))
        perms = registry.list_permissions_for_resource("res-1")
        assert len(perms) == 2

    def test_register_policy_evaluator(self) -> None:
        registry = ResourceRegistry()

        def allow_all(tup: AuthorizationTuple) -> Literal["allow", "deny", "ask"]:
            return "allow"

        registry.register_policy("pol-allow", allow_all)
        # Verify it's used via evaluate_access below.


# ---------------------------------------------------------------------------
# evaluate_access with AND/OR/DENY_OVERRIDE logic
# ---------------------------------------------------------------------------


class TestEvaluateAccessAggregateLogic:
    def test_and_all_allow_grants(self) -> None:
        registry = ResourceRegistry()
        registry.register_resource(ProtectedResource("res-1", "action", "deploy"))
        registry.register_policy("pol-a", lambda tup: "allow")
        registry.register_policy("pol-b", lambda tup: "allow")
        registry.bind_permission(Permission("perm-1", "res-1", ["pol-a", "pol-b"]))
        decision = registry.evaluate_access("res-1", _make_tuple(), logic="AND")
        assert decision.decision == "allow"

    def test_and_any_deny_blocks(self) -> None:
        registry = ResourceRegistry()
        registry.register_resource(ProtectedResource("res-1", "action", "deploy"))
        registry.register_policy("pol-a", lambda tup: "allow")
        registry.register_policy("pol-b", lambda tup: "deny")
        registry.bind_permission(Permission("perm-1", "res-1", ["pol-a", "pol-b"]))
        decision = registry.evaluate_access("res-1", _make_tuple(), logic="AND")
        assert decision.decision == "deny"

    def test_or_any_allow_grants(self) -> None:
        registry = ResourceRegistry()
        registry.register_resource(ProtectedResource("res-1", "action", "deploy"))
        registry.register_policy("pol-a", lambda tup: "deny")
        registry.register_policy("pol-b", lambda tup: "allow")
        registry.bind_permission(Permission("perm-1", "res-1", ["pol-a", "pol-b"]))
        decision = registry.evaluate_access("res-1", _make_tuple(), logic="OR")
        assert decision.decision == "allow"

    def test_or_all_deny_blocks(self) -> None:
        registry = ResourceRegistry()
        registry.register_resource(ProtectedResource("res-1", "action", "deploy"))
        registry.register_policy("pol-a", lambda tup: "deny")
        registry.register_policy("pol-b", lambda tup: "deny")
        registry.bind_permission(Permission("perm-1", "res-1", ["pol-a", "pol-b"]))
        decision = registry.evaluate_access("res-1", _make_tuple(), logic="OR")
        assert decision.decision == "deny"

    def test_deny_override_blocks_on_any_deny(self) -> None:
        registry = ResourceRegistry()
        registry.register_resource(ProtectedResource("res-1", "action", "deploy"))
        registry.register_policy("pol-a", lambda tup: "allow")
        registry.register_policy("pol-b", lambda tup: "deny")
        registry.bind_permission(Permission("perm-1", "res-1", ["pol-a", "pol-b"]))
        decision = registry.evaluate_access("res-1", _make_tuple(), logic="DENY_OVERRIDE")
        assert decision.decision == "deny"

    def test_deny_override_grants_when_no_deny(self) -> None:
        registry = ResourceRegistry()
        registry.register_resource(ProtectedResource("res-1", "action", "deploy"))
        registry.register_policy("pol-a", lambda tup: "allow")
        registry.register_policy("pol-b", lambda tup: "ask")
        registry.bind_permission(Permission("perm-1", "res-1", ["pol-a", "pol-b"]))
        decision = registry.evaluate_access("res-1", _make_tuple(), logic="DENY_OVERRIDE")
        assert decision.decision == "allow"


# ---------------------------------------------------------------------------
# Negative permission logic
# ---------------------------------------------------------------------------


class TestNegativePermissionLogic:
    def test_negative_logic_inverts_allow_to_deny(self) -> None:
        registry = ResourceRegistry()
        registry.register_resource(ProtectedResource("res-1", "action", "deploy"))
        registry.register_policy("pol-a", lambda tup: "allow")
        registry.bind_permission(
            Permission("perm-1", "res-1", ["pol-a"], logic="negative")
        )
        decision = registry.evaluate_access("res-1", _make_tuple(), logic="AND")
        assert decision.decision == "deny"

    def test_negative_logic_inverts_deny_to_allow(self) -> None:
        registry = ResourceRegistry()
        registry.register_resource(ProtectedResource("res-1", "action", "deploy"))
        registry.register_policy("pol-a", lambda tup: "deny")
        registry.bind_permission(
            Permission("perm-1", "res-1", ["pol-a"], logic="negative")
        )
        decision = registry.evaluate_access("res-1", _make_tuple(), logic="AND")
        assert decision.decision == "allow"


# ---------------------------------------------------------------------------
# Edge cases: missing resource, no permissions
# ---------------------------------------------------------------------------


class TestEvaluateAccessEdgeCases:
    def test_missing_resource_denies(self) -> None:
        registry = ResourceRegistry()
        decision = registry.evaluate_access("nonexistent", _make_tuple())
        assert decision.decision == "deny"
        assert decision.reason == "resource_not_found"

    def test_no_permissions_falls_back_to_pdp(self) -> None:
        pdp = PolicyDecisionPoint()
        registry = ResourceRegistry(pdp=pdp)
        registry.register_resource(ProtectedResource("res-1", "action", "read"))
        # No permissions bound → should delegate to PDP.
        decision = registry.evaluate_access("res-1", _make_tuple("read"))
        assert decision.decision == "allow"

    def test_no_permissions_no_pdp_denies(self) -> None:
        registry = ResourceRegistry()
        registry.register_resource(ProtectedResource("res-1", "action", "read"))
        decision = registry.evaluate_access("res-1", _make_tuple("read"))
        assert decision.decision == "deny"
        assert decision.reason == "no_permissions_bound"

    def test_unregistered_policy_falls_back_to_pdp(self) -> None:
        pdp = PolicyDecisionPoint()
        registry = ResourceRegistry(pdp=pdp)
        registry.register_resource(ProtectedResource("res-1", "action", "read"))
        # Policy ID not registered → falls back to PDP.
        registry.bind_permission(Permission("perm-1", "res-1", ["unregistered-pol"]))
        decision = registry.evaluate_access("res-1", _make_tuple("read"))
        assert decision.decision == "allow"


# ---------------------------------------------------------------------------
# Backward compatibility with PolicyDecisionPoint
# ---------------------------------------------------------------------------


class TestBackwardCompatPDP:
    def test_pdp_still_decides_consequential(self) -> None:
        pdp = PolicyDecisionPoint()
        tup = AuthorizationTuple(
            subject_id="u1",
            tenant_id="t1",
            workload_id="w1",
            operation_id="deploy",
            target_id="prod",
            delegated_scope=("deploy",),
        )
        decision = pdp.decide(tup)
        assert decision.decision == "ask"

    def test_pdp_still_decides_non_consequential(self) -> None:
        pdp = PolicyDecisionPoint()
        decision = pdp.decide(_make_tuple("read"))
        assert decision.decision == "allow"

    def test_resource_registry_with_pdp_preserves_pdp_behavior(self) -> None:
        pdp = PolicyDecisionPoint()
        registry = ResourceRegistry(pdp=pdp)
        # No resources registered at all — PDP is still usable independently.
        assert registry._pdp is pdp


# ---------------------------------------------------------------------------
# Aggregate helper functions
# ---------------------------------------------------------------------------


class TestAggregateHelpers:
    def test_aggregate_and_empty_denies(self) -> None:
        assert _aggregate_decisions([], "AND") == "deny"

    def test_aggregate_or_empty_denies(self) -> None:
        assert _aggregate_decisions([], "OR") == "deny"

    def test_aggregate_deny_override_empty_denies(self) -> None:
        assert _aggregate_decisions([], "DENY_OVERRIDE") == "deny"

    def test_invert_allow_to_deny(self) -> None:
        assert _invert_decision("allow") == "deny"

    def test_invert_deny_to_allow(self) -> None:
        assert _invert_decision("deny") == "allow"

    def test_invert_ask_stays_ask(self) -> None:
        assert _invert_decision("ask") == "ask"

    def test_and_with_ask_and_no_deny_returns_ask(self) -> None:
        assert _aggregate_decisions(["allow", "ask"], "AND") == "ask"

    def test_or_with_ask_and_no_allow_returns_ask(self) -> None:
        assert _aggregate_decisions(["ask", "deny"], "OR") == "ask"
