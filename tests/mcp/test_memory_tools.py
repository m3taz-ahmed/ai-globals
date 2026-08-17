"""Tests for aizee_mcp/tools/memory_tools.py — memory-related MCP tools."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from mcp.server.fastmcp import FastMCP

# Set up isolated root BEFORE importing
_ROOT = tempfile.mkdtemp(prefix="aios_mem_test_")
os.environ["AIZEE_ROOT"] = _ROOT
ROOT = Path(_ROOT)
for sub in ("brain", "rules", "tech-stack", "workflows", "skills"):
    (ROOT / sub).mkdir(parents=True, exist_ok=True)

from aizee_mcp.tools.common import reset_state  # noqa: E402
from aizee_mcp.tools.memory_tools import register_memory_tools  # noqa: E402

_mcp = FastMCP("test-memory")
register_memory_tools(_mcp)


def _call(name: str, arguments: dict) -> str:
    os.environ["AIZEE_ROOT"] = _ROOT
    reset_state()
    return _mcp._tool_manager.get_tool(name).fn(**arguments)


def _mock_memory():
    """Return a MagicMock that behaves like a MemoryStore."""
    m = MagicMock()
    m.root = ROOT
    m.search.return_value = []
    m.search_vector.return_value = []
    m.get.return_value = None
    m.related.return_value = []
    m.add.return_value = MagicMock(id="test-id-123")
    return m


class TestSearchMemory:
    def test_invalid_query(self):
        """Cover line 36: validate_query error."""
        result = _call("search_memory", {"query": ""})
        data = json.loads(result)
        assert data["ok"] is False

    def test_invalid_kind(self):
        """Cover line 39: validate_kind error."""
        result = _call("search_memory", {"query": "test", "kind": "../etc"})
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid kind" in data["error"]

    def test_successful_search(self):
        """Cover normal search path with mocked store."""
        mock_mem = MagicMock(id="m1", kind="semantic", source="rules/core.md", content="test content")
        mock_store = _mock_memory()
        mock_store.search.return_value = [mock_mem]
        with patch("aizee_mcp.tools.memory_tools.memory", return_value=mock_store):
            result = _call("search_memory", {"query": "test"})
            data = json.loads(result)
            assert len(data) == 1
            assert data[0]["id"] == "m1"


class TestSearchMemoryVector:
    def test_invalid_query(self):
        """Cover line 52: validate_query error."""
        result = _call("search_memory_vector", {"query": ""})
        data = json.loads(result)
        assert data["ok"] is False

    def test_invalid_kind(self):
        """Cover line 55: validate_kind error."""
        result = _call("search_memory_vector", {"query": "test", "kind": "../etc"})
        data = json.loads(result)
        assert data["ok"] is False

    def test_successful_vector_search(self):
        mock_store = _mock_memory()
        mock_store.search_vector.return_value = [{"id": "v1", "score": 0.9}]
        with patch("aizee_mcp.tools.memory_tools.memory", return_value=mock_store):
            result = _call("search_memory_vector", {"query": "test"})
            data = json.loads(result)
            assert len(data) == 1
            assert data[0]["id"] == "v1"


class TestQueryContext:
    def test_invalid_query(self):
        """Cover line 65: validate_query error."""
        result = _call("query_context", {"query": ""})
        data = json.loads(result)
        assert data["ok"] is False

    def test_invalid_kind(self):
        """Cover line 68: validate_kind error."""
        result = _call("query_context", {"query": "test", "kind": "../etc"})
        data = json.loads(result)
        assert data["ok"] is False

    def test_vector_result_record_not_found(self):
        """Cover line 100: continue when store.get returns None for vector result."""
        mock_store = _mock_memory()
        # FTS returns nothing, vector returns a result whose ID is not in store
        mock_store.search.return_value = []
        mock_store.search_vector.return_value = [{"id": "missing-id", "score": 0.8}]
        mock_store.get.return_value = None
        with patch("aizee_mcp.tools.memory_tools.memory", return_value=mock_store):
            result = _call("query_context", {"query": "test"})
            data = json.loads(result)
            assert data == []

    def test_query_context_mixed_results(self):
        """Cover full hybrid search with FTS + vector overlap + new vector result."""
        mock_store = _mock_memory()
        fts_mem = MagicMock(id="m1", kind="semantic", source="rules/core.md", content="fts content")
        mock_store.search.return_value = [fts_mem]
        # Vector result overlaps with FTS + a new one
        mock_store.search_vector.return_value = [
            {"id": "m1", "score": 0.95},  # overlaps with FTS
            {"id": "m2", "score": 0.85},  # new
        ]
        new_mem = MagicMock(id="m2", kind="factual", source="tech-stack/x.md", content="vector content")
        mock_store.get.side_effect = lambda mid: new_mem if mid == "m2" else None
        with patch("aizee_mcp.tools.memory_tools.memory", return_value=mock_store):
            result = _call("query_context", {"query": "test"})
            data = json.loads(result)
            assert len(data) == 2
            # m1 should have score from vector overlap
            m1_item = next(i for i in data if i["id"] == "m1")
            assert m1_item["score"] == 0.95
            assert m1_item["vector"] is True
            # m2 should be a new vector result
            m2_item = next(i for i in data if i["id"] == "m2")
            assert m2_item["fts"] is False
            assert m2_item["vector"] is True


class TestGetRelatedMemories:
    def test_invalid_mem_id(self):
        """Cover line 126: invalid mem_id."""
        result = _call("get_related_memories", {"mem_id": ""})
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid mem_id" in data["error"]

    def test_invalid_mem_id_too_long(self):
        """Cover line 126: overlong mem_id."""
        result = _call("get_related_memories", {"mem_id": "a" * 129})
        data = json.loads(result)
        assert data["ok"] is False

    def test_invalid_relation(self):
        """Cover line 128: invalid relation name."""
        result = _call("get_related_memories", {"mem_id": "valid-id", "relation": "../etc"})
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid relation" in data["error"]

    def test_successful_related(self):
        mock_store = _mock_memory()
        related_mem = MagicMock(id="r1", kind="semantic", content="related content")
        mock_store.related.return_value = [(related_mem, "depends_on")]
        with patch("aizee_mcp.tools.memory_tools.memory", return_value=mock_store):
            result = _call("get_related_memories", {"mem_id": "valid-id"})
            data = json.loads(result)
            assert len(data) == 1
            assert data[0]["id"] == "r1"
            assert data[0]["relation"] == "depends_on"


class TestAddMemory:
    def test_invalid_kind(self):
        """Cover line 139: invalid kind."""
        result = _call("add_memory", {"kind": "invalid_kind", "content": "test", "source": "src"})
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid kind" in data["error"]

    def test_invalid_content_empty(self):
        """Cover line 141: empty content."""
        result = _call("add_memory", {"kind": "factual", "content": "", "source": "src"})
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid content" in data["error"]

    def test_invalid_content_too_long(self):
        """Cover line 141: overlong content."""
        result = _call("add_memory", {"kind": "factual", "content": "x" * 100_001, "source": "src"})
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid content" in data["error"]

    def test_invalid_source(self):
        """Cover line 143: invalid source."""
        result = _call("add_memory", {"kind": "factual", "content": "test", "source": ""})
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid source" in data["error"]

    def test_invalid_source_too_long(self):
        """Cover line 143: overlong source."""
        result = _call("add_memory", {"kind": "factual", "content": "test", "source": "a" * 1025})
        data = json.loads(result)
        assert data["ok"] is False

    def test_successful_add(self):
        mock_store = _mock_memory()
        mock_store.add.return_value = MagicMock(id="new-mem-456")
        with patch("aizee_mcp.tools.memory_tools.memory", return_value=mock_store):
            result = _call("add_memory", {"kind": "factual", "content": "test content", "source": "test"})
            data = json.loads(result)
            assert data["ok"] is True
            assert data["id"] == "new-mem-456"


class TestInvalidateMemory:
    def test_invalid_id(self):
        """Cover line 151: invalid id."""
        result = _call("invalidate_memory", {"id": ""})
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid id" in data["error"]

    def test_invalid_id_too_long(self):
        """Cover line 151: overlong id."""
        result = _call("invalidate_memory", {"id": "a" * 129})
        data = json.loads(result)
        assert data["ok"] is False

    def test_memory_not_found(self):
        mock_store = _mock_memory()
        mock_store.get.return_value = None
        with patch("aizee_mcp.tools.memory_tools.memory", return_value=mock_store):
            result = _call("invalidate_memory", {"id": "nonexistent-id"})
            data = json.loads(result)
            assert data["ok"] is False
            assert "not found" in data["error"]

    def test_successful_invalidate(self):
        mock_store = _mock_memory()
        mock_store.get.return_value = MagicMock(id="existing-id")
        with patch("aizee_mcp.tools.memory_tools.memory", return_value=mock_store):
            result = _call("invalidate_memory", {"id": "existing-id"})
            data = json.loads(result)
            assert data["ok"] is True
            assert data["id"] == "existing-id"
            mock_store.invalidate.assert_called_once_with("existing-id")


class TestIngestMemory:
    def test_successful_ingest(self):
        mock_store = _mock_memory()
        with patch("aizee_mcp.tools.memory_tools.memory", return_value=mock_store), \
             patch("aizee_mcp.tools.memory_tools.Ingestor") as mock_ingestor_cls:
            mock_ingestor = MagicMock()
            mock_ingestor.ingest_all.return_value = ["id1", "id2", "id3"]
            mock_ingestor_cls.return_value = mock_ingestor
            result = _call("ingest_memory", {})
            data = json.loads(result)
            assert data["ingested"] == 3


class TestBuildSchemaGraph:
    def test_invalid_db_path_empty(self):
        """Cover line 161: empty db_path."""
        result = _call("build_schema_graph", {"db_path": ""})
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid db_path" in data["error"]

    def test_invalid_db_path_too_long(self):
        """Cover line 161: overlong db_path."""
        result = _call("build_schema_graph", {"db_path": "a" * 1025})
        data = json.loads(result)
        assert data["ok"] is False

    def test_db_not_found(self):
        """Cover line 165: database file not found."""
        result = _call("build_schema_graph", {"db_path": "nonexistent.db"})
        data = json.loads(result)
        assert data["ok"] is False
        assert "Database not found" in data["error"]

    def test_successful_build(self):
        """Cover lines 166-168: build schema graph from valid SQLite db."""
        # Create a test SQLite database
        db_file = ROOT / "test_schema.db"
        with sqlite3.connect(str(db_file)) as conn:
            conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
            conn.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT)")
            conn.commit()

        with patch("aizee_mcp.tools.memory_tools.SchemaGraph") as mock_graph_cls:
            mock_graph = MagicMock()
            mock_graph.nodes = [MagicMock(id="table:users"), MagicMock(id="table:posts")]
            mock_graph.edges = []
            mock_graph_cls.return_value = mock_graph
            mock_graph_cls.return_value.build.return_value = mock_graph

            result = _call("build_schema_graph", {"db_path": "test_schema.db"})
            data = json.loads(result)
            assert data["ok"] is True
            assert data["nodes"] == 2
            assert "table:users" in data["nodes_list"]

    def test_resolve_path_returns_none(self):
        """Cover line 165: resolve_path returns None."""
        with patch("aizee_mcp.tools.memory_tools.resolve_path", return_value=None):
            result = _call("build_schema_graph", {"db_path": "test.db"})
            data = json.loads(result)
            assert data["ok"] is False
            assert "Database not found" in data["error"]
