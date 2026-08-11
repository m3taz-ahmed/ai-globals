"""Shared pytest fixtures and auto-marking for AI Global OS test suite."""

import shutil
import tempfile
from pathlib import Path

import pytest

from memory.store import MemoryStore
from runtime.kernel import Kernel

# ---------------------------------------------------------------------------
# Auto-mark slow tests based on file path
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-mark tests as slow/fast based on their file path.

    - tests/mcp/ → marked as 'mcp' (slow: spins up MCP server)
    - tests/dashboard/ → marked as 'dashboard' (slow: starts server)
    - tests/e2e/ → marked as 'slow' (end-to-end)
    - memory/tests/test_vector.py → marked as 'vector' (slow: loads model)
    - Everything else → marked as 'fast'
    """
    slow_markers = {
        "tests/mcp/": "mcp",
        "tests/dashboard/": "dashboard",
        "tests/e2e/": "slow",
        "memory/tests/test_vector.py": "vector",
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_root():
    path = Path(tempfile.mkdtemp(prefix="aios_test_"))
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def kernel(tmp_root):
    # Copy minimal structure for tests
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
def store(tmp_root):
    return MemoryStore(tmp_root, db_path=tmp_root / "brain" / "memory.db", enable_vector=False)
