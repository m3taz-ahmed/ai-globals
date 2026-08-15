import json
import shutil
from pathlib import Path

from memory.store import MemoryStore
from plugins.graphify.graph_plugin import GraphifyPlugin
from runtime.kernel import Kernel


def _graph_fixture(tmp_path: Path) -> Path:
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir(parents=True, exist_ok=True)
    graph = {
        "nodes": [
            {"id": "a", "label": "core.py", "source_file": "src/core.py", "file_type": "code", "community": 1},
            {"id": "b", "label": "util.py", "source_file": "src/util.py", "file_type": "code", "community": 1},
            {"id": "c", "label": "helper.py", "source_file": "src/helper.py", "file_type": "code", "community": 2},
            {"id": "d", "label": "README.md", "source_file": "README.md", "file_type": "document", "community": 2},
            {"id": "e", "label": "main", "source_file": "src/main.py", "file_type": "code", "community": 1},
        ],
        "links": [
            {"source": "a", "target": "b", "relation": "contains"},
            {"source": "a", "target": "c", "relation": "imports"},
            {"source": "b", "target": "c", "relation": "imports"},
            {"source": "c", "target": "e", "relation": "calls"},
            {"source": "a", "target": "e", "relation": "contains"},
        ],
    }
    (graph_dir / "graph.json").write_text(json.dumps(graph))
    return graph_dir / "graph.json"


def _fixture(tmp_path: Path) -> tuple[Kernel, MemoryStore, GraphifyPlugin]:
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    _graph_fixture(tmp_path)
    kernel = Kernel(tmp_path)
    store = MemoryStore(tmp_path, enable_vector=False)
    plugin = GraphifyPlugin(kernel, store)
    return kernel, store, plugin


def test_query_graphify_returns_neighborhood(tmp_path):
    _, _, plugin = _fixture(tmp_path)
    result = json.loads(plugin.query_graphify("core.py", depth=1))

    assert result["ok"] is True
    assert result["matches"] == 1
    node_ids = {n["id"] for n in result["nodes"]}
    assert "a" in node_ids
    assert "b" in node_ids
    assert "e" in node_ids


def test_query_graphify_missing_graph(tmp_path):
    shutil.rmtree(tmp_path / "graphify-out", ignore_errors=True)
    kernel = Kernel(tmp_path)
    plugin = GraphifyPlugin(kernel, None)
    result = json.loads(plugin.query_graphify("core.py"))

    assert result["ok"] is False
    assert "not found" in result["error"]


def test_sync_graph_to_memory_adds_summaries(tmp_path):
    _, store, plugin = _fixture(tmp_path)
    result = json.loads(plugin.sync_graph_to_memory())

    assert result["ok"] is True
    assert result["added"] > 0
    for mem_id in result["ids"]:
        assert store.get(mem_id) is not None

    # Check semantic memory contains the synced summaries
    semantic = store.search("Graphify", kind="semantic", limit=10)
    assert len(semantic) > 0


def test_sync_graph_to_memory_requires_memory(tmp_path):
    _graph_fixture(tmp_path)
    kernel = Kernel(tmp_path)
    plugin = GraphifyPlugin(kernel, None)
    result = json.loads(plugin.sync_graph_to_memory())

    assert result["ok"] is False
    assert "Memory store not available" in result["error"]


def test_load_graph_invalid_json(tmp_path):
    """Line 33-34: _load_graph returns None on invalid JSON."""
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "graph.json").write_text("not valid json{{{")
    kernel = Kernel(tmp_path)
    plugin = GraphifyPlugin(kernel, None)
    result = json.loads(plugin.query_graphify("core"))
    assert result["ok"] is False
    assert "not found" in result["error"]


def test_load_graph_non_dict_data(tmp_path):
    """Line 36: _load_graph returns None when JSON is not a dict."""
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "graph.json").write_text(json.dumps(["not", "a", "dict"]))
    kernel = Kernel(tmp_path)
    plugin = GraphifyPlugin(kernel, None)
    result = json.loads(plugin.query_graphify("core"))
    assert result["ok"] is False
    assert "not found" in result["error"]


def test_build_index_skips_non_dict_links(tmp_path):
    """Line 51: non-dict links are skipped."""
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir(parents=True, exist_ok=True)
    graph = {
        "nodes": [{"id": "a", "label": "a.py", "source_file": "src/a.py"}],
        "links": ["bad-link", 42, {"source": "a", "target": "a"}],
    }
    (graph_dir / "graph.json").write_text(json.dumps(graph))
    kernel = Kernel(tmp_path)
    plugin = GraphifyPlugin(kernel, None)
    result = json.loads(plugin.query_graphify("a.py"))
    assert result["ok"] is True


def test_build_index_skips_non_string_source_target(tmp_path):
    """Line 55: links with non-string source/target are skipped."""
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir(parents=True, exist_ok=True)
    graph = {
        "nodes": [{"id": "a", "label": "a.py", "source_file": "src/a.py"}],
        "links": [
            {"source": 123, "target": "a"},
            {"source": "a", "target": 456},
        ],
    }
    (graph_dir / "graph.json").write_text(json.dumps(graph))
    kernel = Kernel(tmp_path)
    plugin = GraphifyPlugin(kernel, None)
    result = json.loads(plugin.query_graphify("a.py"))
    assert result["ok"] is True
    # No edges since all links were skipped
    assert len(result["edges"]) == 0


def test_build_index_skips_unknown_node_refs(tmp_path):
    """Line 57: links referencing unknown nodes are skipped."""
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir(parents=True, exist_ok=True)
    graph = {
        "nodes": [{"id": "a", "label": "a.py", "source_file": "src/a.py"}],
        "links": [
            {"source": "a", "target": "nonexistent"},
            {"source": "ghost", "target": "a"},
        ],
    }
    (graph_dir / "graph.json").write_text(json.dumps(graph))
    kernel = Kernel(tmp_path)
    plugin = GraphifyPlugin(kernel, None)
    result = json.loads(plugin.query_graphify("a.py"))
    assert result["ok"] is True
    assert len(result["edges"]) == 0


def test_is_file_node_non_string_fields(tmp_path):
    """Line 70: _is_file_node returns False when source_file/label are not strings."""
    _graph_fixture(tmp_path)
    kernel = Kernel(tmp_path)
    plugin = GraphifyPlugin(kernel, None)
    assert plugin._is_file_node({"source_file": 123, "label": "x.py"}) is False
    assert plugin._is_file_node({"source_file": "x.py", "label": 123}) is False


def test_neighborhood_breaks_on_empty_frontier(tmp_path):
    """Line 91: _neighborhood breaks early when frontier is empty."""
    _graph_fixture(tmp_path)
    kernel = Kernel(tmp_path)
    plugin = GraphifyPlugin(kernel, None)
    # Query with depth=3 but isolated node 'd' has no neighbors
    result = json.loads(plugin.query_graphify("README.md", depth=3))
    assert result["ok"] is True


def test_query_graphify_no_match(tmp_path):
    """Line 115: query returns error when no node matches."""
    _graph_fixture(tmp_path)
    kernel = Kernel(tmp_path)
    plugin = GraphifyPlugin(kernel, None)
    result = json.loads(plugin.query_graphify("nonexistent_component_xyz"))
    assert result["ok"] is False
    assert "No node matched" in result["error"]


def test_sync_graph_to_memory_missing_graph(tmp_path):
    """Line 152: sync_graph_to_memory returns error when graph not found."""
    # Don't create graph fixture
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    kernel = Kernel(tmp_path)
    store = MemoryStore(tmp_path, enable_vector=False)
    plugin = GraphifyPlugin(kernel, store)
    result = json.loads(plugin.sync_graph_to_memory())
    assert result["ok"] is False
    assert "not found" in result["error"]


def test_register_mcp_tools(tmp_path):
    """Line 168: register_mcp_tools returns the two tool methods."""
    _graph_fixture(tmp_path)
    kernel = Kernel(tmp_path)
    plugin = GraphifyPlugin(kernel, None)
    tools = plugin.register_mcp_tools()
    assert len(tools) == 2
    assert plugin.query_graphify in tools
    assert plugin.sync_graph_to_memory in tools
