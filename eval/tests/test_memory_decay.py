"""Eval integration test: memory_decay table exists at init and decay lifecycle works.

Verifies that the schema contract fix (memory_decay created in _init_schema, not
lazily) holds end-to-end through the eval pipeline. This catches regressions where
the decay table might be moved back to lazy-only creation.
"""

from __future__ import annotations

from pathlib import Path

from memory.schema_contract import verify_schema_integrity
from memory.store import MemoryStore


def test_memory_decay_table_exists_at_init(tmp_path: Path) -> None:
    """The memory_decay table must exist immediately after init, not after first access."""
    store = MemoryStore(tmp_path, enable_vector=False)
    is_valid, drift = verify_schema_integrity(store.db_path)
    assert is_valid, f"Schema drift after init: {drift}"
    # No warning should be logged — verify_schema_integrity returns (True, None).
    assert drift is None


def test_decay_lifecycle_through_eval(tmp_path: Path) -> None:
    """Full decay lifecycle: add → record_access → apply_decay → get_decay_score."""
    store = MemoryStore(tmp_path, enable_vector=False)
    m = store.add(kind="factual", content="aiZee enforces policy gates on all actions")
    assert m.id is not None

    # Initial decay score should be 1.0 (full freshness).
    score0 = store.get_decay_score(m.id)
    assert score0 == 1.0

    # Record accesses → score stays at 1.0 (access doesn't increase beyond max).
    store.record_access(m.id)
    store.record_access(m.id)
    score1 = store.get_decay_score(m.id)
    assert score1 == 1.0

    # Apply decay → score should decrease.
    updated = store.apply_decay(decay_rate=0.5)
    assert updated >= 1
    score2 = store.get_decay_score(m.id)
    assert score2 < 1.0, f"Score should decrease after decay, got {score2}"

    # Re-access after decay → score should recover toward 1.0.
    store.record_access(m.id)
    score3 = store.get_decay_score(m.id)
    assert score3 >= score2, f"Score should recover after access, got {score3} < {score2}"


def test_decay_persistence_across_restarts(tmp_path: Path) -> None:
    """Decay state persists across MemoryStore re-instantiation."""
    store1 = MemoryStore(tmp_path, enable_vector=False)
    m = store1.add(kind="factual", content="persistence test for decay")
    store1.record_access(m.id)
    store1.apply_decay(decay_rate=0.3)
    score1 = store1.get_decay_score(m.id)

    # Re-open the same DB.
    store2 = MemoryStore(tmp_path, enable_vector=False)
    score2 = store2.get_decay_score(m.id)
    assert score1 == score2, f"Decay score not persisted: {score1} != {score2}"
