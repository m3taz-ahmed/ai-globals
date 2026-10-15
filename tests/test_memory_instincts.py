from __future__ import annotations

import json
from pathlib import Path

import pytest

from memory.instincts import (
    add_instinct,
    list_instincts,
    reinforce,
)


class TestAddInstinct:
    def test_add_returns_confidence_baseline(self, tmp_path: Path) -> None:
        res = add_instinct(tmp_path, "tests fail", "run the focused file")
        assert res["confidence"] == 0.3
        assert res["hits"] == 1
        assert res["scope"] == "project"

    def test_empty_trigger_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            add_instinct(tmp_path, "  ", "act")

    def test_dedup_same_pair(self, tmp_path: Path) -> None:
        a = add_instinct(tmp_path, "x", "y")
        b = add_instinct(tmp_path, "x", "y")
        assert a["id"] == b["id"]


class TestReinforce:
    def test_confidence_grows_with_hits(self, tmp_path: Path) -> None:
        res = add_instinct(tmp_path, "a", "b")
        r = reinforce(tmp_path, res["id"])
        assert r["hits"] == 2
        assert r["confidence"] == pytest.approx(0.45)

    def test_confidence_caps_at_max(self, tmp_path: Path) -> None:
        res = add_instinct(tmp_path, "a", "b")
        for _ in range(10):
            r = reinforce(tmp_path, res["id"])
        assert r["confidence"] == 0.9

    def test_missing_id_raises(self, tmp_path: Path) -> None:
        with pytest.raises(KeyError):
            reinforce(tmp_path, "mem_nope")

    def test_cross_project_observation_promotes(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
        res = add_instinct(tmp_path, "a", "b", project="proj-a")
        r = reinforce(tmp_path, res["id"], project="proj-b")
        assert r["promoted"] is True
        user_rows = list_instincts(tmp_path, scope="user")
        assert len(user_rows) == 1
        assert user_rows[0]["promoted_from"] == tmp_path.name


class TestList:
    def test_min_confidence_filter(self, tmp_path: Path) -> None:
        weak = add_instinct(tmp_path, "w", "x")
        strong = add_instinct(tmp_path, "s", "t")
        reinforce(tmp_path, strong["id"])
        rows = list_instincts(tmp_path, min_confidence=0.4)
        ids = [r["id"] for r in rows]
        assert strong["id"] in ids and weak["id"] not in ids

    def test_sorted_by_confidence(self, tmp_path: Path) -> None:
        add_instinct(tmp_path, "1", "1")
        b = add_instinct(tmp_path, "2", "2")
        reinforce(tmp_path, b["id"])
        rows = list_instincts(tmp_path)
        assert rows[0]["id"] == b["id"]


class TestMetaHelper:
    def test_malformed_meta_returns_empty(self) -> None:
        from types import SimpleNamespace

        from memory.instincts import _meta

        assert _meta(SimpleNamespace(meta="{not json")) == {}
        assert _meta(SimpleNamespace(meta=None)) == {}


class TestStoreUpdateMeta:
    def test_update_meta_resigns_row(self, tmp_path: Path) -> None:
        from memory.store import MemoryStore

        store = MemoryStore(tmp_path)
        mem = store.add("note", "content", meta={"a": 1})
        assert store.update_meta(mem.id, {"b": 2})
        fresh = store.get(mem.id)
        assert fresh is not None
        meta = json.loads(fresh.meta)
        assert meta == {"a": 1, "b": 2}
        assert fresh.integrity == "ok"

    def test_update_meta_strips_identity_keys(self, tmp_path: Path) -> None:
        from memory.store import MemoryStore

        store = MemoryStore(tmp_path)
        mem = store.add("note", "content")
        assert store.update_meta(mem.id, {"user_id": "evil", "ok": 1})
        meta = json.loads(store.get(mem.id).meta)
        assert "user_id" not in meta and meta["ok"] == 1

    def test_update_meta_missing_returns_false(self, tmp_path: Path) -> None:
        from memory.store import MemoryStore

        assert not MemoryStore(tmp_path).update_meta("mem_nope", {"a": 1})

    def test_update_meta_tombstoned_returns_false(self, tmp_path: Path) -> None:
        from memory.store import MemoryStore

        store = MemoryStore(tmp_path)
        mem = store.add("note", "content")
        store.soft_delete(mem.id)
        assert not store.update_meta(mem.id, {"a": 1})
