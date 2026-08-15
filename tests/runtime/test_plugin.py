from pathlib import Path
from unittest.mock import patch

import pytest

from memory.store import MemoryStore
from runtime.kernel import Kernel
from runtime.plugin import AIOSPlugin, PluginGuard, PluginManager, _is_plugin_source_safe


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


def test_stub_plugin_on_load_sets_loaded():
    """Cover line 12 (name), 15 (on_load), 18 (register_mcp_tools) of StubPlugin."""
    plugin = StubPlugin.__new__(StubPlugin)
    plugin.kernel = None
    plugin.memory = None
    plugin.on_load()
    assert plugin.loaded is True
    tools = plugin.register_mcp_tools()
    assert len(tools) == 1
    assert tools[0](5) == 10


# ---------------------------------------------------------------------------
# _is_plugin_source_safe
# ---------------------------------------------------------------------------


def test_is_plugin_source_safe_syntax_error() -> None:
    safe, reason = _is_plugin_source_safe("def (", "bad.py")
    assert safe is False
    assert "Syntax error" in reason


def test_is_plugin_source_safe_blocked_name_call() -> None:
    safe, reason = _is_plugin_source_safe("eval('1')", "bad.py")
    assert safe is False
    assert "Blocked call to 'eval'" in reason


def test_is_plugin_source_safe_blocked_attribute_call() -> None:
    safe, reason = _is_plugin_source_safe("obj.exec('x')", "bad.py")
    assert safe is False
    assert "Blocked call to '.exec'" in reason


def test_is_plugin_source_safe_blocked_dunder_access() -> None:
    safe, reason = _is_plugin_source_safe("x.__class__", "bad.py")
    assert safe is False
    assert "Blocked dunder attribute" in reason


def test_is_plugin_source_safe_blocked_builtins_subscript() -> None:
    safe, reason = _is_plugin_source_safe("__builtins__['eval']", "bad.py")
    assert safe is False
    assert "Blocked __builtins__ subscript" in reason


def test_is_plugin_source_safe_clean() -> None:
    safe, reason = _is_plugin_source_safe("x = 1 + 2\n", "ok.py")
    assert safe is True
    assert reason == ""


# ---------------------------------------------------------------------------
# AIOSPlugin defaults
# ---------------------------------------------------------------------------


def test_aios_plugin_default_tools_and_resources(tmp_path):
    _setup_root(tmp_path)
    kernel = Kernel(tmp_path)

    class MinimalPlugin(AIOSPlugin):
        name = "minimal"

        def on_load(self) -> None:
            pass  # pragma: no cover

    plugin = MinimalPlugin(kernel)
    assert plugin.register_mcp_tools() == []
    assert plugin.register_mcp_resources() == []
    plugin.on_load()  # cover line 156


# ---------------------------------------------------------------------------
# PluginGuard
# ---------------------------------------------------------------------------


def test_plugin_guard_blocks_denied_action() -> None:
    guard = PluginGuard(permissions=["Read"])
    assert guard.is_allowed("Read") is True
    assert guard.is_allowed("Bash") is False  # in DENIED_DEFAULT


def test_plugin_guard_wrap_blocks() -> None:
    guard = PluginGuard(permissions=["Read"])

    def fn(action, **kw):
        return "ok"

    wrapped = guard.wrap(fn, "test-plugin")
    with pytest.raises(RuntimeError, match="blocked by sandbox"):
        wrapped(action="Bash")
    assert wrapped(action="Read") == "ok"


# ---------------------------------------------------------------------------
# PluginManager — _load_config / _load_plugin_module / _discover_plugins
# ---------------------------------------------------------------------------


def test_load_config_reads_yaml(tmp_path):
    _setup_root(tmp_path)
    kernel = Kernel(tmp_path)
    manager = PluginManager(kernel, tmp_path)
    cfg = manager._load_config()
    assert "plugins" in cfg
    assert cfg["plugins"]["stub"]["enabled"] is True


def test_load_plugin_module_no_init_file(tmp_path):
    _setup_root(tmp_path)
    kernel = Kernel(tmp_path)
    manager = PluginManager(kernel, tmp_path)
    # 'nonexistent' plugin dir doesn't have __init__.py
    assert manager._load_plugin_module("nonexistent") is None


def test_load_plugin_module_spec_none(tmp_path):
    _setup_root(tmp_path)
    kernel = Kernel(tmp_path)
    manager = PluginManager(kernel, tmp_path)
    with patch("importlib.util.spec_from_file_location", return_value=None):
        assert manager._load_plugin_module("stub") is None


def test_load_plugin_module_exec_module_exception(tmp_path, recwarn):
    _setup_root(tmp_path)
    # Write a plugin that raises on import
    (tmp_path / "plugins" / "crash").mkdir(parents=True, exist_ok=True)
    (tmp_path / "plugins" / "crash" / "__init__.py").write_text("raise RuntimeError('boom')\n")
    (tmp_path / "plugins.yaml").write_text("plugins:\n  crash:\n    enabled: true\n")
    kernel = Kernel(tmp_path)
    manager = PluginManager(kernel, tmp_path)
    assert manager._load_plugin_module("crash") is None
    assert any("failed to load" in str(w.message) for w in recwarn)


def test_discover_plugins_no_valid_plugin_class(tmp_path, recwarn):
    _setup_root(tmp_path)
    # Plugin with no Plugin class
    (tmp_path / "plugins" / "noplug").mkdir(parents=True, exist_ok=True)
    (tmp_path / "plugins" / "noplug" / "__init__.py").write_text("x = 1\n")
    (tmp_path / "plugins.yaml").write_text(
        "plugins:\n  stub:\n    enabled: true\n  noplug:\n    enabled: true\n"
    )
    kernel = Kernel(tmp_path)
    manager = PluginManager(kernel, tmp_path)
    discovered = manager._discover_plugins()
    names = [n for n, _ in discovered]
    assert "stub" in names
    assert "noplug" not in names
    assert any("no valid Plugin class" in str(w.message) for w in recwarn)


def test_load_all_idempotent(tmp_path):
    _setup_root(tmp_path)
    kernel = Kernel(tmp_path)
    manager = PluginManager(kernel, tmp_path)
    manager.load_all()
    first_count = len(manager._plugins)
    manager.load_all()  # second call should be no-op
    assert len(manager._plugins) == first_count


def test_load_all_on_load_exception(tmp_path, recwarn):
    _setup_root(tmp_path)
    # Plugin whose on_load raises
    (tmp_path / "plugins" / "failinit").mkdir(parents=True, exist_ok=True)
    (tmp_path / "plugins" / "failinit" / "__init__.py").write_text(
        "from runtime.plugin import AIOSPlugin\n"
        "class BadPlugin(AIOSPlugin):\n"
        "    name = 'failinit'\n"
        "    def on_load(self): raise RuntimeError('init fail')\n"
        "Plugin = BadPlugin\n"
    )
    (tmp_path / "plugins.yaml").write_text("plugins:\n  failinit:\n    enabled: true\n")
    kernel = Kernel(tmp_path)
    manager = PluginManager(kernel, tmp_path)
    manager.load_all()
    assert "failinit" not in manager._plugins
    assert any("failed to initialize" in str(w.message) for w in recwarn)


def test_get_resources_aggregates(tmp_path):
    _setup_root(tmp_path)
    # Add a plugin that exposes resources (using a mock to avoid abstract Resource)
    (tmp_path / "plugins" / "resplug").mkdir(parents=True, exist_ok=True)
    (tmp_path / "plugins" / "resplug" / "__init__.py").write_text(
        "from unittest.mock import MagicMock\n"
        "from runtime.plugin import AIOSPlugin\n"
        "class ResPlugin(AIOSPlugin):\n"
        "    name = 'resplug'\n"
        "    def on_load(self): pass\n"
        "    def register_mcp_resources(self): return [MagicMock()]\n"
        "Plugin = ResPlugin\n"
    )
    (tmp_path / "plugins.yaml").write_text(
        "plugins:\n  stub:\n    enabled: true\n  resplug:\n    enabled: true\n"
    )
    kernel = Kernel(tmp_path)
    manager = PluginManager(kernel, tmp_path)
    manager.load_all()
    resources = manager.get_resources()
    assert len(resources) == 1


def test_list_plugins_returns_names_and_versions(tmp_path):
    _setup_root(tmp_path)
    kernel = Kernel(tmp_path)
    manager = PluginManager(kernel, tmp_path)
    manager.load_all()
    plugins = manager.list_plugins()
    assert any(p["name"] == "stub" for p in plugins)
    assert all("version" in p for p in plugins)


def test_load_config_returns_empty_when_no_file(tmp_path):
    """Cover line 135: _load_config returns {} when plugins.yaml doesn't exist."""
    (tmp_path / "runtime/policies").mkdir(parents=True)
    (tmp_path / "runtime/policies/default.yaml").write_text("default_action: ask\nrules: []\n")
    kernel = Kernel(tmp_path)
    manager = PluginManager(kernel, tmp_path)
    assert manager._load_config() == {}
