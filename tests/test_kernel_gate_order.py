"""Test that the kernel gate order matches the documented sequence.

Documented order (AGENTS.md): Probity -> Guardian -> Policy -> LoopDetector -> Budget -> Audit

The test wraps each gate's check method with a recorder that appends the
gate name to a list, then asserts the list matches the expected sequence.
All gates are stubbed to *pass* so the full pipeline runs to completion.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import pytest

EXPECTED_ORDER = ["Probity", "Guardian", "Policy", "LoopDetector", "Budget", "Audit"]


def _recorder(name: str, call_order: list[str], return_value: Any = None) -> Callable[..., Any]:
    """Return a callable that records *name* then returns *return_value*."""

    def _wrapper(*_args: Any, **_kwargs: Any) -> Any:
        call_order.append(name)
        return return_value

    return _wrapper


@pytest.mark.unit
def test_kernel_gate_order(kernel: object) -> None:
    """Assert gates fire in order: Probity -> Guardian -> Policy -> LoopDetector -> Budget -> Audit."""
    call_order: list[str] = []

    allow_decision: dict[str, Any] = {
        "decision": "allow",
        "rule": "test-allow",
        "description": "test",
        "approvers": [],
        "requires_approval": False,
    }
    budget_ok: dict[str, Any] = {"ok": True, "reason": None, "action": "allow"}

    with (
        patch.object(kernel.policy_mgr, "check_probity", _recorder("Probity", call_order)),  # type: ignore[attr-defined]
        patch.object(kernel.policy_mgr, "check_guardian", _recorder("Guardian", call_order, None)),  # type: ignore[attr-defined]
        patch.object(kernel.policy, "can", _recorder("Policy", call_order, allow_decision)),  # type: ignore[attr-defined]
        patch.object(kernel.loop_detector, "check_and_record", _recorder("LoopDetector", call_order, None)),  # type: ignore[attr-defined]
        patch.object(kernel.budget, "check", _recorder("Budget", call_order, budget_ok)),  # type: ignore[attr-defined]
        patch.object(kernel.budget, "save", lambda *_a, **_kw: None),  # type: ignore[attr-defined]
        patch.object(kernel.audit, "log", _recorder("Audit", call_order)),  # type: ignore[attr-defined]
    ):
        result = kernel.act("write", dry_run=False, tokens=0, cost=0.0)  # type: ignore[attr-defined]

    assert result["ok"], f"Action should succeed with all gates passing, got: {result}"
    assert call_order == EXPECTED_ORDER, (
        f"Gate order mismatch:\n  expected: {EXPECTED_ORDER}\n  got:      {call_order}"
    )
