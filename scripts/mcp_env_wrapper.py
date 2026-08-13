#!/usr/bin/env python3
"""Generic env-loading wrapper for external MCP servers.

Reads ``.env`` from the AI Global OS root, injects secrets into the
environment, then ``exec``s the original MCP server command. This makes
Devin-managed MCP servers (defined in ``.devin/mcp_config.json``) pick
up centralized secrets without relying on OS-level env vars.

Usage in mcp_config.json:
    {
      "command": "python",
      "args": ["scripts/mcp_env_wrapper.py", "npx", "-y", "@pkg/mcp@1.0"],
      "env": { ...optional... }
    }

The first arg after the wrapper script is the real command; remaining
args are passed through. Environment from ``.env`` + ``mcp_config.json``
env block are merged (config takes precedence).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _discover_root() -> Path:
    root = os.environ.get("AGENT_OS_ROOT")
    if root and Path(root).is_dir():
        return Path(root)
    return Path(__file__).resolve().parent.parent


def _load_env(root: Path) -> None:
    env_file = root / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:]
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if not key or value.startswith("your_"):
            continue
        os.environ.setdefault(key, value)


def main() -> int:
    root = _discover_root()
    os.environ["AGENT_OS_ROOT"] = str(root)
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    _load_env(root)

    # Args after script name: [real_command, arg1, arg2, ...]
    remaining = sys.argv[1:]
    if not remaining:
        print("[mcp-env-wrapper] No command specified", file=sys.stderr)
        return 1

    cmd = remaining[0]
    args = remaining[1:]

    # Resolve relative commands via PATH (augment with user script dirs)
    if not os.path.isabs(cmd):
        import shutil
        import sysconfig
        extra_dirs: list[str] = []
        scheme = "nt_user" if os.name == "nt" else "posix_user"
        scripts_dir = sysconfig.get_path("scripts", scheme)
        if scripts_dir:
            extra_dirs.append(scripts_dir)
        userbase = sysconfig.get_config_var("userbase")
        if userbase:
            for child in ("Scripts", "bin"):
                d = str(Path(userbase) / child)
                if d not in extra_dirs and Path(d).is_dir():
                    extra_dirs.append(d)
        search_path = os.pathsep.join([*extra_dirs, os.environ.get("PATH", "")])
        resolved = shutil.which(cmd, path=search_path)
        if resolved:
            cmd = resolved

    # Launch the real MCP server.
    # On POSIX, os.execvpe replaces this process (no extra layer).
    # On Windows, os.execvpe does NOT reliably inherit the parent's
    # stdin/stdout pipe handles when the MCP client talks over stdio,
    # which silently breaks the JSON-RPC stream (server starts, reads
    # nothing, exits 1). Fall back to subprocess with inherited handles.
    if os.name == "posix":
        os.execvpe(cmd, [cmd, *args], os.environ)
        return 0  # unreachable

    import subprocess

    proc = subprocess.run([cmd, *args], env=os.environ)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
