"""Tests for kernel strict-mode (H3), truthful status() (H1), signer wiring
(P1.2), and the budget quarantine flag (H4)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.budget import BudgetManager
from runtime.kernel import CONSTRUCTED_ONLY_SERVICES, ORPHAN_MODULES, Kernel, _security_strict


def _kernel(tmp_path: Path) -> Kernel:
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    (tmp_path / "workflows/test.md").write_text("[WORKFLOW] test\n[RULES]\n1. [REQ] Step one.\n")
    return Kernel(tmp_path)


class TestSecurityStrict:
    def test_env_toggle(self, monkeypatch) -> None:
        monkeypatch.setenv("AIZEE_SECURITY_STRICT", "1")
        assert _security_strict() is True
        monkeypatch.setenv("AIZEE_SECURITY_STRICT", "0")
        assert _security_strict() is False
        monkeypatch.delenv("AIZEE_SECURITY_STRICT")
        assert _security_strict() is False

    def test_taint_failure_fatal_when_strict(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("AIZEE_SECURITY_STRICT", "1")
        with patch("runtime.taint.get_default_tracker", side_effect=RuntimeError("taint boom")):
            with pytest.raises(RuntimeError, match="taint boom"):
                _kernel(tmp_path)

    def test_taint_failure_warns_when_lenient(self, tmp_path, monkeypatch) -> None:
        monkeypatch.delenv("AIZEE_SECURITY_STRICT", raising=False)
        with patch("runtime.taint.get_default_tracker", side_effect=RuntimeError("taint boom")):
            k = _kernel(tmp_path)
        assert not hasattr(k, "taint_tracker")
        assert "taint_tracker" in k.status()["disabled_defenses"]

    def test_prompt_guardrail_failure_fatal_when_strict(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("AIZEE_SECURITY_STRICT", "1")
        monkeypatch.setitem(sys.modules, "runtime.guardrails.prompt_injection", None)
        with pytest.raises(ImportError):
            _kernel(tmp_path)

    def test_prompt_guardrail_failure_warns_when_lenient(self, tmp_path, monkeypatch) -> None:
        monkeypatch.delenv("AIZEE_SECURITY_STRICT", raising=False)
        monkeypatch.setitem(sys.modules, "runtime.guardrails.prompt_injection", None)
        k = _kernel(tmp_path)
        assert "prompt_injection_guardrail" in k.status()["disabled_defenses"]

    def test_injection_stack_failure_fatal_when_strict(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("AIZEE_SECURITY_STRICT", "1")
        with patch("runtime.injection_detector.InjectionDetector", side_effect=RuntimeError("inj boom")):
            with pytest.raises(RuntimeError, match="inj boom"):
                _kernel(tmp_path)

    def test_injection_stack_failure_warns_when_lenient(self, tmp_path, monkeypatch) -> None:
        monkeypatch.delenv("AIZEE_SECURITY_STRICT", raising=False)
        with patch("runtime.injection_detector.InjectionDetector", side_effect=RuntimeError("inj boom")):
            k = _kernel(tmp_path)
        assert not hasattr(k, "injection_detector")
        assert "injection_stack" in k.status()["disabled_defenses"]

    def test_design_stack_failure_fatal_when_strict(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("AIZEE_SECURITY_STRICT", "1")
        with patch("runtime.design_library.DesignLibrary", side_effect=RuntimeError("design boom")):
            with pytest.raises(RuntimeError, match="design boom"):
                _kernel(tmp_path)

    def test_design_stack_failure_warns_when_lenient(self, tmp_path, monkeypatch) -> None:
        monkeypatch.delenv("AIZEE_SECURITY_STRICT", raising=False)
        with patch("runtime.design_library.DesignLibrary", side_effect=RuntimeError("design boom")):
            k = _kernel(tmp_path)
        assert not hasattr(k, "design_library")
        assert "design_stack" in k.status()["disabled_defenses"]

    def test_clean_kernel_reports_no_disabled_defenses(self, tmp_path) -> None:
        assert _kernel(tmp_path).status()["disabled_defenses"] == []


class TestTruthfulStatus:
    def test_constructed_labels(self, tmp_path) -> None:
        status = _kernel(tmp_path).status()
        for key in (
            "mcp_auditor", "model_router", "fairness_detector",
            "hallucination_detector", "stale_api_detector",
            "laravel_policy_linter", "filament_access_auditor",
            "db_migration_safety", "ui_a11y_checker", "blade_template_linter",
        ):
            assert status[key] == "constructed", key

    def test_cli_wired_label(self, tmp_path) -> None:
        assert _kernel(tmp_path).status()["policy_linter"] == "cli-wired"

    def test_constructed_only_list(self, tmp_path) -> None:
        listed = set(_kernel(tmp_path).status()["constructed_only_services"])
        assert listed == set(CONSTRUCTED_ONLY_SERVICES)
        assert "mcp_auditor" in listed
        # Wired services must not be listed as constructed-only.
        assert "audit_signer" not in listed and "policy_linter" not in listed

    def test_budget_quarantine_flag_in_status(self, tmp_path) -> None:
        assert _kernel(tmp_path).status()["budget_state_quarantined"] is False

    def test_orphan_modules_exist(self) -> None:
        root = Path(__file__).resolve().parents[2]
        for name in ORPHAN_MODULES:
            assert (root / "runtime" / f"{name}.py").exists(), name


class TestSignerWiring:
    def test_audit_logger_has_signer(self, tmp_path) -> None:
        k = _kernel(tmp_path)
        assert k.audit.signer is k.audit_signer

    def test_kernel_audit_entries_are_signed(self, tmp_path) -> None:
        k = _kernel(tmp_path)
        k.act("Read")
        res = k.audit.verify_chain()
        assert res["valid"] and res["signatures_checked"] >= 1


class TestBudgetQuarantineFlag:
    def test_flag_set_on_corrupt_state(self, tmp_path) -> None:
        (tmp_path / "state").mkdir(parents=True, exist_ok=True)
        (tmp_path / "state" / "budget.json").write_text("x", encoding="utf-8")
        with patch("runtime.crypto.decrypt_file", side_effect=ValueError("bad key")):
            bm = BudgetManager(tmp_path)
        assert bm.state_quarantined is True

    def test_flag_unset_on_clean_state(self, tmp_path) -> None:
        assert BudgetManager(tmp_path).state_quarantined is False
