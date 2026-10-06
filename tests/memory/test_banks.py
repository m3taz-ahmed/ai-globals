"""Tests for memory banks (namespaces) + reflect — hindsight adoption."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from memory.store import MemoryStore


def _store(tmp: Path) -> MemoryStore:
    return MemoryStore(tmp, tmp / "memory.db", enable_vector=False)


@pytest.fixture()
def store() -> MemoryStore:
    # mkdtemp (no rmtree teardown): the open SQLite handle can't be deleted
    # on Windows; same convention as tests/memory/test_store.py.
    return _store(Path(tempfile.mkdtemp(prefix="aizee_banks_")))


def test_add_defaults_to_global_bank(store: MemoryStore) -> None:
    mem = store.add("factual", "the sky is blue and the grass is green")
    assert mem.bank == "global"


def test_add_with_named_bank_roundtrip(store: MemoryStore) -> None:
    mem = store.add("semantic", "project alpha uses Postgres", bank="alpha")
    assert mem.bank == "alpha"
    fetched = store.get(mem.id)
    assert fetched is not None
    assert fetched.bank == "alpha"


def test_same_content_in_different_banks_is_distinct(store: MemoryStore) -> None:
    a = store.add("factual", "deployment requires a manual approval gate")
    b = store.add("factual", "deployment requires a manual approval gate", bank="beta")
    assert a.id != b.id
    assert a.bank == "global"
    assert b.bank == "beta"


def test_search_scoped_to_bank(store: MemoryStore) -> None:
    store.add("factual", "caching layer uses Redis for sessions", bank="alpha")
    store.add("factual", "caching layer uses Memcached for sessions", bank="beta")
    alpha_hits = store.search("caching sessions", bank="alpha")
    assert len(alpha_hits) == 1
    assert alpha_hits[0].bank == "alpha"
    all_hits = store.search("caching sessions")
    assert {m.bank for m in all_hits} == {"alpha", "beta"}


def test_list_all_scoped_to_bank(store: MemoryStore) -> None:
    store.add("factual", "entry one", bank="alpha")
    store.add("factual", "entry two", bank="beta")
    store.add("factual", "entry three")
    alpha = store.list_all(bank="alpha")
    assert len(alpha) == 1
    assert alpha[0].bank == "alpha"
    assert len(store.list_all()) == 3


def test_count_scoped_to_bank(store: MemoryStore) -> None:
    store.add("factual", "one", bank="alpha")
    store.add("factual", "two", bank="alpha")
    store.add("factual", "three")
    assert store.count(bank="alpha") == 2
    assert store.count() == 3


def test_search_as_of_scoped_to_bank(store: MemoryStore) -> None:
    store.add("factual", "in alpha", bank="alpha")
    store.add("factual", "in beta", bank="beta")
    hits = store.as_of(bank="alpha")
    assert [m.bank for m in hits] == ["alpha"]


def test_search_temporal_scoped_to_bank(store: MemoryStore) -> None:
    store.add("factual", "alpha fact", bank="alpha")
    store.add("factual", "beta fact", bank="beta")
    hits = store.search_temporal("2000-01-01", "2999-01-01", bank="beta")
    assert [m.bank for m in hits] == ["beta"]


def test_search_safe_scoped_to_bank(store: MemoryStore) -> None:
    store.add("factual", "alpha passwords rotate monthly", bank="alpha")
    store.add("factual", "beta passwords never rotate", bank="beta")
    hits = store.search_safe("passwords rotate", bank="beta")
    assert len(hits) == 1
    assert hits[0].bank == "beta"


def test_banks_listing(store: MemoryStore) -> None:
    store.add("factual", "a1", bank="alpha")
    store.add("factual", "a2", bank="alpha")
    store.add("factual", "g1")
    banks = store.banks()
    assert banks == {"alpha": 2, "global": 1}


def test_banks_exclude_soft_deleted(store: MemoryStore) -> None:
    mem = store.add("factual", "doomed entry", bank="alpha")
    store.soft_delete(mem.id)
    assert store.banks() == {}


def test_reflect_extractive_fallback(store: MemoryStore) -> None:
    store.add("factual", "the API requires an OAuth bearer token")
    store.add("factual", "rate limits are 100 requests per minute")
    result = store.reflect("API authentication")
    assert result.answer
    assert not result.synthesized
    assert len(result.supporting) >= 1


def test_reflect_scoped_to_bank(store: MemoryStore) -> None:
    store.add("factual", "alpha deploys on Fridays only", bank="alpha")
    store.add("factual", "beta deploys continuously", bank="beta")
    result = store.reflect("deployment schedule", bank="alpha")
    assert result.bank == "alpha"
    assert all(m.bank == "alpha" for m in result.supporting)


def test_reflect_empty_store(store: MemoryStore) -> None:
    result = store.reflect("anything at all")
    assert result.answer == ""
    assert result.supporting == []


def test_reflect_with_llm_fn(store: MemoryStore) -> None:
    store.add("factual", "the build pipeline runs in GitHub Actions")
    calls: list[str] = []

    def fake_llm(prompt: str) -> str:
        calls.append(prompt)
        return "synthesized answer"

    result = store.reflect("build pipeline", llm_fn=fake_llm)
    assert result.synthesized
    assert result.answer == "synthesized answer"
    assert calls and "GitHub Actions" in calls[0]


def test_reflect_dedupes_supporting(store: MemoryStore) -> None:
    mem = store.add("factual", "unique fact for dedup check")
    result = store.reflect("dedup check", limit=5)
    contents = [m.content for m in result.supporting]
    assert contents == list(dict.fromkeys(contents))
    assert mem.id in {m.id for m in result.supporting}


def test_list_all_include_deleted_with_bank(store: MemoryStore) -> None:
    mem = store.add("factual", "tombstoned alpha fact", bank="alpha")
    store.soft_delete(mem.id)
    assert store.list_all(bank="alpha") == []
    gone = store.list_all(bank="alpha", include_deleted=True)
    assert [m.id for m in gone] == [mem.id]


def test_reflect_skips_exact_duplicates(store: MemoryStore) -> None:
    import json
    import uuid
    from datetime import datetime, timezone

    from memory.store import Memory

    now = datetime.now(timezone.utc).isoformat()
    dup_content = "the cache TTL is 300 seconds everywhere"
    mems = [
        Memory(
            id=f"mem_{uuid.uuid4().hex[:12]}",
            kind="factual",
            content=dup_content,
            source="t",
            meta=json.dumps({}),
            created_at=now,
            valid_from=now,
            valid_to=None,
        )
        for _ in range(2)
    ]
    store.add_batch(mems)
    result = store.reflect("cache TTL", limit=5)
    assert len([m for m in result.supporting if m.content == dup_content]) == 1


def test_bank_column_migration_on_old_db(tmp_path: Path) -> None:
    """Old DBs without the bank column migrate additively and read 'global'."""
    import sqlite3

    db = tmp_path / "memory.db"
    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE memories (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, content TEXT NOT NULL,
            source TEXT, meta TEXT, created_at TEXT NOT NULL,
            valid_from TEXT NOT NULL, valid_to TEXT, integrity_sig TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO memories (id, kind, content, created_at, valid_from) "
        "VALUES ('mem_old', 'factual', 'legacy row', '2020-01-01', '2020-01-01')"
    )
    conn.commit()
    conn.close()

    store = MemoryStore(tmp_path, db, enable_vector=False)
    legacy = store.get("mem_old")
    assert legacy is not None
    assert legacy.bank == "global"
    with store._conn() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(memories)")}
    assert "bank" in cols
