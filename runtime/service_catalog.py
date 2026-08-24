"""Multi-index service/skill catalog for aiZee.

Inspired by Floci's ``ServiceDescriptor`` record + ``ServiceCatalog``
multi-index lookup pattern. Provides fast lookup of skills, workflows,
and tech-stack entries by multiple keys (name, persona, trigger, stack).

The catalog is additive — existing ``SkillResolver`` is NOT modified.
New code can use the catalog for batch discovery; legacy code keeps working.

Usage::

    from runtime.service_catalog import ServiceDescriptor, ServiceCatalog

    catalog = ServiceCatalog([
        ServiceDescriptor(name="flutter-architect", kind="skill",
                          personas=["MOBILE", "UX"], triggers=["flutter", "dart"],
                          tech_stack=["flutter"]),
    ])
    matches = catalog.by_persona("MOBILE")  # → [ServiceDescriptor(...)]
    match = catalog.match_trigger("build a flutter app")  # → Optional[...]
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ServiceDescriptor:
    """Describes a catalog entry (skill, workflow, or tech-stack reference).

    Inspired by Floci's ``ServiceDescriptor`` record. Immutable so it can
    be safely shared across threads and used as dict keys via identity.
    """

    name: str
    kind: str  # "skill" | "workflow" | "tech-stack" | "rule"
    enabled: bool = True
    include_in_status: bool = True
    personas: frozenset[str] = field(default_factory=frozenset)
    triggers: frozenset[str] = field(default_factory=frozenset)
    tech_stack: frozenset[str] = field(default_factory=frozenset)
    file_path: str = ""
    description: str = ""
    context7_id: str = ""
    lords: frozenset[str] = field(default_factory=frozenset)

    def supports_persona(self, persona: str) -> bool:
        """True if this descriptor serves the given persona."""
        return persona in self.personas

    def supports_tech(self, tech: str) -> bool:
        """True if this descriptor covers the given tech-stack."""
        return tech in self.tech_stack


class ServiceCatalog:
    """Multi-index catalog for fast descriptor lookup.

    Inspired by Floci's ``ServiceCatalog``: builds multiple indexes at
    construction time for O(1) lookups by different keys.

    Indexes:
    - by_name: exact name → descriptor
    - by_kind: kind → list of descriptors
    - by_persona: persona → list of descriptors
    - by_trigger: trigger keyword → list of descriptors
    - by_tech_stack: tech-stack → list of descriptors
    - by_lord: lord skill → list of descriptors
    """

    def __init__(self, descriptors: list[ServiceDescriptor]) -> None:
        self._all: tuple[ServiceDescriptor, ...] = tuple(descriptors)
        self._by_name: dict[str, ServiceDescriptor] = {}
        self._by_kind: dict[str, list[ServiceDescriptor]] = {}
        self._by_persona: dict[str, list[ServiceDescriptor]] = {}
        self._by_trigger: dict[str, list[ServiceDescriptor]] = {}
        self._by_tech: dict[str, list[ServiceDescriptor]] = {}
        self._by_lord: dict[str, list[ServiceDescriptor]] = {}
        self._status_descriptors: list[ServiceDescriptor] = []
        self._build_indexes()

    def _build_indexes(self) -> None:
        for desc in self._all:
            # by_name (last one wins if duplicate — matches Floci behavior)
            self._by_name[desc.name] = desc

            # by_kind
            self._by_kind.setdefault(desc.kind, []).append(desc)

            # by_persona
            for persona in desc.personas:
                self._by_persona.setdefault(persona, []).append(desc)

            # by_trigger
            for trigger in desc.triggers:
                key = trigger.lower()
                self._by_trigger.setdefault(key, []).append(desc)

            # by_tech_stack
            for tech in desc.tech_stack:
                key = tech.lower()
                self._by_tech.setdefault(key, []).append(desc)

            # by_lord
            for lord in desc.lords:
                self._by_lord.setdefault(lord, []).append(desc)

            # status descriptors (only enabled + include_in_status)
            if desc.enabled and desc.include_in_status:
                self._status_descriptors.append(desc)

    def by_name(self, name: str) -> ServiceDescriptor | None:
        """Lookup by exact name. Returns None if not found."""
        return self._by_name.get(name)

    def by_kind(self, kind: str) -> list[ServiceDescriptor]:
        """Lookup by kind ('skill', 'workflow', 'tech-stack', 'rule')."""
        return list(self._by_kind.get(kind, []))

    def by_persona(self, persona: str) -> list[ServiceDescriptor]:
        """Lookup by persona name (e.g., 'ARCH', 'QA', 'DEV')."""
        return list(self._by_persona.get(persona, []))

    def by_trigger(self, trigger: str) -> list[ServiceDescriptor]:
        """Lookup by exact trigger keyword (case-insensitive)."""
        return list(self._by_trigger.get(trigger.lower(), []))

    def by_tech_stack(self, tech: str) -> list[ServiceDescriptor]:
        """Lookup by tech-stack name (case-insensitive)."""
        return list(self._by_tech.get(tech.lower(), []))

    def by_lord(self, lord: str) -> list[ServiceDescriptor]:
        """Lookup by lord skill name."""
        return list(self._by_lord.get(lord, []))

    def match_trigger(self, text: str) -> list[ServiceDescriptor]:
        """Find descriptors whose triggers appear in the given text.

        Returns descriptors sorted by number of trigger matches (descending).
        Useful for persona detection: pass the task description, get matching
        skills/workflows ranked by relevance.
        """
        text_lower = text.lower()
        scores: dict[str, int] = {}
        matches: dict[str, ServiceDescriptor] = {}
        for trigger, descs in self._by_trigger.items():
            if trigger in text_lower:
                for desc in descs:
                    scores[desc.name] = scores.get(desc.name, 0) + 1
                    matches[desc.name] = desc
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [matches[name] for name, _ in ranked]

    def match_tech_stack(self, text: str) -> list[ServiceDescriptor]:
        """Find descriptors whose tech_stack appears in the given text."""
        text_lower = text.lower()
        scores: dict[str, int] = {}
        matches: dict[str, ServiceDescriptor] = {}
        for tech, descs in self._by_tech.items():
            if tech in text_lower:
                for desc in descs:
                    scores[desc.name] = scores.get(desc.name, 0) + 1
                    matches[desc.name] = desc
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [matches[name] for name, _ in ranked]

    def all(self) -> list[ServiceDescriptor]:
        """Return all descriptors."""
        return list(self._all)

    def all_status_descriptors(self) -> list[ServiceDescriptor]:
        """Return descriptors included in status (enabled + include_in_status)."""
        return list(self._status_descriptors)

    def enabled_names(self) -> list[str]:
        """Return names of all enabled descriptors."""
        return [d.name for d in self._all if d.enabled]

    def count(self) -> int:
        """Total descriptor count."""
        return len(self._all)

    def count_by_kind(self) -> dict[str, int]:
        """Count descriptors grouped by kind."""
        return {kind: len(descs) for kind, descs in self._by_kind.items()}

    def count_by_persona(self) -> dict[str, int]:
        """Count descriptors grouped by persona."""
        return {persona: len(descs) for persona, descs in self._by_persona.items()}

    def stats(self) -> dict[str, Any]:
        """Return summary statistics for the catalog."""
        return {
            "total": self.count(),
            "enabled": len(self.enabled_names()),
            "by_kind": self.count_by_kind(),
            "by_persona": self.count_by_persona(),
            "personas_indexed": len(self._by_persona),
            "triggers_indexed": len(self._by_trigger),
            "tech_indexed": len(self._by_tech),
        }


def build_catalog_from_directory(
    skills_dir: Path,
    kind: str = "skill",
) -> ServiceCatalog:
    """Build a ServiceCatalog by scanning a directory for skill files.

    Scans for ``{name}.md`` and ``{name}/SKILL.md`` layouts.
    Extracts triggers from frontmatter if present (heuristic: keywords
    in description or filename).

    This is a convenience builder — for full metadata (personas, tech_stack),
    construct ServiceDescriptor instances explicitly.
    """
    skills_path = skills_dir if isinstance(skills_dir, Path) else Path(skills_dir)
    descriptors: list[ServiceDescriptor] = []
    if not skills_path.is_dir():
        return ServiceCatalog(descriptors)

    # Flat layout: {name}.md
    for md_file in skills_path.glob("*.md"):
        name = md_file.stem
        triggers = frozenset({name.lower().replace("-", " ")})
        descriptors.append(ServiceDescriptor(
            name=name,
            kind=kind,
            triggers=triggers,
            file_path=str(md_file),
        ))

    # Directory layout: {name}/SKILL.md
    for skill_dir in skills_path.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                name = skill_dir.name
                triggers = frozenset({name.lower().replace("-", " ")})
                descriptors.append(ServiceDescriptor(
                    name=name,
                    kind=kind,
                    triggers=triggers,
                    file_path=str(skill_file),
                ))

    return ServiceCatalog(descriptors)


# ---------------------------------------------------------------------------
# Entity Catalog with Plugin Extension Points (Backstage-inspired)
#
# Additive layer on top of ServiceCatalog. Provides a versioned entity schema,
# typed relations, a CatalogStore with multi-index lookup, and plugin
# extension points (DashboardWidgetExtension, ScaffolderExtension) wired
# through a PluginRegistry.
# ---------------------------------------------------------------------------

# API version constant for aiZee catalog entities.
CATALOG_API_VERSION = "aizee/v1alpha1"

# Entity kind constants.
KIND_SKILL = "Skill"
KIND_AGENT = "Agent"
KIND_WORKFLOW = "Workflow"
KIND_TECHSTACK = "TechStack"
KIND_PERSONA = "Persona"

# Relation type constants.
REL_DEPENDS_ON = "dependsOn"
REL_PROVIDES_CAPABILITY = "providesCapability"
REL_OWNED_BY = "ownedBy"
REL_PART_OF = "partOf"
REL_HAS_PART = "hasPart"
REL_DERIVED_FROM = "derivedFrom"


@dataclass
class EntityMeta:
    """Metadata for a catalog entity (name, namespace, labels, tags)."""

    name: str
    namespace: str = "default"
    title: str = ""
    description: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class EntityRelation:
    """A typed relation between catalog entities."""

    type: str  # "dependsOn", "providesCapability", "ownedBy", "partOf"
    target_ref: str  # ref string of target entity


@dataclass
class CatalogEntity:
    """Versioned catalog entity (Backstage-inspired).

    ``api_version`` is pinned to ``aizee/v1alpha1``. ``kind`` is one of
    ``Skill``, ``Agent``, ``Workflow``, ``TechStack``, ``Persona``.
    """

    api_version: str
    kind: str
    metadata: EntityMeta
    spec: dict[str, Any] = field(default_factory=dict)
    relations: list[EntityRelation] = field(default_factory=list)

    def ref(self) -> str:
        """Return 'kind:namespace/name' reference string."""
        return f"{self.kind.lower()}:{self.metadata.namespace}/{self.metadata.name}"


class CatalogStore:
    """Multi-index store for CatalogEntity instances.

    Indexes:
    - by ref (kind:namespace/name) -> entity
    - by kind -> list of refs
    - by label ("key=value") -> list of refs
    - by tag -> list of refs
    """

    def __init__(self) -> None:
        self._entities: dict[str, CatalogEntity] = {}
        self._by_kind: dict[str, list[str]] = {}
        self._by_label: dict[str, list[str]] = {}
        self._by_tag: dict[str, list[str]] = {}

    def add(self, entity: CatalogEntity) -> None:
        """Register an entity in all indexes."""
        ref = entity.ref()
        self._entities[ref] = entity
        self._by_kind.setdefault(entity.kind, []).append(ref)
        for key, value in entity.metadata.labels.items():
            label_key = f"{key}={value}"
            self._by_label.setdefault(label_key, []).append(ref)
        for tag in entity.metadata.tags:
            self._by_tag.setdefault(tag, []).append(ref)

    def get(self, ref: str) -> CatalogEntity | None:
        """Lookup by ref string. Returns None if not found."""
        return self._entities.get(ref)

    def list_by_kind(self, kind: str) -> list[CatalogEntity]:
        """List all entities of a given kind."""
        return [self._entities[r] for r in self._by_kind.get(kind, [])]

    def list_by_label(self, key: str, value: str) -> list[CatalogEntity]:
        """List all entities with label key=value."""
        label_key = f"{key}={value}"
        return [self._entities[r] for r in self._by_label.get(label_key, [])]

    def list_by_tag(self, tag: str) -> list[CatalogEntity]:
        """List all entities with the given tag."""
        return [self._entities[r] for r in self._by_tag.get(tag, [])]

    def query(self, filter_fn: Callable[[CatalogEntity], bool]) -> list[CatalogEntity]:
        """Return all entities matching the custom filter function."""
        return [e for e in self._entities.values() if filter_fn(e)]

    def get_relations(
        self, ref: str, relation_type: str | None = None
    ) -> list[EntityRelation]:
        """Get relations of an entity, optionally filtered by type."""
        entity = self._entities.get(ref)
        if entity is None:
            return []
        if relation_type is None:
            return list(entity.relations)
        return [r for r in entity.relations if r.type == relation_type]

    def get_dependencies(self, ref: str) -> list[CatalogEntity]:
        """Get all entities this entity depends on (transitive).

        Follows ``dependsOn`` relations breadth-first, guarding against
        cycles via a visited set.
        """
        result: list[CatalogEntity] = []
        visited: set[str] = set()
        queue: list[str] = [ref]
        while queue:
            current_ref = queue.pop(0)
            if current_ref in visited:
                continue
            visited.add(current_ref)
            for rel in self.get_relations(current_ref, REL_DEPENDS_ON):
                target = self._entities.get(rel.target_ref)
                if target is not None and rel.target_ref not in visited:
                    result.append(target)
                    queue.append(rel.target_ref)
        return result

    def get_dependents(self, ref: str) -> list[CatalogEntity]:
        """Get all entities that depend on this entity (direct only)."""
        result: list[CatalogEntity] = []
        for entity in self._entities.values():
            for rel in entity.relations:
                if rel.type == REL_DEPENDS_ON and rel.target_ref == ref:
                    result.append(entity)
                    break
        return result

    def all(self) -> list[CatalogEntity]:
        """Return all entities in the store."""
        return list(self._entities.values())

    def count(self) -> int:
        """Total entity count."""
        return len(self._entities)


class CatalogExtension(ABC):
    """Base class for catalog extensions (plugin extension point)."""

    @abstractmethod
    def name(self) -> str:
        """Unique name of this extension."""

    @abstractmethod
    def register(self, store: CatalogStore) -> None:
        """Register entities/relations into the store."""


class DashboardWidgetExtension(CatalogExtension):
    """Extension that registers dashboard widgets for entities."""

    @abstractmethod
    def render(self, entity: CatalogEntity) -> dict[str, Any]:
        """Render widget data for the given entity."""


class ScaffolderExtension(CatalogExtension):
    """Extension that registers scaffolder templates."""

    @abstractmethod
    def scaffold(self, params: dict[str, Any]) -> list[str]:
        """Return list of file paths to create from params."""


class PluginRegistry:
    """Registry that wires catalog extensions into a CatalogStore."""

    def __init__(self, store: CatalogStore) -> None:
        self._store = store
        self._extensions: list[CatalogExtension] = []

    def register(self, extension: CatalogExtension) -> None:
        """Register an extension: calls extension.register(store) then tracks it."""
        extension.register(self._store)
        self._extensions.append(extension)

    def extensions(self) -> list[CatalogExtension]:
        """Return all registered extensions."""
        return list(self._extensions)

    def get_dashboard_widgets(self, entity: CatalogEntity) -> list[dict[str, Any]]:
        """Get all dashboard widgets for an entity from widget extensions."""
        widgets: list[dict[str, Any]] = []
        for ext in self._extensions:
            if isinstance(ext, DashboardWidgetExtension):
                widgets.append(ext.render(entity))
        return widgets

    def get_scaffolder_templates(self) -> list[ScaffolderExtension]:
        """Return all registered scaffolder extensions."""
        return [ext for ext in self._extensions if isinstance(ext, ScaffolderExtension)]
