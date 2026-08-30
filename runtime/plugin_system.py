"""Plugin System — bundles skills, agents, commands, hooks, and MCP servers.

Inspired by Claude Code's plugin architecture. A plugin is a self-contained
package that groups related capabilities:

- **Skills** — SKILL.md instruction packs loaded progressively
- **Agents** — subagent definitions for specialized tasks
- **Commands** — slash commands (e.g., /design, /taste, /qa)
- **Hooks** — lifecycle hooks (UserPromptSubmit, PreToolUse, PostToolUse, Stop)
- **MCP Servers** — external tool integrations via Model Context Protocol

The registry discovers plugins from a ``plugins/`` directory, validates their
manifest, and loads them on demand. Plugins are isolated — a broken plugin
never crashes the kernel.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar

from runtime.schemas import AizeeError, ErrorSeverity

_logger = logging.getLogger(__name__)


class PluginType(str, Enum):
    """Type of plugin capability."""

    SKILL = "skill"
    AGENT = "agent"
    COMMAND = "command"
    HOOK = "hook"
    MCP_SERVER = "mcp_server"
    BUNDLE = "bundle"  # Contains multiple capability types


class HookPhase(str, Enum):
    """Lifecycle phases where hooks can fire."""

    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    STOP = "Stop"


class PluginStatus(str, Enum):
    """Lifecycle status of a plugin."""

    DISCOVERED = "discovered"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginManifest:
    """Parsed plugin manifest (plugin.json)."""

    name: str
    version: str
    description: str
    type: PluginType = PluginType.BUNDLE
    author: str = ""
    homepage: str = ""
    license: str = "MIT"
    skills: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    hooks: dict[str, str] = field(default_factory=dict)  # phase → script path
    mcp_servers: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    personas: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PluginManifest:
        """Parse a plugin.json dict into a PluginManifest."""
        name = str(data.get("name", ""))
        version = str(data.get("version", "0.0.0"))
        description = str(data.get("description", ""))
        if not name or not description:
            raise PluginError("Plugin manifest must have 'name' and 'description'")
        ptype = PluginType(str(data.get("type", "bundle")))
        hooks_raw = data.get("hooks", {})
        hooks: dict[str, str] = {}
        if isinstance(hooks_raw, dict):
            for k, v in hooks_raw.items():
                hooks[str(k)] = str(v)
        return cls(
            name=name,
            version=version,
            description=description,
            type=ptype,
            author=str(data.get("author", "")),
            homepage=str(data.get("homepage", "")),
            license=str(data.get("license", "MIT")),
            skills=_as_str_list(data.get("skills", [])),
            agents=_as_str_list(data.get("agents", [])),
            commands=_as_str_list(data.get("commands", [])),
            hooks=hooks,
            mcp_servers=_as_str_list(data.get("mcp_servers", [])),
            dependencies=_as_str_list(data.get("dependencies", [])),
            keywords=_as_str_list(data.get("keywords", [])),
            personas=_as_str_list(data.get("personas", [])),
        )


def _as_str_list(value: object) -> list[str]:
    """Safely convert a value to a list of strings."""
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [value]
    return []


@dataclass
class Plugin:
    """A loaded plugin instance."""

    manifest: PluginManifest
    path: Path
    status: PluginStatus = PluginStatus.DISCOVERED
    error: str | None = None

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def is_active(self) -> bool:
        return self.status == PluginStatus.ACTIVE


class PluginRegistry:
    """Discovers, validates, and manages plugins from a directory.

    Plugins live in ``<root>/plugins/<plugin-name>/plugin.json``. The registry
    scans the directory, parses manifests, and tracks lifecycle status. Plugins
    are loaded lazily — only when their skills/commands are first invoked.
    """

    MANIFEST_NAME: ClassVar[str] = "plugin.json"
    SKILL_FILE: ClassVar[str] = "SKILL.md"

    def __init__(self, plugins_dir: Path | None = None) -> None:
        """Initialize the registry.

        Args:
            plugins_dir: Directory to scan for plugins. Defaults to
                ``<root>/plugins/``.
        """
        self._plugins: dict[str, Plugin] = {}
        self._plugins_dir = plugins_dir
        self._keyword_index: dict[str, list[str]] = {}  # keyword → plugin names
        self._persona_index: dict[str, list[str]] = {}  # persona → plugin names

    def discover(self, plugins_dir: Path | None = None) -> int:
        """Scan the plugins directory and register all valid plugins.

        Returns the number of plugins discovered.
        """
        scan_dir = plugins_dir or self._plugins_dir
        if scan_dir is None or not scan_dir.exists():
            return 0

        count = 0
        for plugin_dir in sorted(scan_dir.iterdir()):
            if not plugin_dir.is_dir():
                continue
            manifest_path = plugin_dir / self.MANIFEST_NAME
            if not manifest_path.exists():
                continue
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest = PluginManifest.from_dict(data)
                plugin = Plugin(manifest=manifest, path=plugin_dir)
                self._plugins[manifest.name] = plugin
                self._index_plugin(plugin)
                count += 1
            except (json.JSONDecodeError, PluginError, OSError):
                # Skip broken plugins silently — isolation
                continue

        return count

    def get(self, name: str) -> Plugin | None:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self, *, status: PluginStatus | None = None) -> list[Plugin]:
        """List all plugins, optionally filtered by status."""
        plugins = list(self._plugins.values())
        if status is not None:
            plugins = [p for p in plugins if p.status == status]
        return plugins

    def activate(self, name: str) -> bool:
        """Activate a plugin by name. Returns True on success."""
        plugin = self._plugins.get(name)
        if plugin is None:
            return False
        # Check dependencies
        for dep in plugin.manifest.dependencies:
            dep_plugin = self._plugins.get(dep)
            if dep_plugin is None or not dep_plugin.is_active:
                plugin.status = PluginStatus.ERROR
                plugin.error = f"Unmet dependency: {dep}"
                return False
        plugin.status = PluginStatus.ACTIVE
        plugin.error = None
        return True

    def deactivate(self, name: str) -> bool:
        """Deactivate a plugin by name."""
        plugin = self._plugins.get(name)
        if plugin is None:
            return False
        plugin.status = PluginStatus.DISCOVERED
        return True

    def find_by_keyword(self, keyword: str) -> list[Plugin]:
        """Find plugins matching a keyword (case-insensitive)."""
        kw_lower = keyword.lower()
        names: set[str] = set()
        for indexed_kw, plugin_names in self._keyword_index.items():
            if kw_lower in indexed_kw.lower():
                names.update(plugin_names)
        return [self._plugins[n] for n in names if n in self._plugins]

    def find_by_persona(self, persona: str) -> list[Plugin]:
        """Find plugins relevant to a persona."""
        names = self._persona_index.get(persona, [])
        return [self._plugins[n] for n in names if n in self._plugins]

    def load_skill(self, plugin_name: str, skill_name: str) -> str | None:
        """Load a skill's SKILL.md content from a plugin.

        Returns the file content, or None if not found.
        """
        plugin = self._plugins.get(plugin_name)
        if plugin is None or not plugin.is_active:
            return None
        skill_path = plugin.path / "skills" / skill_name / self.SKILL_FILE
        if not skill_path.exists():
            skill_path = plugin.path / "skills" / f"{skill_name}.md"
        if not skill_path.exists():
            return None
        try:
            return skill_path.read_text(encoding="utf-8")
        except OSError:
            return None

    def run_hook(self, plugin_name: str, phase: HookPhase, context: dict[str, object]) -> str | None:
        """Run a hook script for a plugin. Returns the script output or None.

        Executes the hook via ``subprocess.run`` with a 30-second timeout.
        Hook failures are logged but never crash the OS — a broken plugin
        is isolated from the kernel.
        """
        plugin = self._plugins.get(plugin_name)
        if plugin is None or not plugin.is_active:
            return None
        hook_path = plugin.manifest.hooks.get(phase.value)
        if hook_path is None:
            return None
        full_path = plugin.path / hook_path
        if not full_path.exists():
            _logger.warning(
                "Hook script not found for plugin %s phase %s: %s",
                plugin_name, phase.value, full_path,
            )
            return None
        try:
            result = subprocess.run(
                [sys.executable, str(full_path)],
                input=json.dumps(context),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired:
            _logger.warning(
                "Hook script timed out for plugin %s phase %s",
                plugin_name, phase.value,
            )
            return None
        except Exception as exc:
            _logger.warning(
                "Hook script failed for plugin %s phase %s: %s",
                plugin_name, phase.value, exc,
            )
            return None
        if result.returncode != 0:
            _logger.warning(
                "Hook script exited with code %d for plugin %s phase %s: %s",
                result.returncode, plugin_name, phase.value, result.stderr.strip(),
            )
            return None
        _logger.debug(
            "Hook script succeeded for plugin %s phase %s",
            plugin_name, phase.value,
        )
        return result.stdout.strip() or None

    def stats(self) -> dict[str, int]:
        """Return registry statistics."""
        status_counts: dict[str, int] = {}
        for plugin in self._plugins.values():
            key = plugin.status.value
            status_counts[key] = status_counts.get(key, 0) + 1
        return {
            "total": len(self._plugins),
            "active": sum(1 for p in self._plugins.values() if p.is_active),
            **status_counts,
        }

    def _index_plugin(self, plugin: Plugin) -> None:
        """Index a plugin's keywords and personas for fast lookup."""
        for kw in plugin.manifest.keywords:
            self._keyword_index.setdefault(kw.lower(), []).append(plugin.name)
        for persona in plugin.manifest.personas:
            self._persona_index.setdefault(persona, []).append(plugin.name)


# -- Exception -----------------------------------------------------------------


class PluginError(AizeeError):
    """Raised when a plugin operation fails."""

    def __init__(self, message: str, context: dict[str, object] | None = None) -> None:
        super().__init__("PLUGIN_ERROR", message, ErrorSeverity.MEDIUM, context)
