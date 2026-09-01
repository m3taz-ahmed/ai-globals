"""Tests for dashboard settings → runtime override wiring.

Verifies that apply_settings_to_kernel() actually applies each settings
section onto the live kernel components (budget, guardian, mcp_firewall,
policy, loop_detector, injection_defense, persona, audit, telemetry).

FAST tier — no MCP, no model loading, no network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runtime.settings import (
    clear_settings_cache,
    get_settings_manager,
)


@pytest.fixture
def tmp_root(tmp_path: Path) -> Path:
    """Temp OS root with state/ + a minimal MCP config.json."""
    (tmp_path / "state").mkdir()
    mcp_config = tmp_path / "aizee_mcp" / "config.json"
    mcp_config.parent.mkdir()
    mcp_config.write_text(
        json.dumps({"mcpServers": {"aizee": {}}}),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture(autouse=True)
def _reset_caches():
    clear_settings_cache()
    yield
    clear_settings_cache()


def _make_kernel(tmp_root: Path) -> Any:
    """Create a real Kernel for testing (with settings overrides applied)."""
    from runtime.kernel import Kernel

    return Kernel(root=tmp_root, project_root=tmp_root)


class TestBudgetOverride:
    def test_budget_max_tokens_applied(self, tmp_root: Path) -> None:
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("budget", {"global": {"max_tokens": 999_999}})
        kernel = _make_kernel(tmp_root)
        assert kernel.budget.budgets["global"].max_tokens == 999_999

    def test_budget_zero_means_unlimited(self, tmp_root: Path) -> None:
        """A max_tokens of 0 in settings must NOT impose a zero budget."""
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("budget", {"global": {"max_tokens": 0}})
        kernel = _make_kernel(tmp_root)
        # 0 should be skipped — the BudgetManager default (1_000_000) stays.
        assert kernel.budget.budgets["global"].max_tokens != 0

    def test_budget_on_exceed_applied(self, tmp_root: Path) -> None:
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("budget", {"session": {"on_exceed": "warn"}})
        kernel = _make_kernel(tmp_root)
        assert kernel.budget.budgets["session"].on_exceed == "warn"


class TestGuardianOverride:
    def test_guardian_default_decision_applied(self, tmp_root: Path) -> None:
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("guardian", {"default_decision": "deny"})
        kernel = _make_kernel(tmp_root)
        from runtime.enums import Decision
        assert kernel.guardian.config.default_decision == Decision.DENY

    def test_guardian_on_error_applied(self, tmp_root: Path) -> None:
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("guardian", {"on_evaluation_error": "allow"})
        kernel = _make_kernel(tmp_root)
        from runtime.enums import Decision
        assert kernel.guardian.config.on_evaluation_error == Decision.ALLOW


class TestFirewallOverride:
    def test_firewall_catch_all_applied(self, tmp_root: Path) -> None:
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("mcp_firewall", {"catch_all_action": "deny"})
        kernel = _make_kernel(tmp_root)
        from runtime.mcp_firewall import FirewallAction
        assert kernel.mcp_firewall.default_action == FirewallAction.DENY


class TestPolicyOverride:
    def test_policy_default_action_applied(self, tmp_root: Path) -> None:
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("policy", {"default_action": "allow"})
        kernel = _make_kernel(tmp_root)
        assert kernel.policy.default_action == "allow"


class TestLoopDetectorOverride:
    def test_loop_detector_window_applied(self, tmp_root: Path) -> None:
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("loop_detector", {"window": 50, "threshold": 10})
        kernel = _make_kernel(tmp_root)
        assert kernel.loop_detector.window == 50
        assert kernel.loop_detector.threshold == 10


class TestInjectionDefenseOverride:
    def test_block_threshold_applied(self, tmp_root: Path) -> None:
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("injection_defense", {"block_threshold": 20, "suspicious_threshold": 8})
        kernel = _make_kernel(tmp_root)
        assert kernel.injection_detector.block_threshold == 20
        assert kernel.injection_detector.suspicious_threshold == 8


class TestPersonaOverride:
    def test_persona_default_applied(self, tmp_root: Path) -> None:
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("persona", {"default": "DEV"})
        kernel = _make_kernel(tmp_root)
        assert kernel.persona.default == "DEV"

    def test_persona_multi_applied(self, tmp_root: Path) -> None:
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("persona", {"multi": False})
        kernel = _make_kernel(tmp_root)
        assert kernel.persona.multi is False


class TestAuditOverride:
    def test_audit_retention_applied(self, tmp_root: Path) -> None:
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("audit", {"retention_days": 90})
        kernel = _make_kernel(tmp_root)
        assert kernel.audit.retention_days == 90


class TestTelemetryOverride:
    def test_telemetry_enabled_applied(self, tmp_root: Path) -> None:
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("telemetry", {"enabled": False, "sse_interval": 10})
        kernel = _make_kernel(tmp_root)
        assert kernel.telemetry.enabled is False
        assert kernel.telemetry.sse_interval == 10


class TestReapplyOnReload:
    def test_settings_change_picked_up_on_new_kernel(self, tmp_root: Path) -> None:
        """A new Kernel after settings change picks up the new values."""
        sm = get_settings_manager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        kernel1 = _make_kernel(tmp_root)
        assert kernel1.policy.default_action == "ask"  # default
        sm.update_section("policy", {"default_action": "deny"})
        # Simulate dashboard restart: reload settings + new kernel
        from runtime.settings import reload_settings_manager
        reload_settings_manager(tmp_root)
        kernel2 = _make_kernel(tmp_root)
        assert kernel2.policy.default_action == "deny"
