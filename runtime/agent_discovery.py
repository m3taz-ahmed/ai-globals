#!/usr/bin/env python3
"""Agent discovery — detect local AI agent configurations.

Inspired by Preloop's ``preloop agents discover``: scans common
locations for AI coding assistant configs (Claude Code, Cursor, Cline,
Windsurf, Aider, Devin) and reports their status. This is read-only —
it does not modify any configs.

Usage::

    from runtime.agent_discovery import AgentDiscovery
    discovery = AgentDiscovery()
    agents = discovery.discover()
    for a in agents:
        print(f"{a.name}: {a.config_path} ({'active' if a.is_active else 'inactive'})")
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar


@dataclass
class DiscoveredAgent:
    """A locally-detected AI agent configuration."""

    name: str
    kind: str  # claude_code, cursor, cline, windsurf, aider, devin, generic
    config_path: Path
    is_active: bool = False
    mcp_servers: list[str] = field(default_factory=list)
    model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentDiscovery:
    """Discovers local AI agent configurations.

    Scans well-known config locations on the current platform and reports
    what agents are installed. Does not modify anything.
    """

    # (kind, name, relative_path_from_home, is_active_check)
    _TARGETS: ClassVar[list[tuple[str, str, str]]] = [
        ("claude_code", "Claude Code", ".claude/settings.json"),
        ("claude_code", "Claude Code (project)", ".claude.json"),
        ("cursor", "Cursor", ".cursor/settings.json"),
        ("cursor", "Cursor (rules)", ".cursor/rules"),
        ("cline", "Cline", ".cline/rules"),
        ("windsurf", "Windsurf", ".windsurf/settings.json"),
        ("windsurf", "Windsurf (rules)", ".windsurfrules"),
        ("aider", "Aider", ".aider.conf.yml"),
        ("devin", "Devin", ".devin/config.json"),
        ("devin", "Devin (mcp)", ".devin/mcp_config.json"),
        ("generic", "AGENTS.md", "AGENTS.md"),
    ]

    def __init__(self, home: Path | None = None, project_root: Path | None = None) -> None:
        self.home = home or Path(os.path.expanduser("~"))
        self.project_root = project_root or Path.cwd()

    def discover(self) -> list[DiscoveredAgent]:
        """Scan home + project root for agent configs."""
        found: list[DiscoveredAgent] = []
        for kind, name, rel in self._TARGETS:
            for base in (self.home, self.project_root):
                path = base / rel
                if path.exists():
                    agent = self._parse_config(kind, name, path)
                    if agent is not None:
                        found.append(agent)
        # Deduplicate by (kind, config_path).
        seen: set[tuple[str, str]] = set()
        unique: list[DiscoveredAgent] = []
        for a in found:
            key = (a.kind, str(a.config_path))
            if key not in seen:
                seen.add(key)
                unique.append(a)
        return unique

    def _parse_config(self, kind: str, name: str, path: Path) -> DiscoveredAgent | None:
        """Parse a config file and extract agent info."""
        agent = DiscoveredAgent(
            name=name,
            kind=kind,
            config_path=path,
            is_active=True,
        )
        if path.is_dir():
            # Rules directory — count files.
            count = sum(1 for _ in path.iterdir() if _.is_file())
            agent.metadata["file_count"] = count
            return agent
        if path.suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return agent
            # Extract MCP servers if present.
            mcp = data.get("mcpServers") or data.get("mcp_servers") or {}
            if isinstance(mcp, dict):
                agent.mcp_servers = list(mcp.keys())
            model = data.get("model") or data.get("defaultModel")
            if isinstance(model, str):
                agent.model = model
            return agent
        if path.suffix == ".yml" or path.suffix == ".yaml":
            try:
                import yaml

                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception:
                return agent
            model = data.get("model")
            if isinstance(model, str):
                agent.model = model
            return agent
        # Plain text (AGENTS.md, .windsurfrules) — just mark active.
        return agent

    def report(self) -> str:
        """Human-readable report of discovered agents."""
        agents = self.discover()
        if not agents:
            return "No AI agent configurations found."
        lines = [f"Discovered {len(agents)} agent configuration(s):"]
        for a in agents:
            model_str = f" [model={a.model}]" if a.model else ""
            mcp_str = f" [mcp={','.join(a.mcp_servers)}]" if a.mcp_servers else ""
            lines.append(f"  - {a.name} ({a.kind}): {a.config_path}{model_str}{mcp_str}")
        return "\n".join(lines)
