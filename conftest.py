"""Root conftest.py - shared pytest fixtures and auto-marking for the entire aiZee test suite.

This file lives at the repository root and is automatically discovered by
pytest for **all** of the unified test tree (tests/, including the layer
subdirs tests/{runtime,memory,eval,aizee_mcp}/ consolidated in v6.1.0).
The per-directory conftest.py duplicates have been removed
in favour of this single source of truth (P3.3 / I12-Q4).
"""

from __future__ import annotations

import gc
import itertools
import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

# Hermeticity pin (C2 / P0.1): the test suite must always resolve the aiZee
# root to THIS repository, never the ambient AIZEE_ROOT env var (which in a
# deployed setup points at the read-only mirror). Subsystems that read
# AIZEE_ROOT directly (crypto keys, plugin discovery, dashboard token) follow
# this pin as well. Set before any project imports so module-level reads see
# the pinned value.
os.environ["AIZEE_ROOT"] = str(Path(__file__).resolve().parent)

from memory.store import MemoryStore
from runtime.kernel import Kernel

# Boot-phase GC window: collection allocates almost exclusively permanent
# objects, so automatic cyclic sweeps during boot only add pauses. GC stays
# off until pytest_collection_modifyitems, where survivors are frozen into
# the permanent generation and GC resumes with sparse thresholds.
gc.disable()

# ---------------------------------------------------------------------------
# Auto-mark slow tests based on file path
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-mark tests as slow/fast based on their file path.

    - tests/mcp/            -> marked as 'mcp'       (slow: spins up MCP server)
    - tests/dashboard/      -> marked as 'dashboard' (slow: starts server)
    - tests/e2e/            -> marked as 'slow'      (end-to-end)
    - tests/memory/test_vector.py -> marked as 'vector' (slow: loads model)
    - Everything else       -> marked as 'fast'
    """
    slow_markers = {
        "tests/mcp/": "mcp",
        "tests/dashboard/": "dashboard",
        "tests/e2e/": "slow",
        "tests/memory/test_vector.py": "vector",
    }

    for item in items:
        item_path = str(item.fspath).replace("\\", "/")
        marked_slow = False
        for path_prefix, marker_name in slow_markers.items():
            if path_prefix in item_path:
                item.add_marker(pytest.mark.__getattr__(marker_name))
                item.add_marker(pytest.mark.slow)
                marked_slow = True
                break
        if not marked_slow:
            item.add_marker(pytest.mark.fast)

    # End of the boot GC window: freeze survivors so the collector never
    # rescans them, then resume with sparse thresholds. The deliberate lack of
    # a pre-freeze collect freezes a small amount of boot garbage (~MBs) but
    # saves a full sweep (~0.1s+ on this heap) per invocation.
    gc.freeze()
    gc.set_threshold(50_000, 20, 20)
    gc.enable()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_root() -> Iterator[Path]:
    """Yield a fresh temporary directory, cleaned up after the test."""
    path = Path(tempfile.mkdtemp(prefix="aizee_test_"))
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def kernel(tmp_root: Path) -> Kernel:
    """Return a Kernel backed by a minimal tmp_root directory structure."""
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_root / sub).mkdir(parents=True, exist_ok=True)
    (tmp_root / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
        "  - name: deny-destructive\n    condition: \"'rm -rf' in command\"\n    action: deny\n"
    )
    (tmp_root / "workflows/test.md").write_text(
        "[WORKFLOW] test\n[OBJ] Test workflow for unit tests.\n[RULES]\n1. [REQ] Step one.\n2. [CMD] Step two.\n"
    )
    return Kernel(tmp_root)


@pytest.fixture
def store(tmp_root: Path) -> MemoryStore:
    """Return a MemoryStore backed by a SQLite DB inside tmp_root."""
    return MemoryStore(tmp_root, db_path=tmp_root / "brain" / "memory.db", enable_vector=False)


# ---------------------------------------------------------------------------
# Global cleanup - close leaked SQLite connections after each test
# ---------------------------------------------------------------------------


_gc_sweep_tick = itertools.count(1)


@pytest.fixture(autouse=True)
def _close_sqlite_connections() -> Iterator[None]:
    """Periodically force-close leaked SQLite connections after tests.

    Prevents ``ResourceWarning: unclosed database`` warnings that occur
    when tests create ``MemoryStore`` / ``SqliteStorage`` instances without
    explicit cleanup. A full ``gc.collect()`` after every test costs ~0.1s on
    this suite's heap (~11 min across the fast tier); cyclic garbage — the
    only thing refcounting misses — accumulates safely between sweeps, so
    collect every 64 tests instead.
    """
    yield
    if next(_gc_sweep_tick) % 64 == 0:
        gc.collect()


# ---------------------------------------------------------------------------
# Mock time.sleep for fast tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_time_sleep(request: pytest.FixtureRequest) -> Iterator[None]:
    """Replace ``time.sleep()`` with a no-op for fast tests.

    Slow/integration tests (marked with ``@pytest.mark.slow`` or
    ``@pytest.mark.integration``) keep real sleep.  This prevents flaky
    timing-dependent tests and speeds up the fast tier.
    """
    if request.node.get_closest_marker("slow") or request.node.get_closest_marker("integration"):
        yield
        return
    import time as _time

    original_sleep = _time.sleep
    _time.sleep = lambda _seconds: None
    try:
        yield
    finally:
        _time.sleep = original_sleep
