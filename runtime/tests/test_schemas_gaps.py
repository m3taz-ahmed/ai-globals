"""Gap coverage: runtime/schemas.py validators, PaginatedResult, GateVerdict."""

from __future__ import annotations

import pytest

from runtime.schemas import (
    BudgetSchema,
    GateDecision,
    GateVerdict,
    PaginatedResult,
    PolicyFileSchema,
)


class TestPaginatedResult:
    def test_to_dict_minimal(self) -> None:
        p = PaginatedResult(items=[1, 2])
        assert p.to_dict() == {"items": [1, 2]}
        assert p.has_more is False

    def test_to_dict_full(self) -> None:
        p = PaginatedResult(items=[1], next_token="tok", total=42)
        d = p.to_dict()
        assert d == {"items": [1], "next_token": "tok", "total": 42}
        assert p.has_more is True


class TestGateVerdict:
    def test_decision_coerced_from_str(self) -> None:
        v = GateVerdict(gate="g", decision="allow")
        assert v.decision is GateDecision.ALLOW
        assert v.is_allowed and not v.is_blocked

    def test_reason_type_enforced(self) -> None:
        with pytest.raises(TypeError):
            GateVerdict(gate="g", decision="allow", reason=5)  # type: ignore[arg-type]

    def test_metadata_type_enforced(self) -> None:
        with pytest.raises(TypeError):
            GateVerdict(gate="g", decision="allow", metadata="x")  # type: ignore[arg-type]

    def test_redact_requires_spans(self) -> None:
        with pytest.raises(ValueError, match="spans"):
            GateVerdict(gate="g", decision=GateDecision.REDACT)

    def test_redact_factory(self) -> None:
        v = GateVerdict.redact("g", "secret", spans=((0, 3, "key"),))
        assert v.decision is GateDecision.REDACT
        assert v.spans == ((0, 3, "key"),)

    def test_factories_and_dict(self) -> None:
        v = GateVerdict.require_approval("gate", "need human", score=3)
        d = v.to_dict()
        assert d["decision"] == "require_approval" and d["metadata"] == {"score": 3}
        assert GateVerdict.block("g").is_blocked
        assert GateVerdict.allow("g").is_allowed


class TestSchemaValidators:
    def test_budget_period_invalid(self) -> None:
        with pytest.raises(Exception):
            BudgetSchema(period="yearly")

    def test_budget_on_exceed_invalid(self) -> None:
        with pytest.raises(Exception):
            BudgetSchema(on_exceed="explode")

    def test_policy_default_action_invalid(self) -> None:
        with pytest.raises(Exception):
            PolicyFileSchema(default_action="yolo")
