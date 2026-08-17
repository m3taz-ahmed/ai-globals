#!/usr/bin/env python3
"""Centralized secrets loader for aiZee MCP servers.

Reads ``.env`` from the OS root and injects all key-value pairs into
``os.environ`` **before** any MCP server process is spawned. This keeps
secrets out of the repository (``.env`` is git-ignored) while making
them available to every MCP server and plugin transparently.

Usage (automatic):
    The MCP wrappers (``aizee_mcp_wrapper.py``, ``graphify_mcp_wrapper.py``)
    call ``load_env()`` at startup. External MCP servers spawned by
    ``runtime/mcp_client.py`` inherit the augmented environment.

Usage (manual / CLI):
    python scripts/mcp_secrets_loader.py          # load + print status
    python scripts/mcp_secrets_loader.py --check   # exit 1 if missing required vars

Resolution order:
    1. ``AIZEE_ROOT/.env``  (canonical location)
    2. ``cwd/.env``            (fallback for non-standard layouts)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def discover_env_file() -> Path | None:
    """Find the ``.env`` file to load."""
    # 1. Explicit AIZEE_ROOT
    root_env = os.environ.get("AIZEE_ROOT")
    if root_env:
        candidate = Path(root_env) / ".env"
        if candidate.is_file():
            return candidate
    # 2. Parent of this script (scripts/ -> root/)
    script_parent = Path(__file__).resolve().parent.parent
    candidate = script_parent / ".env"
    if candidate.is_file():
        return candidate
    # 3. CWD fallback
    candidate = Path.cwd() / ".env"
    if candidate.is_file():
        return candidate
    return None


def parse_env_line(line: str) -> tuple[str, str] | None:
    """Parse a single ``KEY=VALUE`` line. Returns None for comments/blanks."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    # Strip optional ``export `` prefix
    if line.startswith("export "):
        line = line[7:]
    if "=" not in line:
        return None
    key, _, value = line.partition("=")
    key = key.strip()
    value = value.strip()
    # Remove surrounding quotes
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    if not key:
        return None
    return key, value


def load_env(env_path: Path | None = None, overwrite: bool = False) -> dict[str, str]:
    """Load ``.env`` into ``os.environ``.

    Args:
        env_path: Explicit path to ``.env``. Auto-discovered if None.
        overwrite: If True, replace existing env vars. Default: only set missing.

    Returns:
        Dict of newly-injected key-value pairs.
    """
    if env_path is None:
        env_path = discover_env_file()
    if env_path is None or not env_path.is_file():
        return {}

    injected: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        parsed = parse_env_line(line)
        if parsed is None:
            continue
        key, value = parsed
        # Skip placeholder values
        if value.startswith("your_") and value.endswith("_here"):
            continue
        if overwrite or key not in os.environ or not os.environ[key]:
            os.environ[key] = value
            injected[key] = value
    return injected


# Required vars per MCP server (for --check mode).
# A server passes if ANY of its alternative vars is set.
REQUIRED_VARS: dict[str, list[list[str]]] = {
    "linkedin": [["LINKEDIN_ACCESS_TOKEN"], ["LINKEDIN_MCP_TOKEN_PATH"]],
    "upwork": [["UPWORK_CLIENT_ID", "UPWORK_CLIENT_SECRET"]],
    "freelancer": [["FREELANCER_OAUTH_TOKEN"]],
    # fiverr: no secrets required
}


def check_required() -> dict[str, list[str]]:
    """Return dict of server -> list of missing required var groups.

    A server is satisfied if ANY alternative group is fully present.
    """
    missing: dict[str, list[str]] = {}
    for server, alternatives in REQUIRED_VARS.items():
        # Server is OK if at least one alternative group is fully set
        satisfied = any(
            all(os.environ.get(v) for v in group)
            for group in alternatives
        )
        if not satisfied:
            # Report all vars from all alternatives as missing
            all_vars = [v for group in alternatives for v in group]
            missing[server] = all_vars
    return missing


def main() -> int:
    """CLI entry: load .env and print status / check required."""
    env_path = discover_env_file()
    check_mode = "--check" in sys.argv

    if env_path is None:
        print("[mcp-secrets] No .env file found.", file=sys.stderr)
        if check_mode:
            return 1
        return 0

    injected = load_env(env_path)
    print(f"[mcp-secrets] Loaded from: {env_path}")
    if injected:
        print(f"[mcp-secrets] Injected {len(injected)} var(s): {', '.join(injected.keys())}")
    else:
        print("[mcp-secrets] No new vars injected (all already set or placeholders).")

    if check_mode:
        missing = check_required()
        if missing:
            print("\n[mcp-secrets] MISSING required vars:", file=sys.stderr)
            for server, vars_list in missing.items():
                print(f"  {server}: {', '.join(vars_list)}", file=sys.stderr)
            return 1
        print("[mcp-secrets] All required vars present.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
