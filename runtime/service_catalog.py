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

from dataclasses import dataclass, field
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
    skills_dir: Any,
    kind: str = "skill",
) -> ServiceCatalog:
    """Build a ServiceCatalog by scanning a directory for skill files.

    Scans for ``{name}.md`` and ``{name}/SKILL.md`` layouts.
    Extracts triggers from frontmatter if present (heuristic: keywords
    in description or filename).

    This is a convenience builder — for full metadata (personas, tech_stack),
    construct ServiceDescriptor instances explicitly.
    """
    from pathlib import Path

    skills_path = Path(skills_dir) if not isinstance(skills_dir, Path) else skills_dir
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
