#!/usr/bin/env python3
"""Shared helpers for MCP tool modules."""

from __future__ import annotations

import re
import threading
from pathlib import Path

import config
from memory.store import MemoryStore
from runtime.kernel import Kernel

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")

_kernel_instance: Kernel | None = None
_memory_instance: MemoryStore | None = None
_current_root: Path | None = None
_kernel_lock = threading.Lock()
_memory_lock = threading.Lock()

_MAX_RESULTS = 100
_MAX_INPUT_LENGTH = 100_000


def root() -> Path:
    """Discover root each call to react to env changes."""
    return config.discover_root()


def reset_state() -> None:
    """Reset cached kernel and memory instances. Useful for tests and env changes."""
    global _kernel_instance, _memory_instance, _current_root
    _kernel_instance = None
    _memory_instance = None
    _current_root = None


def kernel() -> Kernel:
    """Return a Kernel instance, recreating if the discovered root changes."""
    global _kernel_instance, _current_root
    with _kernel_lock:
        discovered = root()
        if _kernel_instance is None or _current_root != discovered:
            _current_root = discovered
            _kernel_instance = Kernel(_current_root)
        return _kernel_instance


def memory() -> MemoryStore:
    """Return a MemoryStore instance tied to the discovered root."""
    global _memory_instance
    with _memory_lock:
        discovered = root()
        if _memory_instance is None or _memory_instance.root != discovered:
            _memory_instance = MemoryStore(discovered)
        return _memory_instance


def is_safe_name(name: str) -> bool:
    """Reject path separators, parent-directory references, control chars, and overlong names."""
    if not name or ".." in name or "/" in name or "\\" in name or len(name) > 128:
        return False
    if any(ord(c) < 32 or c == "\x7f" for c in name):
        return False
    return bool(_NAME_RE.fullmatch(name))


def resolve_path(root_path: Path, relative: Path) -> Path | None:
    """Resolve a relative path and ensure it stays under root."""
    if ".." in relative.parts:
        return None
    if str(relative).startswith("\\\\") or str(relative).startswith("//"):
        return None
    try:
        target = (root_path / relative).resolve(strict=False)
        root_resolved = root_path.resolve()
        target.relative_to(root_resolved)
    except (ValueError, OSError, RuntimeError):
        return None
    return target


def truncate(content: str, limit: int = 500) -> str:
    return content if len(content) <= limit else content[:limit] + "..."


def validate_query(query: str) -> str | None:
    """Return an error JSON string if query is invalid, None if valid."""
    import json

    if not isinstance(query, str) or not query or len(query) > _MAX_INPUT_LENGTH:
        return json.dumps({"ok": False, "error": "Invalid query"})
    return None


def validate_kind(kind: str | None) -> str | None:
    """Return an error JSON string if kind is invalid, None if valid."""
    import json

    if kind is not None and not is_safe_name(kind):
        return json.dumps({"ok": False, "error": "Invalid kind"})
    return None
