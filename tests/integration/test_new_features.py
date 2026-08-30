#!/usr/bin/env python3
"""Integration tests for the 15 repository-study features."""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.astryx import AstryxLinter
from runtime.guardian import Guardian
from runtime.kernel import Kernel
from runtime.preloop import FeedbackLoop, Outcome
from runtime.probity import Guardrails, GuardrailViolationError
from runtime.sovereign import AgentCapabilities, Capability

# TEST-10: integration tests — excluded from FAST tier.
pytestmark = pytest.mark.integration


@pytest.fixture
def kernel(tmp_path: Path) -> Kernel:
    """Create a Kernel with a temporary project root."""
    root = Path(__file__).resolve().parents[2]
    return Kernel(root, tmp_path)


def test_kernel_loads_new_governance_modules(kernel: Kernel) -> None:
    """The kernel initializes the new governance, metrics, tracing, and preloop modules."""
    status = kernel.status()
    assert "metrics" in status
    assert "guardian_rules" in status
    assert "capabilities" in status
    assert isinstance(kernel.governance, object)
    assert isinstance(kernel.preloop, object)


def test_guardian_and_metrics_count(kernel: Kernel) -> None:
    """Guardian denials increment the metrics counter."""
    kernel.guardian = Guardian(
        [
            {
                "name": "block-test",
                "tool": "blocked",
                "condition": {"eq": ["attributes.action.type", "blocked"]},
                "decision": "deny",
            }
        ]
    )
    result = kernel.act("blocked")
    assert result["ok"] is False
    assert "Guardian denied" in result["error"]
    samples = {s.name: s.value for s in kernel.metrics.collect()}
    assert samples.get("aizee_guardian_denials_total", 0) >= 1


def test_astryx_lint_rejects_eval() -> None:
    """Astryx flags eval in Python code."""
    linter = AstryxLinter()
    findings = linter.lint_text("eval('1+1')")
    assert any(f.rule == "no-eval" for f in findings)


def test_sovereign_capability_check() -> None:
    """Sovereign capability model grants and requires capabilities."""
    caps = AgentCapabilities()
    caps.grant(Capability("file.write"))
    caps.require(Capability("file.write", "project"))
    with pytest.raises(PermissionError):
        caps.require(Capability("shell.exec"))


def test_preloop_feedback_ranking() -> None:
    """Preloop feedback loop ranks actions by success."""
    fb = FeedbackLoop()
    for _ in range(3):
        fb.record(Outcome("edit", True, 1.0))
    fb.record(Outcome("edit", False, 0.0))
    fb.record(Outcome("write", True, 0.5))
    assert fb.best_action(["edit", "write"]) == "edit"


def test_probity_guardrails() -> None:
    """Probity blocks forbidden commands."""
    g = Guardrails(
        {"rules": [{"kind": "forbidCommandPattern", "name": "no-rm", "pattern": "rm -rf /", "message": "Forbidden"}]}
    )
    with pytest.raises(GuardrailViolationError):
        g.check({"type": "command", "command": "rm -rf /", "history": []})
