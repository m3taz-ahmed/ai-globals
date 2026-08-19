#!/usr/bin/env python3
"""Plugin manager and base interface for aiZee extensions."""

from __future__ import annotations

import ast
import fnmatch
import functools
import importlib.util
import threading
import warnings
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import yaml

import config
from aizee_mcp._compat import Resource  # pyright: ignore[reportAttributeAccessIssue]
from runtime.schemas import AizeeError, ErrorSeverity

if TYPE_CHECKING:
    from memory.store import MemoryStore
    from runtime.kernel import Kernel


class PluginSandboxError(AizeeError):
    """Raised when a plugin action is blocked by the sandbox."""

    def __init__(self, plugin_name: str, action: str) -> None:
        super().__init__(
            "PLUGIN_SANDBOX_BLOCKED",
            f"Plugin '{plugin_name}' action '{action}' blocked by sandbox",
            ErrorSeverity.MEDIUM,
            {"plugin_name": plugin_name, "action": action},
        )


_DENYLISTED_MODULES: set[str] = {
    "os", "subprocess", "sys", "shutil", "socket", "requests", "urllib", "http",
    "ftplib", "telnetlib", "smtplib", "ctypes", "mmap", "signal", "pickle", "marshal",
    "importlib", "types", "builtins", "code", "codeop", "runpy", "webbrowser",
    "multiprocessing", "concurrent",
}

# Builtins names that are dangerous when imported/called directly.
_DENYLISTED_BUILTIN_NAMES: set[str] = {
    "__import__", "globals", "locals", "vars", "dir", "type",
    "classmethod", "staticmethod",
}

_DANGEROUS_CALLS: set[str] = {
    "eval", "exec", "compile", "open", "__import__", "getattr", "setattr",
    "literal_eval",
}


def _is_plugin_source_safe(source: str, filename: str) -> tuple[bool, str]:
    """Statically scan plugin source for imports and calls that break the sandbox."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        return False, f"Syntax error: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            for name in names:
                root = name.split(".")[0]
                if root in _DENYLISTED_MODULES:
                    return False, f"Blocked import of '{name}' in {filename}"
                # Block importing dangerous builtin names from builtins module.
                if isinstance(node, ast.ImportFrom) and node.module == "builtins" and name in _DENYLISTED_BUILTIN_NAMES:
                    return False, f"Blocked import of '{name}' from builtins in {filename}"
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _DANGEROUS_CALLS:
                return False, f"Blocked call to '{func.id}' in {filename}"
            if isinstance(func, ast.Attribute) and func.attr in _DANGEROUS_CALLS:
                return False, f"Blocked call to '.{func.attr}' in {filename}"
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__") and len(node.attr) > 4:
                return False, f"Blocked dunder attribute access '{node.attr}' in {filename}"
        elif isinstance(node, ast.Subscript):
            # Block __builtins__['eval'] style bypasses
            if isinstance(node.value, ast.Name) and node.value.id == "__builtins__":
                return False, f"Blocked __builtins__ subscript in {filename}"
    return True, ""


class AIOSPlugin(ABC):
    """Base interface for aiZee plugins.

    Plugins are loaded by the kernel after the runtime is initialized and may
    expose MCP tools and resources.

    Two-phase lifecycle (inspired by Filament's Plugin interface):
    1. ``register()`` — called during registration phase (before any plugin boots).
       Register resources, pages, widgets, livewire components here.
    2. ``boot()`` — called after ALL plugins are registered.
       Add authorization gates, configure global defaults, register assets here.

    Legacy single-phase ``on_load()`` is still supported: if a plugin does not
    override ``register()``/``boot()``, ``on_load()`` is called during the
    registration phase for backward compatibility.
    """

    name: str = ""
    version: str = "0.1.0"
    loaded: bool = False

    def __init__(self, kernel: Kernel, memory: MemoryStore | None = None) -> None:
        self.kernel = kernel
        self.memory = memory

    @abstractmethod
    def on_load(self) -> None:
        """Called once when the plugin is loaded (legacy single-phase)."""

    def register(self) -> None:
        """Registration phase: register components BEFORE any plugin boots.

        Override for two-phase lifecycle. Default: calls ``on_load()`` for
        backward compatibility with legacy plugins.
        """
        self.on_load()

    def boot(self) -> None:
        """Boot phase: called after ALL plugins are registered.

        Override for two-phase lifecycle. Default: no-op.
        Add authorization gates, configure global defaults, register assets.
        """
        return None

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
        self.allowed: set[str] = set()
        self.denied: set[str] = set(self.DENIED_DEFAULT)
        # Resource-based permissions: entries like "Write:/tmp/*" or "Read:/var/log/*"
        self.resource_patterns: dict[str, list[str]] = {}
        for perm in (permissions or []):
            if ":" in perm:
                action_part, resource_part = perm.split(":", 1)
                if action_part and resource_part:
                    self.resource_patterns.setdefault(action_part, []).append(resource_part)
                else:
                    self.allowed.add(perm)
            else:
                self.allowed.add(perm)

    def is_allowed(self, action: str) -> bool:
        return action not in self.denied and (not self.allowed or action in self.allowed)

    def is_resource_allowed(self, action: str, resource: str) -> bool:
        """Check whether *action* on *resource* is permitted via glob patterns.

        Permissions like ``"Write:/tmp/*"`` or ``"Read:/var/log/*"`` are matched
        against the resource path using :func:`fnmatch.fnmatch`. Explicit
        resource-based grants override the default denied set for matching
        resources. If no resource-based permissions are configured for the
        action, falls back to :meth:`is_allowed` for plain action-level checks.
        """
        patterns = self.resource_patterns.get(action)
        if patterns:
            # Explicit resource grant overrides default denial for matching paths.
            return any(fnmatch.fnmatch(resource, pat) for pat in patterns)
        # No resource patterns for this action — fall back to action-level check.
        return self.is_allowed(action)

    def wrap(self, fn: Callable[..., Any], plugin_name: str) -> Callable[..., Any]:
        @functools.wraps(fn)
        def guarded(*args: Any, **kwargs: Any) -> Any:
            action = kwargs.get("action") or (args[0] if args else "unknown")
            if not self.is_allowed(str(action)):
                raise PluginSandboxError(plugin_name, str(action))
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
        """Load the plugin module using its package path after a static safety scan."""
        init_file = self.plugins_dir / name / "__init__.py"
        if not init_file.is_file():
            return None
        source = init_file.read_text(encoding="utf-8")
        safe, reason = _is_plugin_source_safe(source, str(init_file))
        if not safe:
            warnings.warn(f"Plugin '{name}' blocked by sandbox: {reason}", stacklevel=2)
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
        """Return enabled plugin classes from the plugins directory.

        If ``plugins.yaml`` exists and lists enabled plugins, only those are
        loaded (explicit mode). If ``plugins.yaml`` is missing or empty, all
        subdirectories of ``plugins/`` with a valid ``__init__.py`` are
        auto-discovered (auto-discovery mode).
        """
        if not self.plugins_dir.is_dir():
            return []

        enabled = self._enabled_plugins()
        discovered: list[tuple[str, type[AIOSPlugin]]] = []
        for candidate in self.plugins_dir.iterdir():
            if not candidate.is_dir() or candidate.name.startswith("_") or candidate.name.startswith("."):
                continue
            # In explicit mode, only load plugins listed in plugins.yaml
            if enabled and candidate.name not in enabled:
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

    def _register_phase(self, memory: MemoryStore | None = None) -> None:
        """Phase 1: instantiate and register all discovered plugins."""
        for name, cls in self._discover_plugins():
            guard = self._guard_for(name)
            try:
                plugin = cls(self.kernel, memory)
                plugin.register()
                self._plugins[name] = plugin
                self._guards[name] = guard
            except Exception as exc:
                warnings.warn(
                    f"Plugin '{name}' failed to register: {exc}", stacklevel=2
                )

    def _boot_phase(self) -> None:
        """Phase 2: boot all registered plugins."""
        for name, plugin in self._plugins.items():
            try:
                plugin.boot()
            except Exception as exc:
                warnings.warn(
                    f"Plugin '{name}' failed to boot: {exc}", stacklevel=2
                )

    def load_all(self, memory: MemoryStore | None = None) -> None:
        """Load all enabled plugins using two-phase register/boot lifecycle.

        Phase 1 (register): instantiate each plugin and call ``register()``.
        Phase 2 (boot): call ``boot()`` on all successfully registered plugins.
        This ensures no plugin assumes another is booted during registration.
        """
        with self._lock:
            if self._loaded:
                return
            self._register_phase(memory)
            self._boot_phase()
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
