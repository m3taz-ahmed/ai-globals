#!/usr/bin/env python3
"""Generate a global MCP config with absolute paths for IDE-agnostic use.

Writes ``mcp_config.json`` to the global Devin config directory
(``%APPDATA%\\devin`` on Windows, ``~/.config/devin`` on Linux/macOS)
so that MCP servers are available in **any** workspace, not just
``D:\\.ai``.

All script paths are resolved to absolute paths pointing at the
AI Global OS root, so the config works regardless of which project
is currently open.

Usage:
    python scripts/mcp_global_sync.py          # write global config
    python scripts/mcp_global_sync.py --check   # print what would be written
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def discover_root() -> Path:
    root = os.environ.get("AGENT_OS_ROOT")
    if root and Path(root).is_dir():
        return Path(root)
    return Path(__file__).resolve().parent.parent


def global_config_dir() -> Path:
    """Return the global Devin config directory."""
    if os.name == "nt":
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(base) / "devin"
    return Path.home() / ".config" / "devin"


def build_global_config(root: Path) -> dict:
    """Build MCP config with absolute paths rooted at the OS root."""
    scripts = str(root / "scripts")
    py = sys.executable or "python"

    def abs_script(name: str) -> str:
        return str(root / "scripts" / name)

    return {
        "mcpServers": {
            "ai-global-os": {
                "command": py,
                "args": [abs_script("aios_mcp_wrapper.py")],
            },
            "graphify": {
                "command": py,
                "args": [abs_script("graphify_mcp_wrapper.py")],
            },
            "upwork": {
                "command": py,
                "args": [abs_script("mcp_env_wrapper.py"), "npx", "-y", "@furkankoykiran/upwork-mcp@1.2.2"],
            },
            "freelancer": {
                "command": py,
                "args": [abs_script("mcp_env_wrapper.py"), "npx", "-y", "freelancer-mcp-server@2.0.0"],
            },
            "fiverr": {
                "command": py,
                "args": [abs_script("mcp_env_wrapper.py"), "uvx", "fiverr-mcp-server"],
            },
            "context7": {
                "command": "npx",
                "args": ["-y", "@upstash/context7-mcp@3.1.0"],
            },
            "linkedin": {
                "command": py,
                "args": [abs_script("mcp_env_wrapper.py"), "octopus-linkedin-mcp"],
            },
        }
    }


def main() -> int:
    root = discover_root()
    check_mode = "--check" in sys.argv

    config = build_global_config(root)
    target = global_config_dir() / "mcp_config.json"

    print(f"[mcp-global-sync] OS root: {root}")
    print(f"[mcp-global-sync] Target:  {target}")

    if check_mode:
        print(json.dumps(config, indent=2))
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)

    # Back up existing config if it has content
    if target.exists() and target.stat().st_size > 0:
        backup = target.with_suffix(".json.bak")
        target.rename(backup)
        print(f"[mcp-global-sync] Backed up existing config to {backup}")

    target.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"[mcp-global-sync] Written global MCP config ({len(config['mcpServers'])} servers)")
    print("[mcp-global-sync] All paths are absolute — works from any workspace.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
