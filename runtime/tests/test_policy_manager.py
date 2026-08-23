"""Tests for runtime/managers/policy_manager.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from runtime.approval_cache import ApprovalCache
from runtime.audit import AuditLogger
from runtime.budget import BudgetManager
from runtime.guardian import DecisionStatus, Guardian
from runtime.managers.policy_manager import PolicyManager
from runtime.metrics import Counter
from runtime.preloop import FeedbackLoop
from runtime.probity import GuardrailViolationError


def _setup_roots(tmp_path: Path) -> tuple[Path, Path]:
    """Create OS root and project root with policy dirs."""
    os_root = tmp_path / "os"
    project_root = tmp_path / "project"
    for sub in ("runtime/policies", "state"):
        (os_root / sub).mkdir(parents=True, exist_ok=True)
        (project_root / sub).mkdir(parents=True, exist_ok=True)
    (os_root / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    return os_root, project_root


def _make_manager(os_root: Path, project_root: Path) -> PolicyManager:
    audit = AuditLogger(project_root)
    budget = BudgetManager(project_root)
    approval_cache = ApprovalCache()
    preloop = FeedbackLoop()
    actions_total = Counter("actions", "test", ("action", "decision"))
    guardian_denials = Counter("guardian", "test", ("rule",))
    probity_violations = Counter("probity", "test", ("rule",))
    return PolicyManager(
        os_root, project_root, audit, budget, approval_cache, preloop,
        actions_total, guardian_denials, probity_violations,
    )


class TestBuildGuardian:
    def test_guardian_from_yaml(self, tmp_path: Path) -> None:
        """Cover line 51: Guardian loaded from guardian.yaml."""
        os_root, project_root = _setup_roots(tmp_path)
        guardian_yaml = project_root / "runtime/policies/guardian.yaml"
        guardian_yaml.write_text(
            "default_decision: allow\nrules:\n"
            "  - name: deny-rm\n    when:\n"
            "      all:\n"
            "        - key: args.command\n          op: contains\n          value: 'rm -rf'\n"
            "    decision: deny\n    message: No rm -rf\n",
            encoding="utf-8",
        )
        mgr = _make_manager(os_root, project_root)
        assert isinstance(mgr.guardian, Guardian)
        assert len(mgr.guardian.rules) > 0


class TestBuildProbity:
    def test_probity_from_yaml(self, tmp_path: Path) -> None:
        """Cover lines 57-60: Guardrails loaded from probity.yaml."""
        os_root, project_root = _setup_roots(tmp_path)
        probity_yaml = project_root / "runtime/policies/probity.yaml"
        probity_yaml.write_text(
            "rules:\n"
            "  - kind: forbidCommandPattern\n    name: no-rm\n"
            "    pattern: 'rm -rf'\n    message: Forbidden\n",
            encoding="utf-8",
        )
        mgr = _make_manager(os_root, project_root)
        assert len(mgr.probity.rules) > 0


class TestCheckGuardian:
    def test_guardian_exception_fails_closed(self, tmp_path: Path) -> None:
        """Cover lines 85-96: exception in guardian.authorize denies (fail-closed)."""
        os_root, project_root = _setup_roots(tmp_path)
        mgr = _make_manager(os_root, project_root)
        # Pass a guardian that raises on authorize
        bad_guardian = MagicMock()
        bad_guardian.authorize.side_effect = RuntimeError("boom")
        result = mgr.check_guardian("write", {"type": "write"}, guardian=bad_guardian)
        assert result is not None
        assert result["ok"] is False
        assert result["decision"]["rule"] == "guardian_error"

    def test_guardian_require_approval(self, tmp_path: Path) -> None:
        """Cover line 95: guardian REQUIRE_APPROVAL returns error response."""
        os_root, project_root = _setup_roots(tmp_path)
        mgr = _make_manager(os_root, project_root)
        mock_guardian = MagicMock()
        mock_decision = MagicMock()
        mock_decision.status = DecisionStatus.REQUIRE_APPROVAL
        mock_decision.rule_name = "approval-rule"
        mock_decision.reason = "needs review"
        mock_guardian.authorize.return_value = mock_decision
        result = mgr.check_guardian("write", {"type": "write"}, guardian=mock_guardian)
        assert result is not None
        assert result["ok"] is False
        assert result["requires_approval"] is True


class TestCheckProbity:
    def test_probity_command_event(self, tmp_path: Path) -> None:
        """Cover line 112: exec/command/shell action sets event['command']."""
        os_root, project_root = _setup_roots(tmp_path)
        probity_yaml = project_root / "runtime/policies/probity.yaml"
        probity_yaml.write_text(
            "rules:\n"
            "  - kind: forbidCommandPattern\n    name: no-rm\n"
            "    pattern: 'rm -rf'\n    message: Forbidden\n",
            encoding="utf-8",
        )
        mgr = _make_manager(os_root, project_root)
        with pytest.raises(Exception):
            mgr.check_probity("command", {"command": "rm -rf /"}, mgr.probity)

    def test_probity_violation_reraises_and_increments(self, tmp_path: Path) -> None:
        """Cover lines 116-119: probity violation increments counter and re-raises."""
        os_root, project_root = _setup_roots(tmp_path)
        mgr = _make_manager(os_root, project_root)
        # Create a probity that always raises
        bad_probity = MagicMock()
        bad_probity.check.side_effect = GuardrailViolationError("test-rule", "violated")
        with pytest.raises(GuardrailViolationError):
            mgr.check_probity("write", {"path": "x", "content": "y"}, bad_probity)


class TestBuildBudgetKwargs:
    def test_rollout_id_in_budget_kwargs(self, tmp_path: Path) -> None:
        """Cover line 184: rollout_id is passed through to budget kwargs."""
        os_root, project_root = _setup_roots(tmp_path)
        mgr = _make_manager(os_root, project_root)
        kwargs = mgr.build_budget_kwargs({"rollout_id": "r-123"})
        assert kwargs["rollout_id"] == "r-123"

    def test_token_weight_in_budget_kwargs(self, tmp_path: Path) -> None:
        """Cover line 186: token_weight is passed through."""
        os_root, project_root = _setup_roots(tmp_path)
        mgr = _make_manager(os_root, project_root)
        kwargs = mgr.build_budget_kwargs({"token_weight": 2.5})
        assert kwargs["token_weight"] == 2.5

    def test_input_output_tokens_in_budget_kwargs(self, tmp_path: Path) -> None:
        """Cover lines 188-189: input_tokens and output_tokens are passed through."""
        os_root, project_root = _setup_roots(tmp_path)
        mgr = _make_manager(os_root, project_root)
        kwargs = mgr.build_budget_kwargs({"input_tokens": 100, "output_tokens": 50})
        assert kwargs["input_tokens"] == 100
        assert kwargs["output_tokens"] == 50

    def test_session_id_in_budget_kwargs(self, tmp_path: Path) -> None:
        """Cover session_id being added to budget kwargs."""
        os_root, project_root = _setup_roots(tmp_path)
        mgr = _make_manager(os_root, project_root)
        kwargs = mgr.build_budget_kwargs({}, session_id="sess-123")
        assert kwargs["session_id"] == "sess-123"
