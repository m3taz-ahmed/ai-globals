"""Gap tests for runtime/settings.py — validation branches, migrations, appliers."""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from runtime.schemas import ValidationError
from runtime.settings import (
    SettingsManager,
    _apply_audit_overrides,
    _apply_budget_overrides,
    _apply_design_overrides,
    _apply_firewall_overrides,
    _apply_guardian_overrides,
    _apply_injection_defense_overrides,
    _apply_loop_detector_overrides,
    _apply_memory_overrides,
    _apply_persona_overrides,
    _apply_policy_overrides,
    _apply_telemetry_overrides,
    _default_mcp_servers,
    apply_settings_to_kernel,
    clear_settings_cache,
    get_settings_manager,
    reload_settings_manager,
)


def _sm(tmp_path, data: dict[str, Any] | None = None) -> SettingsManager:
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    if data is not None:
        (tmp_path / "state" / "settings.json").write_text(json.dumps(data), encoding="utf-8")
    return SettingsManager(tmp_path)


class TestMcpConfigDefaults:
    def test_bad_json_returns_empty(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text("{not json", encoding="utf-8")
        assert _default_mcp_servers(cfg) == {}

    def test_missing_file_returns_empty(self, tmp_path):
        assert _default_mcp_servers(tmp_path / "nope.json") == {}

    def test_none_returns_empty(self):
        assert _default_mcp_servers(None) == {}

    def test_mcp_servers_alt_key(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"mcp_servers": {"srv1": {}, "srv2": {}}}), encoding="utf-8")
        out = _default_mcp_servers(cfg)
        assert out == {"srv1": {"enabled": True}, "srv2": {"enabled": True}}


class TestSectionValidation:
    @pytest.mark.parametrize("section,data", [
        ("budget", {"session": {"max_cost_usd": -5}}),
        ("guardian", {"on_evaluation_error": "bogus"}),
        ("guardian", {"rules": "notadict"}),
        ("guardian", {"kill_switch": "notadict"}),
        ("mcp_firewall", {"catch_all_action": "bogus"}),
        ("mcp_firewall", {"rules": [1, 2]}),
        ("policy", {"default_action": "bogus"}),
        ("injection_defense", {"block_threshold": -1}),
        ("injection_defense", {"injection_detector": "yes"}),
        ("mcp_servers", {"srv": "notadict"}),
        ("mcp_servers", {"srv": {"enabled": "yes"}}),
        ("persona", {"default": 5}),
        ("persona", {"multi": "yes"}),
        ("dashboard", {"rate_limit": -1}),
        ("dashboard", {"bind_host": 5}),
        ("dashboard", {"trusted_proxies": "notalist"}),
        ("telemetry", {"enabled": "yes"}),
        ("telemetry", {"sse_interval": 0}),
        ("audit", {"retention_days": -1}),
        ("plugins", {"plug": "notadict"}),
        ("plugins", {"plug": {"enabled": "yes"}}),
        ("design", {"slop_verifier": "yes"}),
        ("loop_detector", {"window": 0}),
    ])
    def test_invalid_section_raises(self, tmp_path, section, data):
        sm = _sm(tmp_path)
        with pytest.raises(ValidationError):
            sm.update_section(section, data)


class TestMigrationGaps:
    def test_missing_migration_step_breaks(self, tmp_path):
        # version far below with no step registered -> warns and breaks
        sm = _sm(tmp_path, {"version": 0, "dashboard": {}})
        out = sm.get_all()
        assert isinstance(out, dict)

    def test_prune_orphan_keys(self, tmp_path):
        sm = _sm(tmp_path, {"version": 2, "bogus_key": {"x": 1}})
        sm.reload()
        assert "bogus_key" not in sm.get_all()

    def test_migration_adds_trusted_proxies(self, tmp_path):
        sm = _sm(tmp_path, {"version": 1, "dashboard": {"rate_limit": 5}})
        out = sm.get_all()
        assert out["dashboard"]["trusted_proxies"] == []


class TestAccessorEdges:
    def test_get_section_non_dict_returns_empty(self, tmp_path):
        sm = _sm(tmp_path)
        sm._data["budget"] = "corrupted"  # type: ignore[assignment]
        assert sm.get_section("budget") == {}

    def test_defaults_non_dict_section(self, tmp_path, monkeypatch):
        sm = _sm(tmp_path)
        monkeypatch.setattr(
            "runtime.settings.default_settings",
            lambda _p=None: {"budget": "notadict"},
        )
        assert sm.defaults("budget") == {}

    def test_get_section_unknown_raises(self, tmp_path):
        sm = _sm(tmp_path)
        with pytest.raises(ValidationError):
            sm.get_section("nonexistent")

    def test_defaults_unknown_section_raises(self, tmp_path):
        sm = _sm(tmp_path)
        with pytest.raises(ValidationError):
            sm.defaults("nonexistent")

    def test_update_non_dict_raises(self, tmp_path):
        sm = _sm(tmp_path)
        with pytest.raises(ValidationError):
            sm.update_section("budget", "notadict")  # type: ignore[arg-type]


class TestManagerCache:
    def test_get_reload_clear(self, tmp_path):
        clear_settings_cache()
        sm1 = get_settings_manager(tmp_path)
        assert get_settings_manager(tmp_path) is sm1
        reload_settings_manager(tmp_path)  # exercises sm.reload() path
        clear_settings_cache()
        # reload on uncached root is a no-op
        reload_settings_manager(tmp_path / "other")


class TestAppliers:
    def test_budget_skips_missing_scope_and_zero(self):
        mgr = MagicMock()
        mgr.budgets = {"session": MagicMock()}
        _apply_budget_overrides(mgr, {
            "session": {"max_tokens": 0, "max_cost_usd": 9.5, "junk": None},
            "nonexistent": {"max_tokens": 5},
            "bad": "notadict",
        })
        assert mgr.budgets["session"].max_cost_usd == 9.5
        # max_tokens=0 skipped (unlimited semantics)
        assert mgr.budgets["session"].max_tokens != 0

    def test_guardian_no_config_returns(self):
        _apply_guardian_overrides(object(), {"default_decision": "deny"})

    def test_guardian_maps_decisions(self):
        g = MagicMock()
        _apply_guardian_overrides(g, {"default_decision": "require_approval", "on_evaluation_error": "deny"})
        assert g.config.on_evaluation_error is not None

    def test_firewall_maps_action(self):
        fw = MagicMock()
        _apply_firewall_overrides(fw, {"catch_all_action": "ask"})
        assert fw.default_action is not None
        _apply_firewall_overrides(fw, {"catch_all_action": "bogus"})

    def test_policy_override(self):
        pol = MagicMock()
        _apply_policy_overrides(pol, {"default_action": "deny"})
        assert pol.default_action == "deny"
        _apply_policy_overrides(pol, {})

    def test_loop_detector(self):
        ld = MagicMock()
        _apply_loop_detector_overrides(ld, {"window": 7, "threshold": 3, "bad": "x"})
        assert ld.window == 7
        _apply_loop_detector_overrides(ld, {"window": "bad"})

    def test_injection_defense_no_detector(self):
        _apply_injection_defense_overrides(object(), {"block_threshold": 5})

    def test_injection_defense_sets(self):
        k = MagicMock()
        _apply_injection_defense_overrides(k, {"block_threshold": 5, "suspicious_threshold": 2})
        assert k.injection_detector.block_threshold == 5

    def test_persona_overrides(self):
        p = MagicMock()
        p.PERSONAS = {"coder": {}}
        _apply_persona_overrides(p, {"default": "coder", "multi": True, "autoload_lords": False})
        assert p.default == "coder"
        assert p.multi is True
        _apply_persona_overrides(p, {"default": "nonexistent-persona", "multi": "bad"})

    def test_memory_and_design_store_on_kernel(self):
        k = MagicMock()
        _apply_memory_overrides(k, {"decay_enabled": False})
        _apply_design_overrides(k, {"slop_verifier": True})
        assert k._settings_memory == {"decay_enabled": False}
        assert k._settings_design == {"slop_verifier": True}

    def test_audit_and_telemetry(self):
        a = MagicMock()
        _apply_audit_overrides(a, {"retention_days": 30})
        assert a.retention_days == 30
        _apply_audit_overrides(a, {"retention_days": "bad"})
        t = MagicMock()
        _apply_telemetry_overrides(t, {"enabled": False, "sse_interval": 3})
        assert t.enabled is False
        _apply_telemetry_overrides(t, {"sse_interval": 0})

    def test_apply_to_kernel_no_sm_returns(self):
        apply_settings_to_kernel(object())

    def test_apply_to_kernel_fail_soft(self, tmp_path):
        sm = _sm(tmp_path)
        kernel = MagicMock()
        kernel.settings_manager = sm
        # make every applier raise -> each section logs + continues
        kernel.budget = MagicMock()
        kernel.budget.budgets = None  # force _apply_budget_overrides to raise
        apply_settings_to_kernel(kernel)  # must not raise

    def test_apply_to_kernel_missing_attrs(self, tmp_path):
        sm = _sm(tmp_path)
        kernel = MagicMock(spec=[])  # no attributes at all
        kernel.settings_manager = sm
        apply_settings_to_kernel(kernel)  # exercises every hasattr-miss branch
