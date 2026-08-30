"""Tests for runtime/settings.py — user-facing settings manager.

Covers: defaults, load/save, validation, section updates, MCP toggles,
reset, fail-safe on corrupt file.
FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.schemas import ValidationError
from runtime.settings import (
    MCP_CATEGORIES,
    SECTIONS,
    SettingsManager,
    default_settings,
)


@pytest.fixture
def tmp_root(tmp_path: Path) -> Path:
    """Provide a temp root with a state/ dir and a minimal MCP config."""
    (tmp_path / "state").mkdir()
    mcp_config = tmp_path / "aizee_mcp" / "config.json"
    mcp_config.parent.mkdir()
    mcp_config.write_text(
        json.dumps({"mcpServers": {"aizee": {}, "upwork": {}, "context7": {}}}),
        encoding="utf-8",
    )
    return tmp_path


# -- Defaults ----------------------------------------------------------------


class TestDefaults:
    def test_default_settings_has_all_sections(self, tmp_root: Path) -> None:
        defaults = default_settings(tmp_root / "aizee_mcp" / "config.json")
        for section in SECTIONS:
            assert section in defaults, f"missing section: {section}"

    def test_default_mcp_servers_from_config(self, tmp_root: Path) -> None:
        defaults = default_settings(tmp_root / "aizee_mcp" / "config.json")
        servers = defaults["mcp_servers"]
        assert "aizee" in servers
        assert "upwork" in servers
        assert servers["aizee"]["enabled"] is True

    def test_default_budget_has_global_and_session(self, tmp_root: Path) -> None:
        defaults = default_settings()
        assert "global" in defaults["budget"]
        assert "session" in defaults["budget"]
        assert defaults["budget"]["global"]["max_tokens"] == 1_000_000

    def test_default_injection_defense_all_true_except_dual_llm(self, tmp_root: Path) -> None:
        defaults = default_settings()
        inj = defaults["injection_defense"]
        assert inj["injection_detector"] is True
        assert inj["dual_llm"] is False
        assert inj["block_threshold"] == 12

    def test_mcp_categories_non_empty(self) -> None:
        assert len(MCP_CATEGORIES) >= 8
        assert "Core" in MCP_CATEGORIES


# -- Load / Save -------------------------------------------------------------


class TestLoadSave:
    def test_load_defaults_when_no_file(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        assert sm.get_section("budget")["global"]["max_tokens"] == 1_000_000

    def test_save_creates_file(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("policy", {"default_action": "allow"})
        assert (tmp_root / "state" / "settings.json").exists()

    def test_reload_after_save(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("policy", {"default_action": "deny"})
        sm2 = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        assert sm2.get_section("policy")["default_action"] == "deny"

    def test_corrupt_file_falls_back_to_defaults(self, tmp_root: Path) -> None:
        settings_file = tmp_root / "state" / "settings.json"
        settings_file.write_text("{not valid json", encoding="utf-8")
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        # Should fall back to defaults, not crash
        assert sm.get_section("budget")["global"]["max_tokens"] == 1_000_000
        # Corrupt file should be quarantined
        assert not settings_file.exists()

    def test_non_dict_root_falls_back(self, tmp_root: Path) -> None:
        settings_file = tmp_root / "state" / "settings.json"
        settings_file.write_text("[1, 2, 3]", encoding="utf-8")
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        assert sm.get_section("budget")["global"]["max_tokens"] == 1_000_000


# -- Section Updates ---------------------------------------------------------


class TestSectionUpdates:
    def test_update_policy(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        result = sm.update_section("policy", {"default_action": "deny"})
        assert result["default_action"] == "deny"

    def test_update_mcp_server_toggle_merges(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        # Toggle off only upwork
        sm.update_section("mcp_servers", {"upwork": {"enabled": False}})
        status = sm.mcp_status()
        assert status["upwork"]["enabled"] is False
        assert status["aizee"]["enabled"] is True

    def test_update_budget_validates_period(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        with pytest.raises(ValidationError):
            sm.update_section("budget", {"global": {"period": "yearly"}})

    def test_update_budget_validates_reserve_range(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        with pytest.raises(ValidationError):
            sm.update_section("budget", {"global": {"finalization_reserve": 0.6}})

    def test_update_guardian_validates_decision(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        with pytest.raises(ValidationError):
            sm.update_section("guardian", {"default_decision": "maybe"})

    def test_update_loop_detector_validates_positive(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        with pytest.raises(ValidationError):
            sm.update_section("loop_detector", {"window": 0})

    def test_update_injection_defense_validates_bool(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        with pytest.raises(ValidationError):
            sm.update_section("injection_defense", {"injection_detector": "yes"})

    def test_update_unknown_section_raises(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        with pytest.raises(ValidationError):
            sm.update_section("nonexistent", {})

    def test_update_non_dict_data_raises(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        with pytest.raises(ValidationError):
            sm.update_section("policy", "not a dict")  # type: ignore[arg-type]


# -- Reset -------------------------------------------------------------------


class TestReset:
    def test_reset_section(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("policy", {"default_action": "deny"})
        result = sm.reset_section("policy")
        assert result["default_action"] == "ask"

    def test_reset_all(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("policy", {"default_action": "deny"})
        sm.update_section("budget", {"global": {"max_tokens": 500}})
        result = sm.reset_all()
        assert result["policy"]["default_action"] == "ask"
        assert result["budget"]["global"]["max_tokens"] == 1_000_000

    def test_reset_unknown_section_raises(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        with pytest.raises(ValidationError):
            sm.reset_section("nonexistent")


# -- MCP Status --------------------------------------------------------------


class TestMcpStatus:
    def test_mcp_status_returns_all_servers(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        status = sm.mcp_status()
        assert "aizee" in status
        assert "upwork" in status
        assert status["aizee"]["enabled"] is True

    def test_is_mcp_enabled_default_true(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        assert sm.is_mcp_enabled("aizee") is True
        # Unknown server defaults to True (fail-open for config)
        assert sm.is_mcp_enabled("unknown_server") is True

    def test_is_mcp_enabled_after_disable(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        sm.update_section("mcp_servers", {"upwork": {"enabled": False}})
        assert sm.is_mcp_enabled("upwork") is False
        assert sm.is_mcp_enabled("aizee") is True

    def test_mcp_categories(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        cats = sm.mcp_categories()
        assert "Core" in cats
        assert "aizee" in cats["Core"]


# -- Reload ------------------------------------------------------------------


class TestReload:
    def test_reload_picks_up_external_changes(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        # Write a new settings file directly
        (tmp_root / "state" / "settings.json").write_text(
            json.dumps({"version": 1, "policy": {"default_action": "allow"}}),
            encoding="utf-8",
        )
        sm.reload()
        assert sm.get_section("policy")["default_action"] == "allow"


# -- Get Section -------------------------------------------------------------


class TestGetSection:
    def test_get_section_returns_copy(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        s1 = sm.get_section("budget")
        s1["global"]["max_tokens"] = 999
        s2 = sm.get_section("budget")
        assert s2["global"]["max_tokens"] == 1_000_000

    def test_get_section_unknown_raises(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        with pytest.raises(ValidationError):
            sm.get_section("nonexistent")

    def test_get_all_returns_deep_copy(self, tmp_root: Path) -> None:
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        all1 = sm.get_all()
        all1["budget"]["global"]["max_tokens"] = 999
        all2 = sm.get_all()
        assert all2["budget"]["global"]["max_tokens"] == 1_000_000


# -- Migration ---------------------------------------------------------------


class TestMigration:
    def test_fresh_install_no_migration(self, tmp_root: Path) -> None:
        """No settings.json → no migration, defaults used."""
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        all_settings = sm.get_all()
        assert all_settings["version"] == 2  # SETTINGS_VERSION
        assert not (tmp_root / "state" / "settings.json").exists()

    def test_v1_file_triggers_migration(self, tmp_root: Path) -> None:
        """v1 file → migrated to v2, backup created."""
        settings_file = tmp_root / "state" / "settings.json"
        settings_file.write_text(
            json.dumps({"version": 1, "policy": {"default_action": "deny"}}),
            encoding="utf-8",
        )
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        all_settings = sm.get_all()
        assert all_settings["version"] == 2
        # User value preserved
        assert all_settings["policy"]["default_action"] == "deny"
        # Backup created
        assert (tmp_root / "state" / "settings.json.v1.bak").exists()
        # Migrated file saved with new version
        saved = json.loads(settings_file.read_text(encoding="utf-8"))
        assert saved["version"] == 2

    def test_v1_orphaned_keys_removed(self, tmp_root: Path) -> None:
        """v1 file with orphaned keys → migration removes them."""
        settings_file = tmp_root / "state" / "settings.json"
        settings_file.write_text(
            json.dumps({
                "version": 1,
                "policy": {"default_action": "allow"},
                "old_removed_section": {"foo": "bar"},
                "another_orphan": 123,
            }),
            encoding="utf-8",
        )
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        all_settings = sm.get_all()
        assert "old_removed_section" not in all_settings
        assert "another_orphan" not in all_settings
        assert "policy" in all_settings  # valid section preserved

    def test_v2_file_no_migration(self, tmp_root: Path) -> None:
        """v2 file (current) → no migration, no backup."""
        settings_file = tmp_root / "state" / "settings.json"
        settings_file.write_text(
            json.dumps({"version": 2, "policy": {"default_action": "deny"}}),
            encoding="utf-8",
        )
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        all_settings = sm.get_all()
        assert all_settings["version"] == 2
        # No backup created (already current)
        assert not (tmp_root / "state" / "settings.json.v2.bak").exists()

    def test_missing_version_treated_as_v1(self, tmp_root: Path) -> None:
        """File without version field → treated as v1, migrated."""
        settings_file = tmp_root / "state" / "settings.json"
        settings_file.write_text(
            json.dumps({"policy": {"default_action": "allow"}}),
            encoding="utf-8",
        )
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        all_settings = sm.get_all()
        assert all_settings["version"] == 2
        assert (tmp_root / "state" / "settings.json.v1.bak").exists()

    def test_explicit_migrate_method(self, tmp_root: Path) -> None:
        """migrate() method works explicitly."""
        settings_file = tmp_root / "state" / "settings.json"
        settings_file.write_text(
            json.dumps({"version": 1, "policy": {"default_action": "allow"}}),
            encoding="utf-8",
        )
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        # Already migrated on load; calling migrate() again is a no-op
        result = sm.migrate()
        assert result["version"] == 2
        # Only one backup (not two)
        assert (tmp_root / "state" / "settings.json.v1.bak").exists()
        assert not (tmp_root / "state" / "settings.json.v2.bak").exists()

    def test_migration_preserves_user_values(self, tmp_root: Path) -> None:
        """User-customized values survive migration."""
        settings_file = tmp_root / "state" / "settings.json"
        settings_file.write_text(
            json.dumps({
                "version": 1,
                "budget": {"global": {"max_tokens": 500000, "max_cost_usd": 25.0}},
                "guardian": {"default_decision": "deny"},
                "mcp_servers": {"upwork": {"enabled": False}},
            }),
            encoding="utf-8",
        )
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        all_settings = sm.get_all()
        # User values preserved
        assert all_settings["budget"]["global"]["max_tokens"] == 500000
        assert all_settings["budget"]["global"]["max_cost_usd"] == 25.0
        assert all_settings["guardian"]["default_decision"] == "deny"
        assert all_settings["mcp_servers"]["upwork"]["enabled"] is False
        # New defaults merged in (session budget wasn't in user file)
        assert "session" in all_settings["budget"]
        assert all_settings["budget"]["session"]["max_tokens"] == 100_000

    def test_migration_adds_missing_trusted_proxies(self, tmp_root: Path) -> None:
        """v1→v2 migration ensures dashboard.trusted_proxies exists."""
        settings_file = tmp_root / "state" / "settings.json"
        settings_file.write_text(
            json.dumps({"version": 1, "policy": {"default_action": "allow"}}),
            encoding="utf-8",
        )
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        all_settings = sm.get_all()
        assert "trusted_proxies" in all_settings["dashboard"]
        assert isinstance(all_settings["dashboard"]["trusted_proxies"], list)

    def test_corrupt_file_quarantined_not_migrated(self, tmp_root: Path) -> None:
        """Corrupt file → quarantined, defaults used, no migration."""
        settings_file = tmp_root / "state" / "settings.json"
        settings_file.write_text("{not valid json", encoding="utf-8")
        sm = SettingsManager(tmp_root, tmp_root / "aizee_mcp" / "config.json")
        all_settings = sm.get_all()
        assert all_settings["version"] == 2  # defaults
        # Quarantined, not backed up as v1
        assert (tmp_root / "state" / "settings.json.corrupt.bak").exists()
        assert not (tmp_root / "state" / "settings.json.v1.bak").exists()
