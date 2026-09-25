"""Tests for runtime.c4_docs — C4 markdown generation from graphify graph."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.c4_docs import C4Generator, _container_of


@pytest.fixture()
def mini_graph(tmp_path: Path) -> Path:
    g = {
        "directed": True,
        "nodes": [
            {"id": "a_mod", "label": "a.py", "file_type": "code", "source_file": "runtime/a.py"},
            {"id": "a_fn", "label": "fn", "file_type": "code", "source_file": "runtime/a.py"},
            {"id": "b_mod", "label": "b.py", "file_type": "code", "source_file": "memory/b.py"},
            {"id": "c_mod", "label": "c.py", "file_type": "code", "source_file": "htmlcov/c.py"},
            {"id": "ext_pkg", "label": "requests"},
        ],
        "links": [
            {"relation": "calls", "source": "a_fn", "target": "b_mod"},
            {"relation": "imports_from", "source": "a_mod", "target": "ext_pkg"},
            {"relation": "contains", "source": "a_mod", "target": "a_fn"},
        ],
    }
    p = tmp_path / "graph.json"
    p.write_text(json.dumps(g), encoding="utf-8")
    return p


def test_container_of() -> None:
    assert _container_of("runtime/x.py") == "runtime"
    assert _container_of("a\\b\\c.py") == "a"
    assert _container_of("solo.py") == "(root)"
    assert _container_of("") == "(root)"


def test_containers_grouped_and_excluded(mini_graph: Path) -> None:
    gen = C4Generator(mini_graph)
    assert "runtime" in gen.containers and "memory" in gen.containers
    assert "htmlcov" not in gen.containers  # excluded generated dir
    assert len(gen.containers["runtime"].files) == 1


def test_cross_container_edges_aggregated(mini_graph: Path) -> None:
    gen = C4Generator(mini_graph)
    assert gen.containers["runtime"].edges_out["memory"] == 1
    assert gen.containers["memory"].edges_in["runtime"] == 1


def test_external_imports_counted(mini_graph: Path) -> None:
    gen = C4Generator(mini_graph)
    assert gen._external["requests"] == 1


def test_generate_writes_docs(mini_graph: Path, tmp_path: Path) -> None:
    gen = C4Generator(mini_graph)
    out = tmp_path / "c4"
    written = gen.generate(out)
    names = {p.name for p in written}
    assert {"context.md", "containers.md"} <= names
    assert "runtime.md" in names and "memory.md" in names
    containers = (out / "containers.md").read_text(encoding="utf-8")
    assert "```mermaid" in containers and "runtime" in containers
    ctx = (out / "context.md").read_text(encoding="utf-8")
    assert "C4Context" in ctx and "requests" in ctx


def test_component_md_internal_edges(mini_graph: Path, tmp_path: Path) -> None:
    gen = C4Generator(mini_graph)
    md = gen.component_md("runtime")
    assert "runtime" in md and "Files" in md
