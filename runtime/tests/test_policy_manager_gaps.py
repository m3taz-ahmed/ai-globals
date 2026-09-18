"""Gap tests for runtime/managers/policy_manager.py."""
from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from runtime.enums import ActionResultStatus
from runtime.managers.policy_manager import PolicyManager


def _mgr(tmp_path, **over) -> PolicyManager:
    m = PolicyManager.__new__(PolicyManager)
    m.root = tmp_path
    m.project_root = tmp_path
    m.audit = MagicMock()
    m.budget = MagicMock()
    m.approval_cache = MagicMock()
    m.approval_service = over.get("approval_service")
    m.preloop = MagicMock()
    m._probity_violations_total = MagicMock()
    m.probity = MagicMock()
    return m


class TestBuildGuardianProbity:
    def _build(self, tmp_path, guardian_yaml=None, probity_yaml=None):
        pol = tmp_path / "runtime" / "policies"
        pol.mkdir(parents=True)
        if guardian_yaml is not None:
            (pol / "guardian.yaml").write_text(guardian_yaml)
        if probity_yaml is not None:
            (pol / "probity.yaml").write_text(probity_yaml)
        m = PolicyManager.__new__(PolicyManager)
        m.root = tmp_path
        m.project_root = tmp_path
        return m

    def test_guardian_rules_not_list(self, tmp_path):
        m = self._build(tmp_path, guardian_yaml="rules: notalist\n")
        g = m._build_guardian()
        assert g is not None

    def test_guardian_corrupt_fails_closed(self, tmp_path):
        from runtime.guardian import DecisionStatus
        m = self._build(tmp_path, guardian_yaml="{unclosed: [")
        g = m._build_guardian()
        assert g.config.default_decision == DecisionStatus.DENY

    def test_probity_rules_not_list(self, tmp_path):
        m = self._build(tmp_path, probity_yaml="rules: 42\n")
        p = m._build_probity()
        assert p is not None

    def test_probity_corrupt_yaml(self, tmp_path):
        m = self._build(tmp_path, probity_yaml="{bad: [")
        p = m._build_probity()
        assert p is not None

    def test_probity_rules_loaded(self, tmp_path):
        m = self._build(tmp_path, probity_yaml="rules:\n  - name: r1\n")
        p = m._build_probity()
        assert p is not None


class TestCheckProbity:
    def test_history_not_list(self, tmp_path):
        m = _mgr(tmp_path)
        m.check_probity("write", {"path": "f.py", "history": "notalist"})
        ev = m.probity.check.call_args[0][0]
        assert ev["history"] == []

    def test_write_and_exec_events(self, tmp_path):
        m = _mgr(tmp_path)
        m.check_probity("write", {"path": "f.py", "content": "c", "history": []})
        m.check_probity("exec", {"command": "ls", "history": []})
        calls = [c[0][0] for c in m.probity.check.call_args_list]
        assert calls[0]["path"] == "f.py" and calls[0]["content"] == "c"
        assert calls[1]["command"] == "ls"

    def test_probity_exception_raises_and_counts(self, tmp_path):
        m = _mgr(tmp_path)
        exc = ValueError("viol")
        cast(Any, exc).rule_name = "r1"
        m.probity.check.side_effect = exc
        with pytest.raises(ValueError):
            m.check_probity("write", {"path": "f"})
        m._probity_violations_total.labels.assert_called_once_with(rule="r1")

    def test_explicit_probity_arg(self, tmp_path):
        m = _mgr(tmp_path)
        custom = MagicMock()
        m.check_probity("read", {}, probity=custom)
        custom.check.assert_called_once()


class TestResolveApproval:
    def test_approved_caches(self, tmp_path):
        m = _mgr(tmp_path)
        assert m.resolve_approval({"approved": True}, dry_run=False) is True
        m.approval_cache.approve.assert_called_once()

    def test_approved_dry_run_skips_cache(self, tmp_path):
        m = _mgr(tmp_path)
        assert m.resolve_approval({"approved": True}, dry_run=True) is True
        m.approval_cache.approve.assert_not_called()

    def test_cache_hit(self, tmp_path):
        m = _mgr(tmp_path)
        m.approval_cache.is_approved.return_value = True
        data = {"type": "t"}
        assert m.resolve_approval(data, False) is True
        assert data["approved"] is True

    def test_approval_service_creates_request(self, tmp_path):
        svc = MagicMock()
        svc.create_request.return_value = MagicMock(id="req1")
        m = _mgr(tmp_path, approval_service=svc)
        m.approval_cache.is_approved.return_value = False
        assert m.resolve_approval({"type": "deploy"}, False) is False
        svc.create_request.assert_called_once()

    def test_no_service(self, tmp_path):
        m = _mgr(tmp_path)
        m.approval_cache.is_approved.return_value = False
        assert m.resolve_approval({"type": "t"}, False) is False


class TestAuditBudget:
    def test_dry_run_skips(self, tmp_path):
        m = _mgr(tmp_path)
        m.audit_budget({"type": "t"}, {}, {}, {"ok": True}, dry_run=True)
        m.budget.save.assert_not_called()
        m.audit.log.assert_not_called()

    def test_budget_blocked_logs(self, tmp_path):
        m = _mgr(tmp_path)
        m.audit_budget({"type": "t"}, {}, {}, {"ok": False, "reason": "over"}, dry_run=False)
        m.audit.log.assert_called_once()
        assert "budget.blocked" in m.audit.log.call_args[0][0]


class TestFinalizeAction:
    def test_blocked(self, tmp_path):
        m = _mgr(tmp_path)
        tel = MagicMock()
        out = m.finalize_action({"type": "t"}, {}, {}, {"ok": False, "reason": "cap"}, False, tel)
        assert out["ok"] is False and out["error"] == "cap"
        tel.record.assert_called_once()
        assert tel.record.call_args[1]["status"] == ActionResultStatus.BUDGET_BLOCKED.value

    def test_allowed(self, tmp_path):
        m = _mgr(tmp_path)
        out = m.finalize_action({"type": "t"}, {}, {}, {"ok": True}, True, MagicMock())
        assert out["ok"] is True


class TestRecordPreloop:
    def test_non_str_tag(self, tmp_path):
        m = _mgr(tmp_path)
        m.record_preloop("act", {"ok": True}, {"decision": 123})
        outcome = m.preloop.record.call_args[0][0]
        assert outcome.tags == ["unknown"]
        assert outcome.reward == 1.0

    def test_not_ok_result(self, tmp_path):
        m = _mgr(tmp_path)
        m.record_preloop("act", {"ok": False}, {"decision": "deny"})
        outcome = m.preloop.record.call_args[0][0]
        assert outcome.reward == 0.0 and outcome.tags == ["deny"]
