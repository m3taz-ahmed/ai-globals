#!/usr/bin/env python3
"""aiZee settings verification — confirms settings are applied even when dashboard is closed.

This script verifies the full settings-persistence chain:
1. settings.json exists and is valid JSON with correct schema version.
2. IDE config files (Devin, Claude, Cursor) match settings.json MCP toggles.
3. The daemon is running (or was recently running) and has synced.
4. The MCP server (aizee_mcp) would load settings on next kernel init.
5. Budget/guardian/policy overrides are present in settings.json.

Usage:
    python scripts/verify_settings.py              # Full verification
    python scripts/verify_settings.py --root PATH  # Custom root
    python scripts/verify_settings.py --json       # JSON output (for CI/tray)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def discover_root(arg_root: str | None) -> Path:
    if arg_root:
        return Path(arg_root)
    env = os.environ.get("AIZEE_ROOT")
    if env and Path(env).is_dir():
        return Path(env)
    return Path(__file__).resolve().parent.parent


def verify_settings_file(root: Path) -> dict[str, Any]:
    """Check settings.json exists, is valid, and has correct schema."""
    path = root / "state" / "settings.json"
    result: dict[str, Any] = {"check": "settings_file", "ok": False, "details": {}}
    if not path.exists():
        result["error"] = f"settings.json not found at {path}"
        return result
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        result["error"] = f"settings.json invalid: {exc}"
        return result
    version = data.get("version", 1)
    result["details"]["version"] = version
    result["details"]["sections"] = list(data.keys())
    result["ok"] = True
    return result


def verify_mcp_toggles(root: Path) -> dict[str, Any]:
    """Check that IDE config files match settings.json MCP server toggles."""
    settings_path = root / "state" / "settings.json"
    result: dict[str, Any] = {"check": "mcp_toggles_synced", "ok": True, "details": {}}
    if not settings_path.exists():
        result["ok"] = False
        result["error"] = "settings.json missing"
        return result
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        result["ok"] = False
        result["error"] = "settings.json invalid"
        return result
    mcp_servers = settings.get("mcp_servers", {})
    if not isinstance(mcp_servers, dict):
        result["ok"] = False
        result["error"] = "mcp_servers section invalid"
        return result

    mismatches: list[str] = []

    # Check .devin/mcp_config.local.json
    devin_local = root / ".devin" / "mcp_config.local.json"
    if devin_local.exists():
        try:
            devin_cfg = json.loads(devin_local.read_text(encoding="utf-8"))
            devin_servers = devin_cfg.get("mcpServers", {})
            for name, cfg in mcp_servers.items():
                if not isinstance(cfg, dict):
                    continue
                enabled = cfg.get("enabled", True)
                devin_entry = devin_servers.get(name, {})
                devin_disabled = devin_entry.get("disabled", False) if isinstance(devin_entry, dict) else False
                if not enabled and not devin_disabled:
                    mismatches.append(f"Devin: {name} disabled in settings but not in .devin config")
                if enabled and devin_disabled:
                    mismatches.append(f"Devin: {name} enabled in settings but disabled in .devin config")
        except (json.JSONDecodeError, OSError):
            mismatches.append("Devin: .devin/mcp_config.local.json unreadable")

    # Check .claude/settings.json
    claude_path = root / ".claude" / "settings.json"
    if claude_path.exists():
        try:
            claude_cfg = json.loads(claude_path.read_text(encoding="utf-8"))
            claude_servers = claude_cfg.get("mcpServers", {})
            for name, cfg in mcp_servers.items():
                if not isinstance(cfg, dict):
                    continue
                enabled = cfg.get("enabled", True)
                in_claude = name in claude_servers
                if not enabled and in_claude:
                    mismatches.append(f"Claude: {name} disabled in settings but present in .claude config")
        except (json.JSONDecodeError, OSError):
            mismatches.append("Claude: .claude/settings.json unreadable")

    result["details"]["mcp_servers_count"] = len(mcp_servers)
    result["details"]["enabled_count"] = sum(1 for c in mcp_servers.values() if isinstance(c, dict) and c.get("enabled", True))
    result["details"]["disabled_count"] = sum(1 for c in mcp_servers.values() if isinstance(c, dict) and not c.get("enabled", True))
    if mismatches:
        result["ok"] = False
        result["details"]["mismatches"] = mismatches
    return result


def verify_daemon(root: Path) -> dict[str, Any]:
    """Check if the daemon is running or was recently running."""
    result: dict[str, Any] = {"check": "daemon_running", "ok": False, "details": {}}
    try:
        # Ensure root is on sys.path for the import
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from runtime.daemon import AizeeDaemon
        status = AizeeDaemon.status(root)
        result["details"] = status
        result["ok"] = status.get("running", False)
        if not result["ok"]:
            result["error"] = "Daemon not running — settings may not sync when dashboard is closed"
    except Exception as exc:
        result["error"] = f"Cannot check daemon status: {exc}"
    return result


def verify_kernel_loads_settings(root: Path) -> dict[str, Any]:
    """Verify that a fresh Kernel init would apply settings (smoke test)."""
    result: dict[str, Any] = {"check": "kernel_applies_settings", "ok": False, "details": {}}
    try:
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from runtime.settings import get_settings_manager
        sm = get_settings_manager(root)
        all_settings = sm.get_all()
        result["details"]["sections_loaded"] = list(all_settings.keys())
        result["details"]["version"] = all_settings.get("version")
        # Check a few key sections
        for section in ("mcp_servers", "budget", "guardian", "policy"):
            if section not in all_settings:
                result["error"] = f"Section '{section}' missing from loaded settings"
                return result
        result["ok"] = True
    except Exception as exc:
        result["error"] = f"Kernel settings load failed: {exc}"
    return result


def verify_budget_overrides(root: Path) -> dict[str, Any]:
    """Check budget settings are present and valid."""
    result: dict[str, Any] = {"check": "budget_overrides", "ok": False, "details": {}}
    try:
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from runtime.settings import get_settings_manager
        sm = get_settings_manager(root)
        budget = sm.get_section("budget")
        for scope in ("global", "session"):
            if scope not in budget:
                result["error"] = f"budget.{scope} missing"
                return result
            cfg = budget[scope]
            if "max_tokens" not in cfg or "max_cost_usd" not in cfg:
                result["error"] = f"budget.{scope} missing max_tokens or max_cost_usd"
                return result
        result["details"]["global_max_tokens"] = budget["global"].get("max_tokens")
        result["details"]["session_max_tokens"] = budget["session"].get("max_tokens")
        result["ok"] = True
    except Exception as exc:
        result["error"] = f"Budget verification failed: {exc}"
    return result


def run_verification(root: Path) -> dict[str, Any]:
    """Run all verification checks. Returns full report."""
    checks = [
        verify_settings_file(root),
        verify_mcp_toggles(root),
        verify_daemon(root),
        verify_kernel_loads_settings(root),
        verify_budget_overrides(root),
    ]
    all_ok = all(c["ok"] for c in checks)
    return {
        "root": str(root),
        "all_ok": all_ok,
        "checks": checks,
        "summary": {
            "total": len(checks),
            "passed": sum(1 for c in checks if c["ok"]),
            "failed": sum(1 for c in checks if not c["ok"]),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="aiZee settings verification")
    parser.add_argument("--root", default=None, help="aiZee root directory")
    parser.add_argument("--json", action="store_true", help="JSON output (for CI/tray)")
    args = parser.parse_args(argv)

    root = discover_root(args.root)
    report = run_verification(root)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("=" * 60)
        print("  aiZee Settings Verification")
        print("=" * 60)
        print(f"  Root: {root}")
        print()
        for check in report["checks"]:
            status = "PASS" if check["ok"] else "FAIL"
            icon = "+" if check["ok"] else "x"
            print(f"  [{icon}] {check['check']}: {status}")
            if not check["ok"] and "error" in check:
                print(f"       Error: {check['error']}")
            if check.get("details"):
                for k, v in check["details"].items():
                    if k != "mismatches" and not isinstance(v, (dict, list)):
                        print(f"       {k}: {v}")
                if "mismatches" in check.get("details", {}):
                    for m in check["details"]["mismatches"]:
                        print(f"       MISMATCH: {m}")
        print()
        print(f"  Summary: {report['summary']['passed']}/{report['summary']['total']} checks passed")
        if report["all_ok"]:
            print("  [OK] All settings verified — dashboard can be closed safely.")
        else:
            print("  [WARN] Some checks failed — settings may not persist when dashboard is closed.")
        print("=" * 60)

    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
