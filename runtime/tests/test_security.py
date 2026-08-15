"""Security-focused tests for plugin sandbox, MCP path validation, and audit redaction."""

from __future__ import annotations

from pathlib import Path

from aios_mcp.tools.common import is_safe_name as _is_safe_name
from aios_mcp.tools.common import resolve_path as _resolve_path
from runtime.audit import AuditLogger
from runtime.kernel import Kernel
from runtime.plugin import AIOSPlugin, PluginManager


class _BadPlugin(AIOSPlugin):
    def on_load(self) -> None:
        pass


def test_plugin_blocks_denylisted_import(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    plugin_dir = plugins_dir / "bad"
    plugin_dir.mkdir()
    (plugin_dir / "__init__.py").write_text(
        "import os\nfrom runtime.plugin import AIOSPlugin\nclass Plugin(AIOSPlugin):\n    def on_load(self): pass\n",
        encoding="utf-8",
    )
    (tmp_path / "plugins.yaml").write_text(
        "plugins:\n  bad:\n    enabled: true\n", encoding="utf-8"
    )
    k = Kernel(tmp_path)
    manager = PluginManager(k, root=tmp_path)
    manager.load_all()
    assert "bad" not in manager.list_plugins()


def test_is_safe_name_rejects_path_traversal() -> None:
    assert not _is_safe_name("../etc/passwd")
    assert not _is_safe_name("foo\\bar")
    assert not _is_safe_name("foo/bar")
    assert _is_safe_name("valid-rule-name")


def test_resolve_path_rejects_parent_refs(tmp_path: Path) -> None:
    root = tmp_path
    assert _resolve_path(root, Path("rules/foo.md")) is not None
    assert _resolve_path(root, Path("../outside.md")) is None


def test_audit_redacts_sensitive_keys(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path)
    logger.log("test", {"api_key": "secret123", "user": "moataz"})
    log_file = tmp_path / "state" / "audit.log"
    text = log_file.read_text(encoding="utf-8")
    assert "secret123" not in text
    assert "[REDACTED]" in text
    assert "moataz" in text


def test_bad_plugin_on_load_executes() -> None:
    """Cover the _BadPlugin.on_load pass statement (line 16)."""
    from unittest.mock import MagicMock

    plugin = _BadPlugin(MagicMock())
    plugin.on_load()  # should not raise
