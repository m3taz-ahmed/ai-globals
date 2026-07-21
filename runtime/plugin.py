#!/usr/bin/env python3
"""Plugin manager and base interface for AI Global OS extensions."""

from __future__ import annotations

import importlib.util
import threading
import warnings
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

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


class PluginGuard:
    """Enforces action permissions for plugins."""

    DENIED_DEFAULT: ClassVar[set[str]] = {"Bash", "RunCommand", "Delete", "Eval", "Write", "Shell"}

    def __init__(self, permissions: list[str] | None = None) -> None:
        self.allowed: set[str] = set(permissions) if permissions else set()
        self.denied: set[str] = set(self.DENIED_DEFAULT)

    def is_allowed(self, action: str) -> bool:
        return action not in self.denied and (not self.allowed or action in self.allowed)

    def wrap(self, fn: Callable[..., Any], plugin_name: str) -> Callable[..., Any]:
        def guarded(*args: Any, **kwargs: Any) -> Any:
            action = kwargs.get("action") or (args[0] if args else "unknown")
            if not self.is_allowed(str(action)):
                raise RuntimeError(f"Plugin '{plugin_name}' action '{action}' blocked by sandbox")
            return fn(*args, **kwargs)

        return guarded


class PluginManager:
    """Discovers, loads, and manages AIOS plugins."""

    def __init__(self, kernel: Kernel, root: Path | None = None) -> None:
        self.kernel = kernel
        self.root = root or config.discover_root()
        self.config_path = self.root / "plugins.yaml"
        self.plugins_dir = self.root / "plugins"
        self._plugins: dict[str, AIOSPlugin] = {}
        self._guards: dict[str, PluginGuard] = {}
        self._lock = threading.Lock()
        self._loaded = False

    def _load_config(self) -> dict[str, Any]:
        if self.config_path.exists():
            data = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
            return data
        return {}

    def _plugin_configs(self) -> dict[str, dict[str, Any]]:
        """Return plugin configs from plugins.yaml."""
        config_data = self._load_config()
        plugins_cfg = config_data.get("plugins", {})
        valid: dict[str, dict[str, Any]] = {}
        for name, cfg in plugins_cfg.items():
            if isinstance(cfg, dict) and cfg.get("enabled", False):
                valid[name] = cfg
        return valid

    def _enabled_plugins(self) -> set[str]:
        """Return explicitly enabled plugin names from plugins.yaml."""
        return set(self._plugin_configs().keys())

    def _guard_for(self, name: str) -> PluginGuard:
        cfg = self._plugin_configs().get(name, {})
        return PluginGuard(cfg.get("permissions"))

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
                guard = self._guard_for(name)
                try:
                    plugin = cls(self.kernel, memory)
                    plugin.on_load()
                    self._plugins[name] = plugin
                    self._guards[name] = guard
                except Exception as exc:
                    warnings.warn(f"Plugin '{name}' failed to initialize: {exc}", stacklevel=2)
            self._loaded = True

    def get_tools(self) -> list[Callable[..., Any]]:
        """Aggregate all sandboxed tools exposed by loaded plugins."""
        tools: list[Callable[..., Any]] = []
        for name, plugin in self._plugins.items():
            guard = self._guards.get(name, PluginGuard())
            for tool in plugin.register_mcp_tools():
                tools.append(guard.wrap(tool, name))
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
