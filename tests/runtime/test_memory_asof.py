"""Tests for bi-temporal as_of queries (P2.3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from memory.store import MemoryStore


def _store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path, enable_vector=False)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _set_ts(store: MemoryStore, mem_id: str, created_at: str, deleted_at: str | None = None) -> None:
    with store._conn() as conn:
        conn.execute(
            "UPDATE memories SET created_at = ?, valid_from = ?, deleted_at = ? WHERE id = ?",
            (created_at, created_at, deleted_at, mem_id),
        )


T0 = "2020-01-01T00:00:00+00:00"
T1 = "2020-01-02T00:00:00+00:00"
T2 = "2020-01-03T00:00:00+00:00"


def test_as_of_returns_entries_written_before_cutoff(tmp_path: Path) -> None:
    s = _store(tmp_path)
    m1 = s.add("fact", "first entry", "test")
    m2 = s.add("fact", "second entry", "test")
    _set_ts(s, m1.id, T0)
    _set_ts(s, m2.id, T2)
    ids = {m.id for m in s.as_of(as_of=T1)}
    assert ids == {m1.id}


def test_as_of_respects_soft_delete_tombstone_time(tmp_path: Path) -> None:
    s = _store(tmp_path)
    m = s.add("fact", "doomed entry", "test")
    s.soft_delete(m.id)
    _set_ts(s, m.id, T0, deleted_at=T2)
    # Tombstone at T2: alive at T1, gone at T2+.
    assert m.id in {x.id for x in s.as_of(as_of=T1)}
    assert m.id not in {x.id for x in s.as_of(as_of=T2)}


def test_valid_at_filters_temporal_validity(tmp_path: Path) -> None:
    s = _store(tmp_path)
    past = _iso(datetime.now(timezone.utc) - timedelta(days=10))
    future = _iso(datetime.now(timezone.utc) + timedelta(days=10))
    m_old = s.add("fact", "expired", "test", valid_to=past)
    m_live = s.add("fact", "live", "test", valid_to=future)
    now = _iso(datetime.now(timezone.utc))
    ids = {x.id for x in s.as_of(valid_at=now)}
    assert m_live.id in ids
    assert m_old.id not in ids


def test_as_of_and_valid_at_combine(tmp_path: Path) -> None:
    s = _store(tmp_path)
    m = s.add("fact", "scoped", "test")
    _set_ts(s, m.id, T0)
    m2 = s.add("fact", "later", "test")
    _set_ts(s, m2.id, T2)
    ids = {x.id for x in s.as_of(as_of=T1, valid_at=T1)}
    assert ids == {m.id}


def test_as_of_no_args_matches_live_view(tmp_path: Path) -> None:
    s = _store(tmp_path)
    m = s.add("fact", "plain", "test")
    ids = {x.id for x in s.as_of()}
    assert m.id in ids
