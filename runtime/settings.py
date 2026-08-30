"""User-facing settings manager for aiZee dashboard.

Persists user-configurable settings to ``state/settings.json`` (separate from
the canonical config sources: ``aizee_mcp/config.json``,
``runtime/policies/*.yaml``, ``state/budget.json``). This module is the
override layer — the canonical sources remain the source of truth; settings
here act as toggles/overrides applied at load time and on restart.

Design goals:
- Single file persistence (``state/settings.json``) with versioned schema.
- Thread-safe (RWLock via ``threading.RLock``).
- Fail-safe: missing/corrupt file → defaults, never crash.
- No env var mutation (security: dashboard cannot alter process env).
- No direct YAML mutation (policies are canonical; settings toggle them
  in-memory at load time via the kernel restart endpoint).
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from runtime.schemas import AizeeError, ErrorSeverity, ValidationError

_logger = logging.getLogger(__name__)

SETTINGS_VERSION = 2
SETTINGS_FILENAME = "settings.json"

# Migration registry: maps (from_version -> migration function).
# Each function takes the raw loaded dict and returns the migrated dict.
# The version field is bumped to (from_version + 1) after each step.
# Add a new entry here when SETTINGS_VERSION is bumped.
_MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def _register_migration(from_version: int) -> Callable[[Callable[[dict[str, Any]], dict[str, Any]]], Callable[[dict[str, Any]], dict[str, Any]]]:
    """Decorator to register a migration step from ``from_version`` to ``from_version + 1``."""
    def decorator(func: Callable[[dict[str, Any]], dict[str, Any]]) -> Callable[[dict[str, Any]], dict[str, Any]]:
        _MIGRATIONS[from_version] = func
        return func
    return decorator


@_register_migration(1)
def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """v1 → v2: First versioned migration (introduces migration framework).

    Changes:
    - Ensures ``dashboard.trusted_proxies`` exists as a list (was missing in
      some early v1 files).
    - Removes orphaned keys not in the current SECTIONS set.
    """
    # Ensure dashboard.trusted_proxies exists
    dash = data.get("dashboard", {})
    if isinstance(dash, dict) and "trusted_proxies" not in dash:
        dash["trusted_proxies"] = []
        data["dashboard"] = dash
    # Remove orphaned top-level keys (not in SECTIONS, not "version")
    known = set(SECTIONS) | {"version"}
    orphaned = [k for k in data if k not in known]
    for k in orphaned:
        _logger.info("settings migration v1→v2: removing orphaned key %r", k)
        data.pop(k, None)
    return data

# Valid option sets — used for validation on save.
_VALID_DECISIONS: frozenset[str] = frozenset({"allow", "deny", "ask", "require_approval"})
_VALID_PERIODS: frozenset[str] = frozenset({"session", "hourly", "daily", "weekly", "monthly"})
_VALID_EXCEED: frozenset[str] = frozenset({"warn", "fallback", "block"})
_VALID_BOOL_KEYS: frozenset[str] = frozenset({
    "injection_detector", "defensive_injector", "tool_output_sanitizer",
    "baseline_registry", "dual_llm", "taint_enforcement", "agent_baseline",
    "decay_enabled", "vector_search", "slop_verifier", "library_autoload",
    "enabled", "multi", "autoload_lords",
})

# MCP server category grouping for the UI.
MCP_CATEGORIES: dict[str, list[str]] = {
    "Core": ["aizee", "graphify", "context7"],
    "Freelance": ["upwork", "freelancer", "fiverr", "mostaql", "khamsat"],
    "Marketing": ["brevo", "sendgrid", "klaviyo", "kit", "listmonk"],
    "Social": ["twitter", "youtube", "postiz", "automatisch"],
    "Ads": ["google-ads", "meta-ads", "tiktok-ads", "linkedin-ads"],
    "Analytics": ["posthog", "growthbook", "flagsmith", "openreplay"],
    "CRM": ["hubspot", "twenty", "chatwoot", "formbricks", "erpnext"],
    "Billing": ["lago"],
    "Other": ["linkedin", "documenso", "n8n"],
}

# Top-level sections exposed to the dashboard.
SECTIONS: tuple[str, ...] = (
    "mcp_servers", "budget", "guardian", "mcp_firewall", "policy",
    "loop_detector", "injection_defense", "plugins", "persona",
    "dashboard", "telemetry", "audit", "memory", "design",
)


def _default_mcp_servers(config_path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Build default MCP server entries from ``aizee_mcp/config.json``.

    All servers default to ``enabled: true``. If the config file is missing
    or unreadable, returns an empty dict (fail-safe).
    """
    if config_path is None or not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        servers = data.get("mcpServers") or data.get("mcp_servers") or {}
        return {name: {"enabled": True} for name in servers}
    except (json.JSONDecodeError, OSError) as exc:
        _logger.warning("settings: could not load MCP config defaults: %s", exc)
        return {}


def _default_budget() -> dict[str, dict[str, Any]]:
    return {
        "global": {
            "max_tokens": 1_000_000,
            "max_cost_usd": 50.0,
            "max_calls": 0,
            "period": "daily",
            "on_exceed": "block",
            "finalization_reserve": 0.0,
            "token_weight_input": 1.0,
            "token_weight_output": 1.0,
            "fallback_model": None,
        },
        "session": {
            "max_tokens": 100_000,
            "max_cost_usd": 5.0,
            "max_calls": 0,
            "period": "session",
            "on_exceed": "block",
            "finalization_reserve": 0.0,
            "token_weight_input": 1.0,
            "token_weight_output": 1.0,
            "fallback_model": None,
        },
    }


def _default_guardian() -> dict[str, Any]:
    return {
        "default_decision": "ask",
        "on_evaluation_error": "deny",
        "rules": {},
        "kill_switch": {
            "cost_ceiling": 0,
            "file_touched_count": 0,
            "tool_call_count": 0,
            "time_limit": 0,
        },
    }


def _default_mcp_firewall() -> dict[str, Any]:
    return {
        "catch_all_action": "require_approval",
        "rules": {},
    }


def _default_policy() -> dict[str, Any]:
    return {"default_action": "ask"}


def _default_loop_detector() -> dict[str, Any]:
    return {"window": 20, "threshold": 5}


def _default_injection_defense() -> dict[str, Any]:
    return {
        "injection_detector": True,
        "defensive_injector": True,
        "tool_output_sanitizer": True,
        "baseline_registry": True,
        "dual_llm": False,
        "taint_enforcement": True,
        "agent_baseline": True,
        "block_threshold": 12,
        "suspicious_threshold": 5,
    }


def _default_plugins() -> dict[str, Any]:
    return {}


def _default_persona() -> dict[str, Any]:
    return {"default": "ARCH", "multi": True, "autoload_lords": True}


def _default_dashboard() -> dict[str, Any]:
    return {
        "rate_limit": 120,
        "rate_window": 60,
        "max_body_size": 1_048_576,
        "trusted_proxies": [],
        "bind_host": "127.0.0.1",
    }


def _default_telemetry() -> dict[str, Any]:
    return {"enabled": True, "sse_interval": 5}


def _default_audit() -> dict[str, Any]:
    return {"retention_days": 30}


def _default_memory() -> dict[str, Any]:
    return {"decay_enabled": True, "vector_search": True}


def _default_design() -> dict[str, Any]:
    return {"slop_verifier": True, "library_autoload": True}


def default_settings(mcp_config_path: Path | None = None) -> dict[str, Any]:
    """Return the full default settings dict."""
    return {
        "version": SETTINGS_VERSION,
        "mcp_servers": _default_mcp_servers(mcp_config_path),
        "budget": _default_budget(),
        "guardian": _default_guardian(),
        "mcp_firewall": _default_mcp_firewall(),
        "policy": _default_policy(),
        "loop_detector": _default_loop_detector(),
        "injection_defense": _default_injection_defense(),
        "plugins": _default_plugins(),
        "persona": _default_persona(),
        "dashboard": _default_dashboard(),
        "telemetry": _default_telemetry(),
        "audit": _default_audit(),
        "memory": _default_memory(),
        "design": _default_design(),
    }


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base. Base keys win on type mismatch."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _validate_section(section: str, data: dict[str, Any]) -> None:
    """Validate a single section's data. Raises ValidationError on bad input."""
    if section == "budget":
        for scope, cfg in data.items():
            if not isinstance(cfg, dict):
                raise ValidationError(f"budget.{scope} must be an object", context={"scope": scope})
            period = cfg.get("period")
            if period is not None and period not in _VALID_PERIODS:
                raise ValidationError(f"budget.{scope}.period invalid", context={"value": period})
            on_exceed = cfg.get("on_exceed")
            if on_exceed is not None and on_exceed not in _VALID_EXCEED:
                raise ValidationError(f"budget.{scope}.on_exceed invalid", context={"value": on_exceed})
            reserve = cfg.get("finalization_reserve")
            if reserve is not None and not (0.0 <= float(reserve) <= 0.5):
                raise ValidationError(f"budget.{scope}.finalization_reserve must be in [0, 0.5]", context={"value": reserve})
            for num_key in ("max_tokens", "max_calls"):
                val = cfg.get(num_key)
                if val is not None and (not isinstance(val, int) or val < 0):
                    raise ValidationError(f"budget.{scope}.{num_key} must be a non-negative integer", context={"value": val})
            cost = cfg.get("max_cost_usd")
            if cost is not None and (not isinstance(cost, (int, float)) or cost < 0):
                raise ValidationError(f"budget.{scope}.max_cost_usd must be non-negative", context={"value": cost})

    elif section == "guardian":
        decision = data.get("default_decision")
        if decision is not None and decision not in _VALID_DECISIONS:
            raise ValidationError("guardian.default_decision invalid", context={"value": decision})
        err_dec = data.get("on_evaluation_error")
        if err_dec is not None and err_dec not in _VALID_DECISIONS:
            raise ValidationError("guardian.on_evaluation_error invalid", context={"value": err_dec})
        rules = data.get("rules")
        if rules is not None and not isinstance(rules, dict):
            raise ValidationError("guardian.rules must be an object")
        ks = data.get("kill_switch")
        if ks is not None and not isinstance(ks, dict):
            raise ValidationError("guardian.kill_switch must be an object")

    elif section == "mcp_firewall":
        action = data.get("catch_all_action")
        if action is not None and action not in _VALID_DECISIONS:
            raise ValidationError("mcp_firewall.catch_all_action invalid", context={"value": action})
        rules = data.get("rules")
        if rules is not None and not isinstance(rules, dict):
            raise ValidationError("mcp_firewall.rules must be an object")

    elif section == "policy":
        action = data.get("default_action")
        if action is not None and action not in _VALID_DECISIONS:
            raise ValidationError("policy.default_action invalid", context={"value": action})

    elif section == "loop_detector":
        for key in ("window", "threshold"):
            val = data.get(key)
            if val is not None and (not isinstance(val, int) or val < 1):
                raise ValidationError(f"loop_detector.{key} must be a positive integer", context={"value": val})

    elif section == "injection_defense":
        for key, val in data.items():
            if key in _VALID_BOOL_KEYS and not isinstance(val, bool):
                raise ValidationError(f"injection_defense.{key} must be boolean", context={"value": val})
            if key in ("block_threshold", "suspicious_threshold") and (not isinstance(val, int) or val < 0):
                raise ValidationError(f"injection_defense.{key} must be non-negative integer", context={"value": val})

    elif section == "mcp_servers":
        for name, cfg in data.items():
            if not isinstance(cfg, dict):
                raise ValidationError(f"mcp_servers.{name} must be an object", context={"server": name})
            enabled = cfg.get("enabled")
            if enabled is not None and not isinstance(enabled, bool):
                raise ValidationError(f"mcp_servers.{name}.enabled must be boolean", context={"value": enabled})

    elif section == "persona":
        default = data.get("default")
        if default is not None and not isinstance(default, str):
            raise ValidationError("persona.default must be a string")
        for key in ("multi", "autoload_lords"):
            val = data.get(key)
            if val is not None and not isinstance(val, bool):
                raise ValidationError(f"persona.{key} must be boolean", context={"value": val})

    elif section == "dashboard":
        for num_key in ("rate_limit", "rate_window", "max_body_size"):
            val = data.get(num_key)
            if val is not None and (not isinstance(val, int) or val < 0):
                raise ValidationError(f"dashboard.{num_key} must be non-negative integer", context={"value": val})
        host = data.get("bind_host")
        if host is not None and not isinstance(host, str):
            raise ValidationError("dashboard.bind_host must be a string")
        proxies = data.get("trusted_proxies")
        if proxies is not None and not isinstance(proxies, list):
            raise ValidationError("dashboard.trusted_proxies must be a list")

    elif section == "telemetry":
        enabled = data.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            raise ValidationError("telemetry.enabled must be boolean", context={"value": enabled})
        interval = data.get("sse_interval")
        if interval is not None and (not isinstance(interval, int) or interval < 1):
            raise ValidationError("telemetry.sse_interval must be a positive integer", context={"value": interval})

    elif section == "audit":
        days = data.get("retention_days")
        if days is not None and (not isinstance(days, int) or days < 0):
            raise ValidationError("audit.retention_days must be non-negative integer", context={"value": days})

    elif section == "memory":
        for key in ("decay_enabled", "vector_search"):
            val = data.get(key)
            if val is not None and not isinstance(val, bool):
                raise ValidationError(f"memory.{key} must be boolean", context={"value": val})

    elif section == "design":
        for key in ("slop_verifier", "library_autoload"):
            val = data.get(key)
            if val is not None and not isinstance(val, bool):
                raise ValidationError(f"design.{key} must be boolean", context={"value": val})

    elif section == "plugins":
        for name, cfg in data.items():
            if not isinstance(cfg, dict):
                raise ValidationError(f"plugins.{name} must be an object", context={"plugin": name})
            enabled = cfg.get("enabled")
            if enabled is not None and not isinstance(enabled, bool):
                raise ValidationError(f"plugins.{name}.enabled must be boolean", context={"value": enabled})


class SettingsManager:
    """Manages user-facing settings persisted to ``state/settings.json``.

    Thread-safe. Fail-safe: corrupt/missing file → defaults. The canonical
    config sources (YAML policies, MCP config.json, budget.json) are NOT
    modified — this is an override/toggle layer read at load time.
    """

    def __init__(self, root: Path, mcp_config_path: Path | None = None) -> None:
        self.root = root
        self._state_dir = root / "state"
        self._settings_file = self._state_dir / SETTINGS_FILENAME
        self._mcp_config_path = mcp_config_path or (root / "aizee_mcp" / "config.json")
        self._lock = threading.RLock()
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load settings from disk, merging with defaults (fail-safe).

        On load, if the file's schema version is older than ``SETTINGS_VERSION``,
        a migration is performed: the old file is backed up to
        ``settings.json.v{old}.bak``, migration steps run sequentially, and
        the migrated data is saved back.
        """
        defaults = default_settings(self._mcp_config_path)
        if not self._settings_file.exists():
            self._data = defaults
            return
        try:
            raw = json.loads(self._settings_file.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("settings file root is not an object")
            # Run migrations if needed (backs up old file + bumps version)
            raw = self._migrate_if_needed(raw)
            # Merge with defaults (new keys from defaults, user values preserved)
            self._data = _deep_merge(defaults, raw)
            # Prune orphaned section-level keys after merge
            self._prune_orphans()
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            _logger.warning("settings.json unreadable (%s); using defaults", exc)
            # Quarantine corrupt file
            quarantine = self._settings_file.with_suffix(".json.corrupt.bak")
            with contextlib.suppress(OSError):
                self._settings_file.replace(quarantine)
            self._data = defaults

    def _migrate_if_needed(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Run sequential migrations from the file's version to SETTINGS_VERSION.

        Backs up the old file before the first migration. Returns the migrated
        dict (with updated ``version`` field). If the file is already at the
        current version, returns it unchanged.
        """
        file_version = raw.get("version", 1)
        if not isinstance(file_version, int) or file_version < 1:
            file_version = 1
        if file_version >= SETTINGS_VERSION:
            return raw
        # Back up the old file before migrating
        backup = self._settings_file.with_suffix(f".json.v{file_version}.bak")
        with contextlib.suppress(OSError):
            self._settings_file.replace(backup)
        _logger.info(
            "settings.json schema v%d → v%d: backed up to %s",
            file_version, SETTINGS_VERSION, backup.name,
        )
        # Run migrations sequentially
        data = raw
        while file_version < SETTINGS_VERSION:
            step = _MIGRATIONS.get(file_version)
            if step is None:
                _logger.warning(
                    "settings migration: no step for v%d→v%d, skipping",
                    file_version, file_version + 1,
                )
                break
            data = step(data)
            data["version"] = file_version + 1
            file_version += 1
        # Persist migrated data
        self._data = data
        self._save()
        return data

    def _prune_orphans(self) -> None:
        """Remove orphaned top-level keys not in SECTIONS or ``version``."""
        known = set(SECTIONS) | {"version"}
        orphaned = [k for k in self._data if k not in known]
        for k in orphaned:
            _logger.info("settings: pruning orphaned key %r", k)
            self._data.pop(k, None)

    def _save(self) -> None:
        """Persist settings to disk atomically."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._data, indent=2, default=str)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._state_dir), suffix=".json.tmp", prefix="settings-"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp_path, self._settings_file)
        except OSError as exc:
            _logger.error("settings save failed: %s", exc, exc_info=True)
            with contextlib.suppress(OSError):
                os.remove(tmp_path)
            raise AizeeError(
                "SETTINGS_SAVE_FAILED",
                f"Failed to save settings: {exc}",
                ErrorSeverity.HIGH,
            ) from exc

    def get_all(self) -> dict[str, Any]:
        """Return a deep copy of all settings."""
        with self._lock:
            return cast(dict[str, Any], json.loads(json.dumps(self._data, default=str)))

    def migrate(self) -> dict[str, Any]:
        """Explicitly run migrations + return the migrated settings.

        Called by the update/install scripts after pulling new code.
        Safe to call multiple times — no-op if already at current version.
        """
        with self._lock:
            self._load()
            return self.get_all()

    def get_section(self, section: str) -> dict[str, Any]:
        """Return a copy of one section."""
        if section not in SECTIONS:
            raise ValidationError(f"Unknown settings section: {section}", context={"section": section})
        with self._lock:
            data = self._data.get(section, {})
            if isinstance(data, (dict, list)):
                return cast(dict[str, Any], json.loads(json.dumps(data, default=str)))
            return {}

    def update_section(self, section: str, data: dict[str, Any]) -> dict[str, Any]:
        """Validate and persist a section update. Returns the updated section."""
        if section not in SECTIONS:
            raise ValidationError(f"Unknown settings section: {section}", context={"section": section})
        if not isinstance(data, dict):
            raise ValidationError(f"Section data must be an object, got {type(data).__name__}")
        _validate_section(section, data)
        with self._lock:
            # For mcp_servers and plugins, merge with existing so partial
            # updates (e.g. toggling one server) don't wipe the rest.
            if section in ("mcp_servers", "plugins", "guardian", "mcp_firewall"):
                existing = self._data.get(section, {})
                merged = _deep_merge(existing, data) if isinstance(existing, dict) else data
                self._data[section] = merged
            else:
                self._data[section] = data
            self._save()
            return cast(dict[str, Any], json.loads(json.dumps(self._data[section], default=str)))

    def reset_section(self, section: str) -> dict[str, Any]:
        """Reset a section to its default value."""
        if section not in SECTIONS:
            raise ValidationError(f"Unknown settings section: {section}", context={"section": section})
        defaults = default_settings(self._mcp_config_path)
        with self._lock:
            self._data[section] = defaults.get(section, {})
            self._save()
            return cast(dict[str, Any], json.loads(json.dumps(self._data[section], default=str)))

    def reset_all(self) -> dict[str, Any]:
        """Reset all settings to defaults."""
        with self._lock:
            self._data = default_settings(self._mcp_config_path)
            self._save()
            return self.get_all()

    def is_mcp_enabled(self, server_name: str) -> bool:
        """Check if a specific MCP server is enabled (default True if unknown)."""
        with self._lock:
            servers = self._data.get("mcp_servers", {})
            entry = servers.get(server_name, {})
            return bool(entry.get("enabled", True))

    def mcp_status(self) -> dict[str, dict[str, Any]]:
        """Return enabled/disabled status for all known MCP servers."""
        with self._lock:
            servers = self._data.get("mcp_servers", {})
            return {
                name: {"enabled": bool(cfg.get("enabled", True))}
                for name, cfg in servers.items()
            }

    def mcp_categories(self) -> dict[str, list[str]]:
        """Return the MCP category grouping for UI rendering."""
        return dict(MCP_CATEGORIES)

    def reload(self) -> None:
        """Reload settings from disk (used after external edits)."""
        with self._lock:
            self._load()
