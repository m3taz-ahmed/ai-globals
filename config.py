#!/usr/bin/env python3
"""AI Global OS configuration and root discovery."""

from __future__ import annotations

import os
import re
from pathlib import Path


def discover_root() -> Path:
    """Discover AI Global OS root.

    Order:
    1. AGENT_OS_ROOT environment variable.
    2. The directory containing the current install (parent of config.py).
    """
    return _resolve_env_dir("AGENT_OS_ROOT", Path(__file__).resolve().parent)


def discover_project_root() -> Path:
    """Discover active project root.

    Order:
    1. AGENT_PROJECT_ROOT environment variable.
    2. AGENT_OS_ROOT environment variable.
    3. Current working directory if it contains `.ai/active-context.md`.
    4. The directory containing the current install (parent of config.py).
    """
    project_env = os.environ.get("AGENT_PROJECT_ROOT")
    if project_env:
        return _resolve_env_dir("AGENT_PROJECT_ROOT", discover_root())
    os_env = os.environ.get("AGENT_OS_ROOT")
    if os_env:
        return _resolve_env_dir("AGENT_OS_ROOT", discover_root())
    cwd = Path.cwd()
    if (cwd / ".ai" / "active-context.md").exists():
        return cwd.resolve()
    return discover_root()


def _resolve_env_dir(env_var: str, fallback: Path) -> Path:
    env_root = os.environ.get(env_var)
    if env_root:
        path = Path(env_root)
        if path.is_dir():
            return path.resolve()
        raise ValueError(f"{env_var} points to non-existent directory: {env_root}")
    return fallback


def _version() -> str:
    pyproject = Path(__file__).resolve().parent / "pyproject.toml"
    if pyproject.exists():
        match = re.search(r'^version\s*=\s*"([^"\n]+)"', pyproject.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            return match.group(1)
    return "4.21.0"


VERSION: str = _version()
