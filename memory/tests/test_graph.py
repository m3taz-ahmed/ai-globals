#!/usr/bin/env python3
"""Tests for memory.graph."""

from __future__ import annotations

import sqlite3

import pytest

from memory.graph import SchemaGraph


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
