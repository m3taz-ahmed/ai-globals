#!/usr/bin/env python3
"""Wrapper script for the AI Global OS MCP server.

This replaces the inline Python one-liner in MCP config files.
Sets AGENT_OS_ROOT and launches the MCP server.
"""
import os
import pathlib
import subprocess
import sys


def discover_root() -> str:
    """Discover the AI Global OS root directory."""
    root = os.environ.get("AGENT_OS_ROOT")
    if root and pathlib.Path(root).is_dir():
        return root
    cwd = pathlib.Path.cwd()
    if (cwd / "config.py").exists():
        return str(cwd)
    return str(cwd)


def main() -> None:
    root = discover_root()
    os.environ["AGENT_OS_ROOT"] = root
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    subprocess.run([sys.executable, "-m", "aios_mcp.aios_server"], cwd=root)


if __name__ == "__main__":
    main()
