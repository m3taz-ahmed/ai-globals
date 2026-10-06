"""Tests for the Entity Catalog with Plugin Extension Points.

Covers CatalogEntity, EntityMeta, EntityRelation, CatalogStore multi-index
lookup, transitive dependency resolution, PluginRegistry extension wiring,
and catalog-based discovery helpers in agent_discovery.
"""

from __future__ import annotations

from pathlib import Path

from runtime.agent_discovery import (
    discover_by_capability,
    discover_by_labels,
    skill_to_entity,
)
from runtime.service_catalog import (
    CATALOG_API_VERSION,
    KIND_AGENT,
    KIND_SKILL,
    KIND_TECHSTACK,
    REL_DEPENDS_ON,
    REL_OWNED_BY,
    REL_PART_OF,
    REL_PROVIDES_CAPABILITY,
    CatalogEntity,
    CatalogStore,
    DashboardWidgetExtension,
    EntityMeta,
    EntityRelation,
    PluginRegistry,
    ScaffolderExtension,
)


def _make_entity(
    name: str,
    kind: str = KIND_SKILL,
    namespace: str = "default",
    labels: dict[str, str] | None = None,
    tags: list[str] | None = None,
    relations: list[EntityRelation] | None = None,
    spec: dict[str, object] | None = None,
) -> CatalogEntity:
    return CatalogEntity(
        api_version=CATALOG_API_VERSION,
        kind=kind,
        metadata=EntityMeta(
            name=name,
            namespace=namespace,
            labels=labels or {},
            tags=tags or [],
        ),
        relations=relations or [],
        spec=spec or {},
    )


class TestCatalogEntity:
    def test_ref_format(self):
        e = _make_entity("flutter-arch", kind=KIND_SKILL)
        assert e.ref() == "skill:default/flutter-arch"

    def test_ref_with_namespace(self):
        e = _make_entity("dev-agent", kind=KIND_AGENT, namespace="team-a")
        assert e.ref() == "agent:team-a/dev-agent"

    def test_api_version_pinned(self):
        e = _make_entity("x")
        assert e.api_version == "aizee/v1alpha1"


class TestEntityMeta:
    def test_defaults(self):
        m = EntityMeta(name="x")
        assert m.namespace == "default"
        assert m.labels == {}
        assert m.annotations == {}
        assert m.tags == []

    def test_with_labels_annotations_tags(self):
        m = EntityMeta(
            name="x",
            labels={"tier": "backend"},
            annotations={"owner": "team-a"},
            tags=["flutter", "dart"],
        )
        assert m.labels["tier"] == "backend"
        assert m.annotations["owner"] == "team-a"
        assert m.tags == ["flutter", "dart"]


class TestEntityRelation:
    def test_construction(self):
        r = EntityRelation(type=REL_DEPENDS_ON, target_ref="skill:default/x")
        assert r.type == "dependsOn"
        assert r.target_ref == "skill:default/x"


class TestCatalogStoreAddGet:
    def test_add_and_get(self):
        store = CatalogStore()
        e = _make_entity("flutter-arch")
        store.add(e)
        assert store.get(e.ref()) is e

    def test_get_missing_returns_none(self):
        store = CatalogStore()
        assert store.get("skill:default/missing") is None


class TestCatalogStoreListByKind:
    def test_list_by_kind(self):
        store = CatalogStore()
        s1 = _make_entity("s1", kind=KIND_SKILL)
        s2 = _make_entity("s2", kind=KIND_SKILL)
        a1 = _make_entity("a1", kind=KIND_AGENT)
        store.add(s1)
        store.add(s2)
        store.add(a1)
        skills = store.list_by_kind(KIND_SKILL)
        assert {e.metadata.name for e in skills} == {"s1", "s2"}
        assert store.list_by_kind(KIND_TECHSTACK) == []


class TestCatalogStoreListByLabel:
    def test_list_by_label(self):
        store = CatalogStore()
        e1 = _make_entity("e1", labels={"tier": "backend"})
        e2 = _make_entity("e2", labels={"tier": "frontend"})
        store.add(e1)
        store.add(e2)
        result = store.list_by_label("tier", "backend")
        assert result == [e1]


class TestCatalogStoreListByTag:
    def test_list_by_tag(self):
        store = CatalogStore()
        e1 = _make_entity("e1", tags=["flutter", "dart"])
        e2 = _make_entity("e2", tags=["flutter"])
        store.add(e1)
        store.add(e2)
        flutter = store.list_by_tag("flutter")
        assert {e.metadata.name for e in flutter} == {"e1", "e2"}
        dart = store.list_by_tag("dart")
        assert dart == [e1]


class TestCatalogStoreQuery:
    def test_query_custom_filter(self):
        store = CatalogStore()
        e1 = _make_entity("e1", kind=KIND_SKILL)
        e2 = _make_entity("e2", kind=KIND_AGENT)
        store.add(e1)
        store.add(e2)
        result = store.query(lambda e: e.kind == KIND_AGENT)
        assert result == [e2]


class TestCatalogStoreRelations:
    def test_get_relations_by_type(self):
        store = CatalogStore()
        target = _make_entity("dep")
        store.add(target)
        e = _make_entity(
            "main",
            relations=[
                EntityRelation(type=REL_DEPENDS_ON, target_ref=target.ref()),
                EntityRelation(type=REL_OWNED_BY, target_ref="persona:default/dev"),
            ],
        )
        store.add(e)
        deps = store.get_relations(e.ref(), REL_DEPENDS_ON)
        assert len(deps) == 1
        assert deps[0].target_ref == target.ref()
        all_rels = store.get_relations(e.ref())
        assert len(all_rels) == 2

    def test_get_relations_missing_entity(self):
        store = CatalogStore()
        assert store.get_relations("skill:default/missing") == []


class TestCatalogStoreDependencies:
    def test_get_dependencies_direct(self):
        store = CatalogStore()
        dep = _make_entity("dep")
        store.add(dep)
        main = _make_entity(
            "main",
            relations=[EntityRelation(type=REL_DEPENDS_ON, target_ref=dep.ref())],
        )
        store.add(main)
        deps = store.get_dependencies(main.ref())
        assert deps == [dep]

    def test_get_dependencies_transitive(self):
        store = CatalogStore()
        c = _make_entity("c")
        b = _make_entity(
            "b",
            relations=[EntityRelation(type=REL_DEPENDS_ON, target_ref=c.ref())],
        )
        a = _make_entity(
            "a",
            relations=[EntityRelation(type=REL_DEPENDS_ON, target_ref=b.ref())],
        )
        store.add(c)
        store.add(b)
        store.add(a)
        deps = store.get_dependencies(a.ref())
        # Transitive: a -> b -> c
        assert {e.metadata.name for e in deps} == {"b", "c"}

    def test_get_dependencies_cycle_safe(self):
        store = CatalogStore()
        x = _make_entity(
            "x",
            relations=[EntityRelation(type=REL_DEPENDS_ON, target_ref="skill:default/y")],
        )
        y = _make_entity(
            "y",
            relations=[EntityRelation(type=REL_DEPENDS_ON, target_ref="skill:default/x")],
        )
        store.add(x)
        store.add(y)
        # Should not infinite-loop.
        deps = store.get_dependencies(x.ref())
        assert {e.metadata.name for e in deps} == {"y"}


class TestCatalogStoreDependents:
    def test_get_dependents(self):
        store = CatalogStore()
        dep = _make_entity("dep")
        main = _make_entity(
            "main",
            relations=[EntityRelation(type=REL_DEPENDS_ON, target_ref=dep.ref())],
        )
        store.add(dep)
        store.add(main)
        dependents = store.get_dependents(dep.ref())
        assert dependents == [main]


class _DummyWidgetExtension(DashboardWidgetExtension):
    def name(self) -> str:
        return "dummy-widget"

    def register(self, store: CatalogStore) -> None:
        store.add(_make_entity("widget-registered", kind=KIND_SKILL))

    def render(self, entity: CatalogEntity) -> dict[str, object]:
        return {"widget": "dummy", "entity": entity.metadata.name}


class _DummyScaffolderExtension(ScaffolderExtension):
    def name(self) -> str:
        return "dummy-scaffolder"

    def register(self, store: CatalogStore) -> None:
        store.add(_make_entity("scaffold-registered", kind=KIND_TECHSTACK))

    def scaffold(self, params: dict[str, object]) -> list[str]:
        return [f"scaffolded/{params.get('name', 'x')}.py"]


class TestPluginRegistry:
    def test_register_calls_extension_register(self):
        store = CatalogStore()
        registry = PluginRegistry(store)
        ext = _DummyWidgetExtension()
        registry.register(ext)
        # register() added an entity to the store.
        assert store.get("skill:default/widget-registered") is not None
        assert ext in registry.extensions()

    def test_get_dashboard_widgets(self):
        store = CatalogStore()
        registry = PluginRegistry(store)
        registry.register(_DummyWidgetExtension())
        entity = _make_entity("target")
        widgets = registry.get_dashboard_widgets(entity)
        assert len(widgets) == 1
        assert widgets[0]["widget"] == "dummy"
        assert widgets[0]["entity"] == "target"

    def test_get_scaffolder_templates(self):
        store = CatalogStore()
        registry = PluginRegistry(store)
        registry.register(_DummyScaffolderExtension())
        templates = registry.get_scaffolder_templates()
        assert len(templates) == 1
        assert templates[0].scaffold({"name": "foo"}) == ["scaffolded/foo.py"]


class TestDiscoverByLabels:
    def test_finds_matching_entities(self):
        store = CatalogStore()
        e1 = _make_entity("e1", labels={"tier": "backend", "lang": "py"})
        e2 = _make_entity("e2", labels={"tier": "frontend"})
        store.add(e1)
        store.add(e2)
        result = discover_by_labels(store, {"tier": "backend"})
        assert result == [e1]

    def test_and_semantics_multiple_labels(self):
        store = CatalogStore()
        e1 = _make_entity("e1", labels={"tier": "backend", "lang": "py"})
        e2 = _make_entity("e2", labels={"tier": "backend", "lang": "go"})
        store.add(e1)
        store.add(e2)
        result = discover_by_labels(store, {"tier": "backend", "lang": "py"})
        assert result == [e1]

    def test_empty_labels_returns_empty(self):
        store = CatalogStore()
        store.add(_make_entity("e1"))
        assert discover_by_labels(store, {}) == []


class TestDiscoverByCapability:
    def test_finds_capability_providers_via_relation(self):
        store = CatalogStore()
        e = _make_entity(
            "provider",
            relations=[
                EntityRelation(type=REL_PROVIDES_CAPABILITY, target_ref="code-review"),
            ],
        )
        store.add(e)
        result = discover_by_capability(store, "code-review")
        assert result == [e]

    def test_finds_capability_providers_via_spec(self):
        store = CatalogStore()
        e = _make_entity("provider", spec={"capabilities": ["code-review", "test"]})
        store.add(e)
        result = discover_by_capability(store, "code-review")
        assert result == [e]

    def test_no_match(self):
        store = CatalogStore()
        store.add(_make_entity("e1"))
        assert discover_by_capability(store, "missing") == []


class TestSkillToEntity:
    def test_converts_skill_file_to_entity(self, tmp_path: Path):
        skill_file = tmp_path / "my-skill.md"
        skill_file.write_text(
            "# My Skill\n\nBuilds Flutter apps with clean architecture.\n",
            encoding="utf-8",
        )
        entity = skill_to_entity(skill_file, "my-skill")
        assert entity.kind == KIND_SKILL
        assert entity.api_version == CATALOG_API_VERSION
        assert entity.ref() == "skill:default/my-skill"
        assert entity.metadata.title == "My Skill"
        assert "Flutter" in entity.metadata.description
        # partOf relation to catalog root.
        part_of = [r for r in entity.relations if r.type == REL_PART_OF]
        assert len(part_of) == 1
        assert part_of[0].target_ref == "workflow:default/aizee"
        assert entity.spec["file_path"] == str(skill_file)

    def test_skill_to_entity_with_frontmatter(self, tmp_path: Path):
        skill_file = tmp_path / "dev-skill.md"
        skill_file.write_text(
            "---\n"
            "name: dev-skill\n"
            "description: A dev skill.\n"
            "persona: DEV\n"
            "depends_on: skill:default/base, skill:default/core\n"
            "capabilities: code-review, testing\n"
            "tags: dev, backend\n"
            "triggers: flutter, dart\n"
            "---\n"
            "# Dev Skill\n\nBuilds things.\n",
            encoding="utf-8",
        )
        entity = skill_to_entity(skill_file, "dev-skill")
        # ownedBy relation from persona.
        owned = [r for r in entity.relations if r.type == REL_OWNED_BY]
        assert len(owned) == 1
        assert owned[0].target_ref == "persona:default/DEV"
        # dependsOn relations.
        deps = [r for r in entity.relations if r.type == REL_DEPENDS_ON]
        assert {r.target_ref for r in deps} == {
            "skill:default/base",
            "skill:default/core",
        }
        # providesCapability relations.
        caps = [r for r in entity.relations if r.type == REL_PROVIDES_CAPABILITY]
        assert {r.target_ref for r in caps} == {"code-review", "testing"}
        # tags from frontmatter.
        assert entity.metadata.tags == ["dev", "backend"]
        # triggers in spec.
        assert entity.spec["triggers"] == ["flutter", "dart"]

    def test_skill_to_entity_missing_file(self, tmp_path: Path):
        entity = skill_to_entity(tmp_path / "missing.md", "missing")
        assert entity.kind == KIND_SKILL
        assert entity.metadata.description == ""
        # partOf still present.
        part_of = [r for r in entity.relations if r.type == REL_PART_OF]
        assert len(part_of) == 1
