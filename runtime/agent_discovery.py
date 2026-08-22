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
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from runtime.service_catalog import (
    CATALOG_API_VERSION,
    KIND_SKILL,
    REL_DEPENDS_ON,
    REL_OWNED_BY,
    REL_PART_OF,
    REL_PROVIDES_CAPABILITY,
    CatalogEntity,
    CatalogStore,
    EntityMeta,
    EntityRelation,
)

logger = logging.getLogger(__name__)


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
                logger.debug("Failed to parse agent config %s", path, exc_info=True)
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


# ---------------------------------------------------------------------------
# Catalog-based discovery (Backstage Entity Catalog integration)
#
# Additive functions that query a CatalogStore by labels, capabilities, and
# convert skill .md files into CatalogEntity instances with relations.
# ---------------------------------------------------------------------------


def discover_by_labels(
    catalog: CatalogStore, labels: dict[str, str]
) -> list[CatalogEntity]:
    """Discover entities matching ALL given labels (AND semantics).

    Returns entities that have every key=value pair in their metadata.labels.
    """
    if not labels:
        return []
    result: list[CatalogEntity] = []
    for entity in catalog.all():
        if all(
            entity.metadata.labels.get(key) == value
            for key, value in labels.items()
        ):
            result.append(entity)
    return result


def discover_by_capability(
    catalog: CatalogStore, capability: str
) -> list[CatalogEntity]:
    """Discover entities that provide a specific capability.

    Matches entities with a ``providesCapability`` relation whose
    target_ref equals the capability, or whose spec lists the capability.
    """
    result: list[CatalogEntity] = []
    for entity in catalog.all():
        # Check providesCapability relations.
        for rel in entity.relations:
            if rel.type == REL_PROVIDES_CAPABILITY and rel.target_ref == capability:
                result.append(entity)
                break
        else:
            # Check spec.capabilities list as a fallback.
            caps = entity.spec.get("capabilities")
            if isinstance(caps, list) and capability in caps:
                result.append(entity)
    return result


def skill_to_entity(skill_path: Path, name: str) -> CatalogEntity:
    """Convert a skill .md file to a CatalogEntity with relations.

    Parses YAML frontmatter (between ``---`` markers) for metadata. Adds:
    - ``partOf`` relation to ``workflow:default/aizee`` (the catalog root)
    - ``ownedBy`` relation to ``persona:default/{persona}`` if frontmatter.persona
    - ``providesCapability`` relation for each frontmatter.capabilities entry
    - ``dependsOn`` relation for each frontmatter.depends_on entry

    Frontmatter is optional; missing fields fall back to heuristics.
    """
    description = ""
    frontmatter: dict[str, Any] = {}
    try:
        text = skill_path.read_text(encoding="utf-8")
        frontmatter, body = _parse_frontmatter(text)
        description = (
            frontmatter.get("description")
            or _first_prose_line(body)
        )
    except OSError:
        logger.debug("Failed to read skill file %s", skill_path, exc_info=True)

    tags = _split_list(frontmatter.get("tags"))
    if not tags:
        tags = ["skill"]

    meta = EntityMeta(
        name=name,
        namespace="default",
        title=str(frontmatter.get("title") or name.replace("-", " ").title()),
        description=description,
        labels={"kind": "skill"},
        tags=tags,
    )

    relations: list[EntityRelation] = [
        EntityRelation(type=REL_PART_OF, target_ref="workflow:default/aizee"),
    ]

    persona = frontmatter.get("persona")
    if isinstance(persona, str) and persona:
        relations.append(
            EntityRelation(type=REL_OWNED_BY, target_ref=f"persona:default/{persona}")
        )
    for dep in _split_list(frontmatter.get("depends_on")):
        relations.append(EntityRelation(type=REL_DEPENDS_ON, target_ref=dep))
    for cap in _split_list(frontmatter.get("capabilities")):
        relations.append(EntityRelation(type=REL_PROVIDES_CAPABILITY, target_ref=cap))

    spec: dict[str, Any] = {"file_path": str(skill_path)}
    triggers = _split_list(frontmatter.get("triggers"))
    if triggers:
        spec["triggers"] = triggers
    tech_stack = _split_list(frontmatter.get("tech_stack"))
    if tech_stack:
        spec["tech_stack"] = tech_stack

    return CatalogEntity(
        api_version=CATALOG_API_VERSION,
        kind=KIND_SKILL,
        metadata=meta,
        spec=spec,
        relations=relations,
    )


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from body. Returns (frontmatter, body)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx == -1:
        return {}, text
    fm_text = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :])
    try:
        import yaml

        data = yaml.safe_load(fm_text) or {}
        if isinstance(data, dict):
            return data, body
    except Exception:
        logger.debug("Failed to parse frontmatter", exc_info=True)
    return {}, body


def _first_prose_line(body: str) -> str:
    """Return the first non-empty, non-heading line from body."""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("["):
            return stripped
    return ""


def _split_list(value: Any) -> list[str]:
    """Normalize a frontmatter value into a list of non-empty strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []
