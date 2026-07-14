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
