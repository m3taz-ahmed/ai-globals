#!/usr/bin/env python3
"""Plugin manager and base interface for AI Global OS extensions."""

from __future__ import annotations

import importlib.util
import threading
import warnings
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from mcp.server.fastmcp.resources import Resource

import config

if TYPE_CHECKING:
    from memory.store import MemoryStore
    from runtime.kernel import Kernel


class AIOSPlugin(ABC):
    """Base interface for AI Global OS plugins.

    Plugins are loaded by the kernel after the runtime is initialized and may
    expose MCP tools and resources.
    """

    name: str = ""
    version: str = "0.1.0"

    def __init__(self, kernel: Kernel, memory: MemoryStore | None = None) -> None:
        self.kernel = kernel
        self.memory = memory

    @abstractmethod
    def on_load(self) -> None:
        """Called once when the plugin is loaded."""

    def register_mcp_tools(self) -> list[Callable[..., Any]]:
        """Return a list of callable tools to register with the MCP server."""
        return []

    def register_mcp_resources(self) -> list[Resource]:
        """Return a list of Resource instances to register with the MCP server."""
        return []


class PluginManager:
    """Discovers, loads, and manages AIOS plugins."""

    def __init__(self, kernel: Kernel, root: Path | None = None) -> None:
        self.kernel = kernel
        self.root = root or config.discover_root()
        self.config_path = self.root / "plugins.yaml"
        self.plugins_dir = self.root / "plugins"
        self._plugins: dict[str, AIOSPlugin] = {}
        self._lock = threading.Lock()
        self._loaded = False

    def _load_config(self) -> dict[str, Any]:
        if self.config_path.exists():
            data = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
            return data
        return {}

    def _enabled_plugins(self) -> set[str]:
        """Return explicitly enabled plugin names from plugins.yaml."""
        config_data = self._load_config()
        plugins_cfg = config_data.get("plugins", {})
        enabled: set[str] = set()
        for name, cfg in plugins_cfg.items():
            if isinstance(cfg, dict) and cfg.get("enabled", False):
                enabled.add(name)
        return enabled

    def _load_plugin_module(self, name: str) -> Any | None:
        """Load the plugin module using its package path."""
        init_file = self.plugins_dir / name / "__init__.py"
        if not init_file.is_file():
            return None
        spec = importlib.util.spec_from_file_location(f"plugins.{name}", init_file)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            warnings.warn(f"Plugin '{name}' failed to load: {exc}", stacklevel=2)
            return None
        return module

    def _discover_plugins(self) -> list[tuple[str, type[AIOSPlugin]]]:
        """Return enabled plugin classes from the plugins directory."""
        if not self.plugins_dir.is_dir():
            return []

        enabled = self._enabled_plugins()
        discovered: list[tuple[str, type[AIOSPlugin]]] = []
        for candidate in self.plugins_dir.iterdir():
            if not candidate.is_dir() or candidate.name not in enabled:
                continue
            module = self._load_plugin_module(candidate.name)
            if module is None:
                continue
            plugin_cls = getattr(module, "Plugin", None)
            if plugin_cls is None or not isinstance(plugin_cls, type) or not issubclass(plugin_cls, AIOSPlugin):
                warnings.warn(f"Plugin '{candidate.name}' has no valid Plugin class", stacklevel=2)
                continue
            discovered.append((candidate.name, plugin_cls))
        return discovered

    def load_all(self, memory: MemoryStore | None = None) -> None:
        """Load all enabled plugins and call their on_load hooks."""
        with self._lock:
            if self._loaded:
                return
            for name, cls in self._discover_plugins():
                try:
                    plugin = cls(self.kernel, memory)
                    plugin.on_load()
                    self._plugins[name] = plugin
                except Exception as exc:
                    warnings.warn(f"Plugin '{name}' failed to initialize: {exc}", stacklevel=2)
            self._loaded = True

    def get_tools(self) -> list[Callable[..., Any]]:
        """Aggregate all tools exposed by loaded plugins."""
        tools: list[Callable[..., Any]] = []
        for plugin in self._plugins.values():
            tools.extend(plugin.register_mcp_tools())
        return tools

    def get_resources(self) -> list[Resource]:
        """Aggregate all resources exposed by loaded plugins."""
        resources: list[Resource] = []
        for plugin in self._plugins.values():
            resources.extend(plugin.register_mcp_resources())
        return resources

    def list_plugins(self) -> list[dict[str, str]]:
        """Return a list of loaded plugin names and versions."""
        return [
            {"name": name, "version": getattr(plugin, "version", "0.1.0")}
            for name, plugin in self._plugins.items()
        ]
