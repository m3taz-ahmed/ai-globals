"""Comprehensive tests for memory/store.py."""

from __future__ import annotations

import json
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

from memory.store import Memory, MemoryStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _store(tmp: Path, enable_vector: bool = False) -> MemoryStore:
    return MemoryStore(tmp, tmp / "memory.db", enable_vector=enable_vector)


def _tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="aios_store_"))


def _mem(kind: str = "factual", content: str = "test", source: str = "") -> Memory:
    now = datetime.now(timezone.utc).isoformat()
    return Memory(
        id=str(uuid.uuid4()),
        kind=kind,
        content=content,
        source=source,
        meta=json.dumps({}),
        created_at=now,
        valid_from=now,
        valid_to=None,
    )


# ---------------------------------------------------------------------------
# add / add_batch / get
# ---------------------------------------------------------------------------

class TestAddAndGet:
    def test_add_and_get(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            m = store.add("factual", "Laravel uses Eloquent ORM", source="tech-stack/laravel-11.md")
            assert m.kind == "factual"
            fetched = store.get(m.id)
            assert fetched is not None
            assert fetched.content == "Laravel uses Eloquent ORM"
            assert fetched.source == "tech-stack/laravel-11.md"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_get_nonexistent_returns_none(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            assert store.get("00000000-0000-0000-0000-000000000000") is None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_add_batch_empty_returns_empty(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            assert store.add_batch([]) == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_add_batch_multiple(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            mems = [_mem(content=f"item {i}", source=f"src{i}") for i in range(5)]
            result = store.add_batch(mems)
            assert len(result) == 5
            for m in result:
                assert store.get(m.id) is not None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_add_with_valid_to(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            m = store.add("episodic", "temp", valid_to="2000-01-01T00:00:00+00:00")
            fetched = store.get(m.id)
            assert fetched is not None
            assert fetched.valid_to == "2000-01-01T00:00:00+00:00"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_add_with_meta(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            m = store.add("factual", "content", meta={"key": "value"})
            fetched = store.get(m.id)
            assert fetched is not None
            assert json.loads(fetched.meta)["key"] == "value"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# search (FTS)
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_fts_match(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            store.add("factual", "Laravel uses Eloquent ORM")
            assert len(store.search("Eloquent")) == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_fts_no_match(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            store.add("factual", "Laravel uses Eloquent ORM")
            assert len(store.search("Django")) == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_with_kind_filter(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            store.add("factual", "Python is great")
            store.add("semantic", "Python is great too")
            results = store.search("Python", kind="factual")
            assert all(m.kind == "factual" for m in results)
            assert len(results) == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_excludes_invalidated(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            m = store.add("factual", "Outdated content about PHP")
            store.invalidate(m.id)
            assert len(store.search("PHP")) == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_percent_wildcard_not_injected(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            store.add("factual", "hello world")
            assert len(store.search("%")) == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_empty_query_returns_empty(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            store.add("factual", "some content")
            assert store.search("") == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# relate / related
# ---------------------------------------------------------------------------

class TestRelations:
    def test_relate_and_related(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            a = store.add("factual", "User model")
            b = store.add("factual", "Post model")
            store.relate(a.id, b.id, "has_many")
            rels = store.related(a.id)
            assert len(rels) == 1
            assert rels[0][1] == "has_many"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_related_with_specific_relation(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            a = store.add("factual", "A")
            b = store.add("factual", "B")
            c = store.add("factual", "C")
            store.relate(a.id, b.id, "has_many")
            store.relate(a.id, c.id, "belongs_to")
            rels = store.related(a.id, relation="has_many")
            assert len(rels) == 1
            assert rels[0][0].content == "B"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_related_no_relations_returns_empty(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            a = store.add("factual", "Lonely node")
            assert store.related(a.id) == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# delete / invalidate
# ---------------------------------------------------------------------------

class TestDeleteAndInvalidate:
    def test_delete_by_source(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            m = store.add("factual", "to delete", source="rules/delete-me.md")
            assert store.get(m.id) is not None
            store.delete_by_source("rules/delete-me.md")
            assert store.get(m.id) is None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_delete_by_source_batch_single_query(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            m1 = store.add("factual", "item1", source="src1")
            m2 = store.add("factual", "item2", source="src2")
            m3 = store.add("factual", "item3", source="src3")
            deleted = store.delete_by_source_batch(["src1", "src2"])
            assert len(deleted) == 2
            assert store.get(m1.id) is None
            assert store.get(m2.id) is None
            assert store.get(m3.id) is not None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_delete_by_source_batch_cleans_relations(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            a = store.add("factual", "A", source="src-a")
            b = store.add("factual", "B", source="src-b")
            store.relate(a.id, b.id, "references")
            store.delete_by_source_batch(["src-a"])
            assert store.related(b.id) == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_delete_by_source_batch_empty_sources(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            assert store.delete_by_source_batch([]) == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_delete_by_source_batch_calls_vector_remove_batch(self):
        """Cover line 282: vector.remove_batch is called when vector is available."""
        tmp = _tmp()
        try:
            store = _store(tmp)
            mock_vector = MagicMock()
            mock_vector.is_available.return_value = True
            store.vector = mock_vector
            m = store.add("factual", "content to batch-delete", source="src-batch")
            deleted = store.delete_by_source_batch(["src-batch"])
            assert len(deleted) == 1
            mock_vector.remove_batch.assert_called_once_with([m.id])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_invalidate_sets_valid_to(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            m = store.add("factual", "valid content")
            store.invalidate(m.id)
            fetched = store.get(m.id)
            assert fetched is not None
            assert fetched.valid_to is not None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_invalidate_removes_from_vector(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            mock_vector = MagicMock()
            mock_vector.is_available.return_value = True
            store.vector = mock_vector
            m = store.add("factual", "content to invalidate")
            store.invalidate(m.id)
            mock_vector.remove.assert_called_once_with(m.id)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# search_vector (with mocked vector)
# ---------------------------------------------------------------------------

class TestSearchVector:
    def test_search_vector_no_vector_returns_empty(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            store.vector = None
            assert store.search_vector("anything") == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_vector_unavailable_returns_empty(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            mock_vector = MagicMock()
            mock_vector.is_available.return_value = False
            store.vector = mock_vector
            assert store.search_vector("anything") == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_vector_with_kind_filter(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            store.add("factual", "factual content", source="s1")
            store.add("semantic", "semantic content", source="s2")
            mock_vector = MagicMock()
            mock_vector.is_available.return_value = True
            mock_vector.search.return_value = [{"id": "fake", "score": 0.9}]
            store.vector = mock_vector
            store.search_vector("content", k=5, kind="factual")
            assert mock_vector.search.called
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_vector_with_kind_filter_empty_result(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            mock_vector = MagicMock()
            mock_vector.is_available.return_value = True
            store.vector = mock_vector
            assert store.search_vector("content", k=5, kind="nonexistent_kind") == []
            mock_vector.search.assert_not_called()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_vector_with_source_filter(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            m = store.add("factual", "content", source="specific-source")
            mock_vector = MagicMock()
            mock_vector.is_available.return_value = True
            mock_vector.search.return_value = [{"id": m.id, "score": 0.95}]
            store.vector = mock_vector
            store.search_vector("content", k=5, source="specific-source")
            mock_vector.search.assert_called_once()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_add_batch_with_vector(self):
        tmp = _tmp()
        try:
            store = _store(tmp)
            mock_vector = MagicMock()
            mock_vector.is_available.return_value = True
            store.vector = mock_vector
            mems = [_mem()]
            store.add_batch(mems)
            mock_vector.add_batch.assert_called_once()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
