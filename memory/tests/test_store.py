import shutil
import tempfile
from pathlib import Path

from memory.store import MemoryStore


def test_add_and_get():
    tmp = Path(tempfile.mkdtemp(prefix="aios_mem_"))
    try:
        store = MemoryStore(tmp, tmp / "memory.db", enable_vector=False)
        m = store.add("factual", "Laravel uses Eloquent ORM", source="tech-stack/laravel-11.md")
        assert m.kind == "factual"
        fetched = store.get(m.id)
        assert fetched is not None
        assert fetched.content == "Laravel uses Eloquent ORM"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_search_fts():
    tmp = Path(tempfile.mkdtemp(prefix="aios_mem_"))
    try:
        store = MemoryStore(tmp, tmp / "memory.db", enable_vector=False)
        store.add("factual", "Laravel uses Eloquent ORM")
        results = store.search("Eloquent")
        assert len(results) == 1
        results = store.search("Rails")
        assert len(results) == 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_relate():
    tmp = Path(tempfile.mkdtemp(prefix="aios_mem_"))
    try:
        store = MemoryStore(tmp, tmp / "memory.db", enable_vector=False)
        a = store.add("factual", "User model")
        b = store.add("factual", "Post model")
        store.relate(a.id, b.id, "has_many")
        rels = store.related(a.id)
        assert len(rels) == 1
        assert rels[0][1] == "has_many"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_invalid_like_wildcards():
    tmp = Path(tempfile.mkdtemp(prefix="aios_mem_"))
    try:
        store = MemoryStore(tmp, tmp / "memory.db", enable_vector=False)
        store.add("factual", "hello world")
        # The literal '%' should not match all records
        results = store.search("%")
        assert len(results) == 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
