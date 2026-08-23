"""Tests for runtime/composite_identity.py — dual-principal attribution."""

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError

import pytest

from runtime.composite_identity import (
    CompositeIdentity,
    CompositeIdentityRegistry,
    Principal,
    PrincipalRole,
)


def _make_identity(
    agent_id: str = "agent-1",
    human_id: str = "human-1",
    session_id: str = "sess-1",
    tenant_id: str = "tenant-1",
) -> CompositeIdentity:
    return CompositeIdentity(
        agent=Principal(PrincipalRole.AGENT, agent_id, "Agent One"),
        human=Principal(PrincipalRole.HUMAN, human_id, "Human One"),
        session_id=session_id,
        tenant_id=tenant_id,
    )


class TestPrincipalRole:
    def test_agent_value(self) -> None:
        assert PrincipalRole.AGENT.value == "agent"

    def test_human_value(self) -> None:
        assert PrincipalRole.HUMAN.value == "human"

    def test_is_str_enum(self) -> None:
        assert isinstance(PrincipalRole.AGENT, str)


class TestPrincipal:
    def test_default_display_name_empty(self) -> None:
        principal = Principal(PrincipalRole.AGENT, "a1")
        assert principal.display_name == ""

    def test_frozen(self) -> None:
        principal = Principal(PrincipalRole.AGENT, "a1", "Agent")
        with pytest.raises((FrozenInstanceError, AttributeError)):
            principal.principal_id = "x"  # type: ignore[misc]

    def test_equality(self) -> None:
        p1 = Principal(PrincipalRole.AGENT, "a1", "Agent")
        p2 = Principal(PrincipalRole.AGENT, "a1", "Agent")
        assert p1 == p2


class TestCompositeIdentityToDict:
    def test_contains_both_principals(self) -> None:
        identity = _make_identity()
        d = identity.to_dict()
        assert d["agent"]["role"] == "agent"
        assert d["agent"]["principal_id"] == "agent-1"
        assert d["human"]["role"] == "human"
        assert d["human"]["principal_id"] == "human-1"

    def test_contains_session_and_tenant(self) -> None:
        identity = _make_identity()
        d = identity.to_dict()
        assert d["session_id"] == "sess-1"
        assert d["tenant_id"] == "tenant-1"

    def test_display_names_preserved(self) -> None:
        identity = _make_identity()
        d = identity.to_dict()
        assert d["agent"]["display_name"] == "Agent One"
        assert d["human"]["display_name"] == "Human One"


class TestCompositeIdentitySignature:
    def test_deterministic_for_same_identity(self) -> None:
        id1 = _make_identity()
        id2 = _make_identity()
        assert id1.signature() == id2.signature()

    def test_unique_for_different_agent(self) -> None:
        id1 = _make_identity(agent_id="agent-1")
        id2 = _make_identity(agent_id="agent-2")
        assert id1.signature() != id2.signature()

    def test_unique_for_different_human(self) -> None:
        id1 = _make_identity(human_id="human-1")
        id2 = _make_identity(human_id="human-2")
        assert id1.signature() != id2.signature()

    def test_unique_for_different_session(self) -> None:
        id1 = _make_identity(session_id="sess-1")
        id2 = _make_identity(session_id="sess-2")
        assert id1.signature() != id2.signature()

    def test_signature_is_hex_sha256(self) -> None:
        sig = _make_identity().signature()
        assert len(sig) == 64
        int(sig, 16)  # valid hex


class TestRegistryRegisterResolve:
    def test_register_returns_signature(self) -> None:
        registry = CompositeIdentityRegistry()
        identity = _make_identity()
        sig = registry.register(identity)
        assert sig == identity.signature()

    def test_resolve_registered_identity(self) -> None:
        registry = CompositeIdentityRegistry()
        identity = _make_identity()
        sig = registry.register(identity)
        assert registry.resolve(sig) == identity

    def test_resolve_unknown_returns_none(self) -> None:
        registry = CompositeIdentityRegistry()
        assert registry.resolve("unknown") is None


class TestRegistryAttribute:
    def test_attribute_record_contains_both_principals(self) -> None:
        registry = CompositeIdentityRegistry()
        sig = registry.register(_make_identity())
        record = registry.attribute(sig, "run_command", {"cmd": "ls"})
        roles = [p["role"] for p in record["principals"]]
        assert "agent" in roles
        assert "human" in roles

    def test_attribute_record_contains_action_and_details(self) -> None:
        registry = CompositeIdentityRegistry()
        sig = registry.register(_make_identity())
        record = registry.attribute(sig, "run_command", {"cmd": "ls"})
        assert record["action"] == "run_command"
        assert record["details"] == {"cmd": "ls"}

    def test_attribute_unknown_signature_empty_principals(self) -> None:
        registry = CompositeIdentityRegistry()
        record = registry.attribute("unknown", "run_command", {})
        assert record["principals"] == []

    def test_attribute_record_contains_session_and_tenant(self) -> None:
        registry = CompositeIdentityRegistry()
        sig = registry.register(_make_identity())
        record = registry.attribute(sig, "run_command", {})
        assert record["session_id"] == "sess-1"
        assert record["tenant_id"] == "tenant-1"


class TestRegistryListClear:
    def test_list_empty_initially(self) -> None:
        registry = CompositeIdentityRegistry()
        assert registry.list_identities() == []

    def test_list_returns_registered(self) -> None:
        registry = CompositeIdentityRegistry()
        identity = _make_identity()
        registry.register(identity)
        assert registry.list_identities() == [identity]

    def test_clear_removes_all(self) -> None:
        registry = CompositeIdentityRegistry()
        sig = registry.register(_make_identity())
        registry.clear()
        assert registry.resolve(sig) is None
        assert registry.list_identities() == []

    def test_clear_on_empty_no_error(self) -> None:
        registry = CompositeIdentityRegistry()
        registry.clear()  # should not raise


class TestRegistryThreadSafety:
    def test_concurrent_registers_no_errors(self) -> None:
        registry = CompositeIdentityRegistry()
        errors: list[Exception] = []

        def worker(idx: int) -> None:
            try:
                for i in range(50):
                    registry.register(_make_identity(agent_id=f"a{idx}_{i}"))
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        assert len(registry.list_identities()) == 8 * 50

    def test_concurrent_register_and_clear(self) -> None:
        registry = CompositeIdentityRegistry()
        errors: list[Exception] = []

        def registrar() -> None:
            try:
                for i in range(50):
                    registry.register(_make_identity(agent_id=f"a{i}"))
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        def clearer() -> None:
            try:
                for _ in range(50):
                    registry.clear()
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=registrar), threading.Thread(target=clearer)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
