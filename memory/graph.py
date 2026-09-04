#!/usr/bin/env python3
"""Deterministic knowledge-graph extraction from structured data.

Re-implements the zero-LLM indexing idea from synaptic-memory: build a graph
from tables, columns, and foreign keys without calling an embedding model.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# SQLite identifiers (table/index/column names) must match this pattern.
# Prevents SQL injection via PRAGMA statements which don't accept parameters.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# OOM guard: cap graph size for huge databases.
_MAX_TABLES = 500
_MAX_COLUMNS_PER_TABLE = 500


def _validate_identifier(name: str, kind: str = "table") -> str:
    """Validate a SQLite identifier against a strict pattern to prevent injection."""
    if not name or not _IDENTIFIER_RE.fullmatch(name):
        raise ValueError(f"Invalid {kind} identifier: {name!r}")
    return name


@dataclass
class Node:
    """A graph node."""

    id: str
    kind: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """A graph edge."""

    source: str
    target: str
    kind: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Graph:
    """A simple knowledge graph."""

    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def add_node(self, node: Node) -> None:
        self.nodes.append(node)

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def to_dict(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "nodes": [
                {"id": n.id, "kind": n.kind, "label": n.label, "properties": n.properties}
                for n in self.nodes
            ],
            "edges": [
                {"source": e.source, "target": e.target, "kind": e.kind, "properties": e.properties}
                for e in self.edges
            ],
        }


class SchemaGraph:
    """Extract a knowledge graph from a SQLite database schema."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def _table_sql(self, conn: sqlite3.Connection, table: str) -> str:
        row = conn.execute("SELECT sql FROM sqlite_master WHERE name = ?", (table,)).fetchone()
        return row[0] if row and row[0] else ""

    def build(self) -> Graph:
        graph = Graph()
        if not self.db_path.exists():
            return graph
        # Read-only open: never create a DB as a side effect of a read.
        uri = f"file:{self.db_path}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            tables = [t for t in tables if not t.startswith("sqlite_")][: _MAX_TABLES]

            for table in tables:
                _validate_identifier(table, "table")
                table_node = Node(id=f"table:{table}", kind="table", label=table, properties={})
                graph.add_node(table_node)

                columns = conn.execute(f"PRAGMA table_info({_validate_identifier(table)})").fetchall()
                for col in columns[: _MAX_COLUMNS_PER_TABLE]:
                    col_name = col["name"]
                    _validate_identifier(col_name, "column")
                    col_id = f"column:{table}.{col_name}"
                    graph.add_node(
                        Node(
                            id=col_id,
                            kind="column",
                            label=col_name,
                            properties={
                                "table": table,
                                "type": col["type"],
                                "notnull": bool(col["notnull"]),
                                "pk": bool(col["pk"]),
                            },
                        )
                    )
                    graph.add_edge(Edge(source=table_node.id, target=col_id, kind="has_column"))

                fks = conn.execute(f"PRAGMA foreign_key_list({_validate_identifier(table)})").fetchall()
                for fk in fks:
                    target_id = f"column:{fk['table']}.{fk['to']}"
                    source_id = f"column:{table}.{fk['from']}"
                    graph.add_edge(
                        Edge(
                            source=source_id,
                            target=target_id,
                            kind="foreign_key",
                            properties={"table": table, "target_table": fk["table"]},
                        )
                    )

            # Index edges
            for table in tables:
                _validate_identifier(table, "table")
                indexes = conn.execute(f"PRAGMA index_list({_validate_identifier(table)})").fetchall()
                for idx in indexes:
                    idx_name = idx["name"]
                    _validate_identifier(idx_name, "index")
                    idx_info = conn.execute(f"PRAGMA index_info({_validate_identifier(idx_name)})").fetchall()
                    for info in idx_info:
                        col_id = f"column:{table}.{info['name']}"
                        graph.add_edge(
                            Edge(
                                source=f"table:{table}",
                                target=col_id,
                                kind="has_index",
                                properties={"index": idx_name},
                            )
                        )

        return graph
