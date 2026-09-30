"""P1.4: memory pin / soft-delete / restore / purge / contradiction strategies."""
from __future__ import annotations

from pathlib import Path

from memory.store import MemoryStore


def _store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(root=tmp_path, enable_vector=False)


def test_pin_unpin(tmp_path):
    s = _store(tmp_path)
    m = s.add("note", "keep me")
    assert s.pin(m.id)
    g = s.get(m.id)
    assert g is not None and g.pinned is True
    s.unpin(m.id)
    g = s.get(m.id)
    assert g is not None and g.pinned is False


def test_pinned_sorts_first(tmp_path):
    s = _store(tmp_path)
    s.add("note", "first added")
    p = s.add("note", "pinned later")
    s.pin(p.id)
    assert s.list_all()[0].id == p.id
    assert s.list_pinned()[0].id == p.id


def test_soft_delete_hides_from_reads(tmp_path):
    s = _store(tmp_path)
    m = s.add("note", "temporary fact")
    assert s.soft_delete(m.id)
    assert s.get(m.id) is None
    assert s.get(m.id, include_deleted=True) is not None
    assert s.list_all() == []
    assert s.count() == 0 and s.count(include_deleted=True) == 1
    assert s.search("temporary") == []


def test_soft_delete_refuses_pinned(tmp_path):
    s = _store(tmp_path)
    m = s.add("note", "pinned fact")
    s.pin(m.id)
    assert s.soft_delete(m.id) is False


def test_restore_resurrects(tmp_path):
    s = _store(tmp_path)
    m = s.add("note", "restore me")
    s.soft_delete(m.id)
    assert s.restore(m.id)
    g = s.get(m.id)
    assert g is not None and g.deleted_at is None


def test_add_resurrects_tombstoned(tmp_path):
    s = _store(tmp_path)
    m = s.add("note", "same content")
    s.soft_delete(m.id)
    again = s.add("note", "same content")
    assert again.id == m.id
    assert s.get(m.id) is not None


def test_purge_deleted(tmp_path):
    s = _store(tmp_path)
    a = s.add("note", "delete me")
    b = s.add("note", "keep me")
    s.soft_delete(a.id)
    assert s.purge_deleted() == 1
    assert s.get(a.id, include_deleted=True) is None
    assert s.get(b.id) is not None


def test_contradiction_latest_wins(tmp_path):
    s = _store(tmp_path)
    old = s.add("fact", "sky is green", meta={"subject": "sky"})
    import time
    time.sleep(0.01)
    new = s.add("fact", "sky is blue", meta={"subject": "sky"})
    groups = s.detect_contradictions()
    assert len(groups) == 1 and set(groups[0]) == {old.id, new.id}
    winner = s.resolve_contradictions(groups[0], strategy="latest_wins")
    assert winner is not None and winner.id == new.id
    assert s.get(old.id) is None  # soft-deleted
    assert s.get(old.id, include_deleted=True) is not None  # recoverable


def test_contradiction_confidence(tmp_path):
    s = _store(tmp_path)
    low = s.add("fact", "v1", meta={"subject": "k", "confidence": 0.2})
    high = s.add("fact", "v2", meta={"subject": "k", "confidence": 0.9})
    winner = s.resolve_contradictions([low.id, high.id], strategy="confidence")
    assert winner is not None and winner.id == high.id


def test_contradiction_source_priority(tmp_path):
    s = _store(tmp_path)
    a = s.add("fact", "v_a", source="untrusted-feed", meta={"subject": "s"})
    b = s.add("fact", "v_b", source="manual-entry", meta={"subject": "s"})
    winner = s.resolve_contradictions(
        [a.id, b.id], strategy="source_priority",
        source_priority=["manual-entry", "untrusted-feed"],
    )
    assert winner is not None and winner.id == b.id


def test_contradiction_merge(tmp_path):
    s = _store(tmp_path)
    a = s.add("fact", "line one\nshared line", meta={"subject": "m"})
    b = s.add("fact", "line two\nshared line", meta={"subject": "m"})
    winner = s.resolve_contradictions([a.id, b.id], strategy="merge")
    assert winner is not None
    assert "line one" in winner.content and "line two" in winner.content
    assert winner.content.count("shared line") == 1
    assert s.get(a.id) is None and s.get(b.id) is None
