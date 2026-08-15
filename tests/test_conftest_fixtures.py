"""Tests that exercise the conftest.py fixtures (tmp_root, kernel, store).

These tests exist to achieve 100% coverage on the fixture lines in conftest.py:
- Lines 51-53: tmp_root fixture (mkdtemp, yield, rmtree)
- Lines 59-69: kernel fixture (mkdir, write_text, Kernel init)
- Line 74: store fixture (MemoryStore init)
"""

from __future__ import annotations

from pathlib import Path

from memory.store import MemoryStore
from runtime.kernel import Kernel


def test_tmp_root_fixture(tmp_root: Path) -> None:
    """Exercise the tmp_root fixture (conftest lines 51-53)."""
    assert tmp_root.exists()
    assert tmp_root.is_dir()
    # Write a file to verify the directory is writable
    (tmp_root / "test.txt").write_text("hello", encoding="utf-8")
    assert (tmp_root / "test.txt").read_text(encoding="utf-8") == "hello"


def test_kernel_fixture(kernel: Kernel) -> None:
    """Exercise the kernel fixture (conftest lines 59-69)."""
    assert kernel is not None
    status = kernel.status()
    assert "version" in status
    assert "personas" in status
    # Verify the policies file was created
    assert (kernel.root / "runtime" / "policies" / "default.yaml").exists()
    # Verify the workflow file was created
    assert (kernel.root / "workflows" / "test.md").exists()


def test_store_fixture(store: MemoryStore) -> None:
    """Exercise the store fixture (conftest line 74)."""
    assert store is not None
    # Add a memory and verify it can be retrieved
    mem = store.add(kind="semantic", content="test content", source="test")
    assert mem.id is not None
    results = store.search("test", limit=10)
    assert len(results) > 0


def test_all_fixtures_together(tmp_root: Path, kernel: Kernel, store: MemoryStore) -> None:
    """Exercise all three fixtures together."""
    assert tmp_root.exists()
    assert kernel.root == tmp_root
    # Store should be using the same tmp_root
    mem = store.add(kind="episodic", content="combined test", source="test")
    assert mem is not None
