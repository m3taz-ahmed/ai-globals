#!/usr/bin/env python3
"""Tests for memory.graph."""

from __future__ import annotations

import sqlite3

import pytest

from memory.graph import Edge, Graph, Node, SchemaGraph, _validate_identifier


@pytest.fixture
def sample_db(tmp_path):
    path = tmp_path / "sample.db"
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE INDEX idx_posts_user ON posts(user_id);
            """
        )
    yield path


def test_schema_graph_builds(sample_db):
    graph = SchemaGraph(sample_db).build()
    node_ids = {n.id for n in graph.nodes}
    assert "table:users" in node_ids
    assert "table:posts" in node_ids
    assert "column:users.id" in node_ids
    assert "column:posts.user_id" in node_ids

    edge_kinds = [e.kind for e in graph.edges]
    assert "has_column" in edge_kinds
    assert "foreign_key" in edge_kinds
    assert "has_index" in edge_kinds

    fk_edge = next(e for e in graph.edges if e.kind == "foreign_key")
    assert fk_edge.source == "column:posts.user_id"
    assert fk_edge.target == "column:users.id"


# ---------------------------------------------------------------------------
# _validate_identifier
# ---------------------------------------------------------------------------

class TestValidateIdentifier:
    def test_valid_identifier_returned(self):
        assert _validate_identifier("users") == "users"

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="Invalid.*identifier"):
            _validate_identifier("")

    def test_invalid_name_raises(self):
        with pytest.raises(ValueError, match="Invalid.*identifier"):
            _validate_identifier("table; DROP TABLE--")

    def test_name_with_space_raises(self):
        with pytest.raises(ValueError, match="Invalid.*identifier"):
            _validate_identifier("bad name")


# ---------------------------------------------------------------------------
# Graph.to_dict
# ---------------------------------------------------------------------------

class TestGraphToDict:
    def test_to_dict_serializes_nodes_and_edges(self):
        """Line 62: Graph.to_dict() returns proper dict structure."""
        g = Graph()
        g.add_node(Node(id="table:users", kind="table", label="users"))
        g.add_node(Node(id="column:users.id", kind="column", label="id", properties={"type": "INTEGER"}))
        g.add_edge(Edge(source="table:users", target="column:users.id", kind="has_column"))
        d = g.to_dict()
        assert len(d["nodes"]) == 2
        assert d["nodes"][0]["id"] == "table:users"
        assert d["nodes"][1]["properties"] == {"type": "INTEGER"}
        assert len(d["edges"]) == 1
        assert d["edges"][0]["kind"] == "has_column"

    def test_to_dict_empty_graph(self):
        d = Graph().to_dict()
        assert d == {"nodes": [], "edges": []}


# ---------------------------------------------------------------------------
# SchemaGraph._table_sql
# ---------------------------------------------------------------------------

class TestTableSql:
    def test_table_sql_returns_create_statement(self, sample_db):
        """Lines 81-82: _table_sql returns the CREATE TABLE SQL for an existing table."""
        sg = SchemaGraph(sample_db)
        with sqlite3.connect(sample_db) as conn:
            sql = sg._table_sql(conn, "users")
        assert "CREATE TABLE" in sql
        assert "users" in sql

    def test_table_sql_returns_empty_for_nonexistent(self, sample_db):
        """Lines 81-82: _table_sql returns empty string for a non-existent table."""
        sg = SchemaGraph(sample_db)
        with sqlite3.connect(sample_db) as conn:
            sql = sg._table_sql(conn, "nonexistent_table")
        assert sql == ""
