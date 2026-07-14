from pathlib import Path

from memory.store import MemoryStore
from runtime.kernel import Kernel
from runtime.plugin import AIOSPlugin, PluginManager


class StubPlugin(AIOSPlugin):
    name = "stub"

    def on_load(self) -> None:
        self.loaded = True

    def register_mcp_tools(self):
        return [self._tool]

    def _tool(self, x: int) -> int:
        return x * 2


def _setup_root(tmp_path: Path) -> Path:
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain", "plugins/stub"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    (tmp_path / "workflows/test.md").write_text(
        "[WORKFLOW] test\n[OBJ] Test workflow.\n[RULES]\n1. [REQ] Step one.\n"
    )
    (tmp_path / "plugins/__init__.py").write_text("")
    (tmp_path / "plugins/stub/__init__.py").write_text(
        "from runtime.plugin import AIOSPlugin\n"
        "class StubPlugin(AIOSPlugin):\n"
        "    name = 'stub'\n"
        "    def on_load(self): self.loaded = True\n"
        "    def register_mcp_tools(self): return [self._tool]\n"
        "    def _tool(self, x: int) -> int: return x * 2\n"
        "Plugin = StubPlugin\n"
    )
    (tmp_path / "plugins.yaml").write_text("plugins:\n  stub:\n    enabled: true\n")
    return tmp_path


def test_plugin_manager_loads_enabled_plugin(tmp_path):
    _setup_root(tmp_path)
    kernel = Kernel(tmp_path)
    store = MemoryStore(tmp_path, enable_vector=False)
    manager = PluginManager(kernel, tmp_path)
    manager.load_all(store)

    assert "stub" in manager._plugins
    assert manager._plugins["stub"].loaded is True
    assert len(manager.get_tools()) == 1
    assert manager.get_tools()[0](5) == 10


def test_plugin_manager_ignores_unlisted_plugins(tmp_path):
    _setup_root(tmp_path)
    (tmp_path / "plugins.yaml").write_text("plugins:\n  other:\n    enabled: true\n")
    kernel = Kernel(tmp_path)
    manager = PluginManager(kernel, tmp_path)
    manager.load_all()

    assert "stub" not in manager._plugins
    assert manager.get_tools() == []


def test_plugin_manager_config_missing(tmp_path):
    (tmp_path / "runtime/policies").mkdir(parents=True)
    (tmp_path / "runtime/policies/default.yaml").write_text("default_action: ask\nrules: []\n")
    kernel = Kernel(tmp_path)
    manager = PluginManager(kernel, tmp_path)
    manager.load_all()
    assert manager.list_plugins() == []


def test_kernel_load_plugins_wires_manager(tmp_path):
    _setup_root(tmp_path)
    kernel = Kernel(tmp_path)
    store = MemoryStore(tmp_path, enable_vector=False)
    kernel.load_plugins(store)

    assert "stub" in kernel.plugins._plugins
