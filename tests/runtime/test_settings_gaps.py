"""Gap-coverage tests for runtime/settings.py — validation, merge, apply-to-kernel."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from runtime import settings as settings_mod
from runtime.schemas import AizeeError, ValidationError
from runtime.settings import (
    SettingsManager,
    apply_settings_to_kernel,
    clear_settings_cache,
    get_settings_manager,
    reload_settings_manager,
)


@pytest.fixture()
def sm(tmp_path):
    return SettingsManager(tmp_path)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_settings_cache()
    yield
    clear_settings_cache()


class TestValidation:
    def test_unknown_section(self, sm):
        with pytest.raises(ValidationError, match="Unknown settings section"):
            sm.update_section("nope", {})

    def test_non_dict_data(self, sm):
        with pytest.raises(ValidationError, match="must be an object"):
            sm.update_section("budget", "x")

    @pytest.mark.parametrize("cfg,match", [
        ({"s": "notadict"}, "must be an object"),
        ({"s": {"period": "bogus"}}, "period invalid"),
        ({"s": {"on_exceed": "bogus"}}, "on_exceed invalid"),
        ({"s": {"finalization_reserve": 0.9}}, "in \\[0, 0.5\\]"),
        ({"s": {"max_tokens": "x"}}, "max_tokens"),
    ])
    def test_budget_validation(self, sm, cfg, match):
        with pytest.raises(ValidationError, match=match):
            sm.update_section("budget", cfg)

    def test_budget_valid(self, sm):
        out = sm.update_section("budget", {"session": {"max_tokens": 500}})
        assert out["session"]["max_tokens"] == 500

    @pytest.mark.parametrize("cfg", [
        {"rate_limit": "x"}, {"rate_limit": -1},
        {"bind_host": 5}, {"trusted_proxies": "x"},
    ])
    def test_dashboard_validation(self, sm, cfg):
        with pytest.raises(ValidationError):
            sm.update_section("dashboard", cfg)

    def test_telemetry_validation(self, sm):
        with pytest.raises(ValidationError, match="enabled must be boolean"):
            sm.update_section("telemetry", {"enabled": "yes"})

    def test_audit_validation(self, sm):
        with pytest.raises(ValidationError, match="retention_days"):
            sm.update_section("audit", {"retention_days": -1})
        sm.update_section("audit", {"retention_days": 30})

    def test_memory_validation(self, sm):
        with pytest.raises(ValidationError, match="must be boolean"):
            sm.update_section("memory", {"decay_enabled": 1})
        sm.update_section("memory", {"decay_enabled": True})

    def test_design_validation(self, sm):
        with pytest.raises(ValidationError, match="must be boolean"):
            sm.update_section("design", {"slop_verifier": "x"})
        sm.update_section("design", {"library_autoload": False})


class TestSections:
    def test_get_section_unknown(self, sm):
        with pytest.raises(ValidationError):
            sm.get_section("nope")

    def test_get_section_copy(self, sm):
        s = sm.get_section("budget")
        s["mutated"] = True
        assert "mutated" not in sm.get_section("budget")

    def test_update_merges_mcp(self, sm):
        sm.update_section("mcp_servers", {"srv1": {"enabled": True}})
        sm.update_section("mcp_servers", {"srv2": {"enabled": False}})
        merged = sm.get_section("mcp_servers")
        assert "srv1" in merged and "srv2" in merged

    def test_update_replaces_scalar_sections(self, sm):
        sm.update_section("telemetry", {"enabled": False})
        sm.update_section("telemetry", {"sse_interval": 5})
        assert "enabled" not in sm.get_section("telemetry")

    def test_reset_section(self, sm):
        sm.update_section("telemetry", {"enabled": False})
        sm.reset_section("telemetry")
        assert sm.get_section("telemetry")["enabled"] is True

    def test_reset_unknown(self, sm):
        with pytest.raises(ValidationError):
            sm.reset_section("nope")

    def test_defaults_preview_no_mutation(self, sm):
        sm.update_section("telemetry", {"enabled": False})
        d = sm.defaults("telemetry")
        assert d["enabled"] is True  # default, not current
        assert sm.get_section("telemetry")["enabled"] is False

    def test_defaults_all_and_unknown(self, sm):
        assert "budget" in sm.defaults()
        with pytest.raises(ValidationError):
            sm.defaults("nope")

    def test_reset_all(self, sm):
        sm.update_section("telemetry", {"enabled": False})
        sm.reset_all()
        assert sm.get_section("telemetry")["enabled"] is True

    def test_is_mcp_enabled(self, sm):
        sm.update_section("mcp_servers", {"aizee": {"enabled": False}})
        assert sm.is_mcp_enabled("aizee") is False
        assert sm.is_mcp_enabled("unknown_srv") is True

    def test_mcp_status(self, sm):
        sm.update_section("mcp_servers", {"a": {"enabled": False}, "b": {}})
        st = sm.mcp_status()
        assert st["a"]["enabled"] is False and st["b"]["enabled"] is True

    def test_mcp_categories(self, sm):
        assert isinstance(sm.mcp_categories(), dict)

    def test_migrate_idempotent(self, sm):
        out = sm.migrate()
        assert out["version"] >= 1
        out2 = sm.migrate()
        assert out["version"] == out2["version"]

    def test_reload(self, tmp_path):
        m1 = SettingsManager(tmp_path)
        m1.update_section("telemetry", {"enabled": False})
        m2 = SettingsManager(tmp_path)
        m2.update_section("telemetry", {"enabled": True})
        m1.reload()
        assert m1.get_section("telemetry")["enabled"] is True


class TestPersistence:
    def test_corrupt_file_quarantined(self, tmp_path):
        sd = tmp_path / "state"
        sd.mkdir()
        (sd / "settings.json").write_text("{bad")
        m = SettingsManager(tmp_path)
        assert m.get_all()  # defaults loaded
        assert (sd / "settings.json.corrupt.bak").exists()

    def test_save_failure_raises(self, sm):
        with patch("os.replace", side_effect=OSError("disk")):
            with pytest.raises(AizeeError):
                sm.update_section("telemetry", {"enabled": False})

    def test_old_version_migrates(self, tmp_path):
        sd = tmp_path / "state"
        sd.mkdir()
        (sd / "settings.json").write_text(json.dumps(
            {"version": 0, "telemetry": {"enabled": False}}))
        m = SettingsManager(tmp_path)
        assert m.get_all()["version"] == settings_mod.SETTINGS_VERSION
        assert list(sd.glob("settings.json.v*.bak"))


class TestCache:
    def test_cached_instance(self, tmp_path):
        m1 = get_settings_manager(tmp_path)
        m2 = get_settings_manager(tmp_path)
        assert m1 is m2

    def test_reload_cached(self, tmp_path):
        get_settings_manager(tmp_path)
        reload_settings_manager(tmp_path)  # no-op safe
        reload_settings_manager(tmp_path / "other")  # uncached → no-op


class TestApplyToKernel:
    def test_no_settings_manager_noop(self):
        k = MagicMock(spec=[])
        del k.settings_manager
        apply_settings_to_kernel(k)  # early return

    def test_full_apply(self):
        k = MagicMock()
        sm = MagicMock()
        sm.get_section.side_effect = lambda s: {
            "budget": {"session": {"max_tokens": 500, "on_exceed": "warn"}},
            "guardian": {"default_decision": "deny"},
            "mcp_firewall": {"catch_all_action": "deny"},
            "policy": {"default_action": "ask"},
            "loop_detector": {"window": 5, "threshold": 3},
            "injection_defense": {"block_threshold": 90,
                                  "suspicious_threshold": 50},
            "persona": {"default": "arch", "multi": True},
            "memory": {"decay_enabled": True},
            "design": {"slop_verifier": False},
            "audit": {"retention_days": 7},
            "telemetry": {"enabled": False, "sse_interval": 2},
        }.get(s, {})
        k.settings_manager = sm
        k.budget.budgets = {"session": MagicMock(max_tokens=None)}
        k.guardian.config = MagicMock()
        k.injection_detector = MagicMock()
        k.persona.PERSONAS = {"arch": object()}
        apply_settings_to_kernel(k)
        assert k.budget.budgets["session"].max_tokens == 500
        assert k.policy.default_action == "ask"
        assert k.loop_detector.window == 5
        assert k.injection_detector.block_threshold == 90
        assert k.persona.default == "arch"
        assert k.audit.retention_days == 7
        assert k.telemetry.enabled is False

    def test_apply_error_isolated(self):
        k = MagicMock()
        sm = MagicMock()
        sm.get_section.side_effect = RuntimeError("boom")
        k.settings_manager = sm
        apply_settings_to_kernel(k)  # all sections warn, no raise

    def test_budget_skips_unknown_scope(self):
        k = MagicMock()
        sm = MagicMock()
        sm.get_section.side_effect = lambda s: (
            {"budget": {"nonexistent_scope": {"max_tokens": 1},
                        "session": "notadict",
                        "global": {"max_tokens": 0}}}.get(s, {}))
        k.settings_manager = sm
        k.budget.budgets = {"global": MagicMock(max_tokens=999)}
        apply_settings_to_kernel(k)
        # 0 limit skipped (unlimited), nonexistent scope not created
        assert k.budget.budgets["global"].max_tokens == 999
