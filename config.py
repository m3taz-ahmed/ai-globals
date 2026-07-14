#!/usr/bin/env python3
"""AI Global OS configuration and root discovery."""

from __future__ import annotations

import os
from pathlib import Path


def discover_root() -> Path:
    """Discover AI Global OS root.

    Order:
    1. AGENT_OS_ROOT environment variable.
    2. The directory containing the current install (parent of config.py).
    """
    env_root = os.environ.get("AGENT_OS_ROOT")
    if env_root:
        path = Path(env_root)
        if path.is_dir():
            return path.resolve()
        raise ValueError(f"AGENT_OS_ROOT points to non-existent directory: {env_root}")
    return Path(__file__).resolve().parent
