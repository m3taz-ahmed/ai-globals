"""Gap coverage: runtime/service_catalog.py — full module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.service_catalog import (
    REL_DEPENDS_ON,
    CatalogEntity,
    CatalogStore,
    DashboardWidgetExtension,
    EntityMeta,
    EntityRelation,
    PluginRegistry,
    ScaffolderExtension,
    ServiceCatalog,
    ServiceDescriptor,
    build_catalog_from_directory,
)


def _desc(**kw: object) -> ServiceDescriptor:
    return ServiceDescriptor(name=str(kw.pop("name", "n")), kind=str(kw.pop("kind", "skill")), **kw)  # type: ignore[arg-type]


class TestServiceDescriptor:
    def test_supports(self) -> None:
        d = _desc(name="x", personas=frozenset({"DEV"}), tech_stack=frozenset({"python"}))
        assert d.supports_persona("DEV") and not d.supports_persona("QA")
        assert d.supports_tech("python") and not d.supports_tech("php")


class TestServiceCatalog:
    def _catalog(self) -> ServiceCatalog:
        descs = [
            _desc(name="a", kind="skill", personas=frozenset({"DEV"}),
                  triggers=frozenset({"Build API"}), tech_stack=frozenset({"Python"}),
                  lords=frozenset({"lord1"})),
            _desc(name="b", kind="workflow", personas=frozenset({"QA"}),
                  triggers=frozenset({"test it"}), tech_stack=frozenset({"pytest"})),
            _desc(name="c", kind="skill", enabled=False, include_in_status=False),
            _desc(name="a2", kind="skill", personas=frozenset({"DEV"})),
        ]
        return ServiceCatalog(descs)

    def test_indexes(self) -> None:
        c = self._catalog()
        assert c.by_name("a") is not None and c.by_name("nope") is None
        assert len(c.by_kind("skill")) == 3
        assert len(c.by_persona("DEV")) == 2
        assert c.by_trigger("BUILD API")[0].name == "a"
        assert c.by_tech_stack("PYTHON")[0].name == "a"
        assert c.by_lord("lord1")[0].name == "a"
        assert c.by_lord("none") == []

    def test_match_trigger_ranking(self) -> None:
        c = self._catalog()
        out = c.match_trigger("please build api and test it now")
        assert [d.name for d in out][:2] == ["a", "b"] or {d.name for d in out} == {"a", "b"}
        assert c.match_trigger("nothing matches") == []

    def test_match_tech_stack(self) -> None:
        c = self._catalog()
        out = c.match_tech_stack("we use python and pytest")
        assert {d.name for d in out} == {"a", "b"}

    def test_all_and_status(self) -> None:
        c = self._catalog()
        assert len(c.all()) == 4
        assert {d.name for d in c.all_status_descriptors()} == {"a", "b", "a2"}
        assert set(c.enabled_names()) == {"a", "b", "a2"}
        assert c.count() == 4

    def test_counts_and_stats(self) -> None:
        c = self._catalog()
        assert c.count_by_kind() == {"skill": 3, "workflow": 1}
        assert c.count_by_persona() == {"DEV": 2, "QA": 1}
        s = c.stats()
        assert s["total"] == 4 and s["enabled"] == 3
        assert s["by_kind"]["workflow"] == 1


class TestBuildFromDirectory:
    def test_missing_dir(self, tmp_path: Path) -> None:
        c = build_catalog_from_directory(tmp_path / "nope")
        assert c.count() == 0

    def test_flat_and_dir_layouts(self, tmp_path: Path) -> None:
        (tmp_path / "flat-skill.md").write_text("# flat")
        d = tmp_path / "dir-skill"
        d.mkdir()
        (d / "SKILL.md").write_text("# dir")
        (tmp_path / "empty-dir").mkdir()  # no SKILL.md -> skipped
        c = build_catalog_from_directory(tmp_path)
        names = {x.name for x in c.all()}
        assert names == {"flat-skill", "dir-skill"}
        assert c.by_trigger("flat skill")[0].name == "flat-skill"


def _entity(name: str, kind: str = "Skill", **kw: Any) -> CatalogEntity:
    meta = EntityMeta(name=name, labels=dict(kw.pop("labels", {}) or {}), tags=list(kw.pop("tags", []) or []))
    rels = [EntityRelation(type=r[0], target_ref=r[1]) for r in kw.pop("relations", []) or []]
    return CatalogEntity(api_version="aizee/v1alpha1", kind=kind, metadata=meta, relations=rels)


class TestCatalogStore:
    def _store(self) -> CatalogStore:
        s = CatalogStore()
        s.add(_entity("lib", labels={"tier": "base"}, tags=["core"]))
        s.add(_entity("app", labels={"tier": "top"}, relations=[(REL_DEPENDS_ON, "skill:default/lib")]))
        s.add(_entity("cycle1", relations=[(REL_DEPENDS_ON, "skill:default/cycle2")]))
        s.add(_entity("cycle2", relations=[(REL_DEPENDS_ON, "skill:default/cycle1")]))
        return s

    def test_ref_and_get(self) -> None:
        s = self._store()
        e = s.get("skill:default/lib")
        assert e is not None and e.ref() == "skill:default/lib"
        assert s.get("nope") is None

    def test_indexes(self) -> None:
        s = self._store()
        assert len(s.list_by_kind("Skill")) == 4
        assert s.list_by_label("tier", "base")[0].metadata.name == "lib"
        assert s.list_by_tag("core")[0].metadata.name == "lib"
        assert s.list_by_tag("none") == []
        assert s.count() == 4 and len(s.all()) == 4

    def test_query(self) -> None:
        s = self._store()
        out = s.query(lambda e: e.metadata.name.startswith("c"))
        assert {e.metadata.name for e in out} == {"cycle1", "cycle2"}

    def test_relations_filtered(self) -> None:
        s = self._store()
        assert s.get_relations("skill:default/app") != []
        assert s.get_relations("skill:default/app", REL_DEPENDS_ON)[0].target_ref == "skill:default/lib"
        assert s.get_relations("skill:default/app", "otherType") == []
        assert s.get_relations("missing") == []

    def test_dependencies_transitive_and_cycle(self) -> None:
        s = self._store()
        deps = s.get_dependencies("skill:default/app")
        assert [d.metadata.name for d in deps] == ["lib"]
        # cycle: cycle1 -> cycle2 -> cycle1 terminates via visited set
        cyc = s.get_dependencies("skill:default/cycle1")
        assert {d.metadata.name for d in cyc} == {"cycle2"}

    def test_dependents(self) -> None:
        s = self._store()
        deps = s.get_dependents("skill:default/lib")
        assert [d.metadata.name for d in deps] == ["app"]
        assert s.get_dependents("skill:default/none") == []


class _Widget(DashboardWidgetExtension):
    def name(self) -> str:
        return "w"

    def register(self, store: CatalogStore) -> None:
        store.add(_entity("widget-entity"))

    def render(self, entity: CatalogEntity) -> dict[str, object]:
        return {"for": entity.metadata.name}


class _Scaffolder(ScaffolderExtension):
    def name(self) -> str:
        return "s"

    def register(self, store: CatalogStore) -> None:
        pass

    def scaffold(self, params: dict[str, object]) -> list[str]:
        return ["file.py"]


class TestPluginRegistry:
    def test_register_and_query(self) -> None:
        store = CatalogStore()
        reg = PluginRegistry(store)
        reg.register(_Widget())
        reg.register(_Scaffolder())
        assert len(reg.extensions()) == 2
        assert store.get("skill:default/widget-entity") is not None
        widgets = reg.get_dashboard_widgets(_entity("e"))
        assert widgets == [{"for": "e"}]
        scaffs = reg.get_scaffolder_templates()
        assert len(scaffs) == 1 and scaffs[0].scaffold({}) == ["file.py"]
