"""Tests for runtime/service_catalog.py — multi-index catalog.

Covers: ServiceDescriptor, ServiceCatalog, build_catalog_from_directory.
FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.service_catalog import (
    ServiceCatalog,
    ServiceDescriptor,
    build_catalog_from_directory,
)

# -- ServiceDescriptor -----------------------------------------------------


class TestServiceDescriptor:
    def test_create_minimal(self) -> None:
        desc = ServiceDescriptor(name="test", kind="skill")
        assert desc.name == "test"
        assert desc.kind == "skill"
        assert desc.enabled is True
        assert desc.personas == frozenset()

    def test_supports_persona(self) -> None:
        desc = ServiceDescriptor(
            name="arch", kind="skill", personas=frozenset({"ARCH", "DEV"}),
        )
        assert desc.supports_persona("ARCH") is True
        assert desc.supports_persona("QA") is False

    def test_supports_tech(self) -> None:
        desc = ServiceDescriptor(
            name="flutter", kind="skill", tech_stack=frozenset({"flutter", "dart"}),
        )
        assert desc.supports_tech("flutter") is True
        assert desc.supports_tech("react") is False

    def test_frozen(self) -> None:
        """ServiceDescriptor is frozen — cannot mutate."""
        desc = ServiceDescriptor(name="test", kind="skill")
        with pytest.raises(AttributeError):
            desc.name = "other"  # type: ignore[misc]


# -- ServiceCatalog --------------------------------------------------------


@pytest.fixture
def sample_catalog() -> ServiceCatalog:
    return ServiceCatalog([
        ServiceDescriptor(
            name="flutter-architect",
            kind="skill",
            personas=frozenset({"MOBILE", "UX"}),
            triggers=frozenset({"flutter", "dart", "widget"}),
            tech_stack=frozenset({"flutter"}),
            lords=frozenset({"clean-code-guard"}),
        ),
        ServiceDescriptor(
            name="backend-api-expert",
            kind="skill",
            personas=frozenset({"DEV", "ARCH"}),
            triggers=frozenset({"api", "rest", "graphql", "endpoint"}),
            tech_stack=frozenset({"fastapi", "django"}),
            lords=frozenset({"docs-guard"}),
        ),
        ServiceDescriptor(
            name="spec-analyze",
            kind="workflow",
            personas=frozenset({"ARCH"}),
            triggers=frozenset({"analyze", "spec", "consistency"}),
            tech_stack=frozenset(),
            lords=frozenset(),
        ),
        ServiceDescriptor(
            name="disabled-skill",
            kind="skill",
            enabled=False,
            personas=frozenset({"QA"}),
            triggers=frozenset({"test"}),
        ),
    ])


class TestServiceCatalog:
    def test_count(self, sample_catalog: ServiceCatalog) -> None:
        assert sample_catalog.count() == 4

    def test_by_name_found(self, sample_catalog: ServiceCatalog) -> None:
        desc = sample_catalog.by_name("flutter-architect")
        assert desc is not None
        assert desc.name == "flutter-architect"

    def test_by_name_missing(self, sample_catalog: ServiceCatalog) -> None:
        assert sample_catalog.by_name("nonexistent") is None

    def test_by_kind(self, sample_catalog: ServiceCatalog) -> None:
        skills = sample_catalog.by_kind("skill")
        assert len(skills) == 3  # flutter, backend, disabled
        workflows = sample_catalog.by_kind("workflow")
        assert len(workflows) == 1

    def test_by_persona(self, sample_catalog: ServiceCatalog) -> None:
        arch_descs = sample_catalog.by_persona("ARCH")
        assert len(arch_descs) == 2  # backend-api-expert, spec-analyze
        names = {d.name for d in arch_descs}
        assert "backend-api-expert" in names
        assert "spec-analyze" in names

    def test_by_persona_missing(self, sample_catalog: ServiceCatalog) -> None:
        assert sample_catalog.by_persona("GAME") == []

    def test_by_trigger_case_insensitive(self, sample_catalog: ServiceCatalog) -> None:
        descs = sample_catalog.by_trigger("FLUTTER")
        assert len(descs) == 1
        assert descs[0].name == "flutter-architect"

    def test_by_tech_stack(self, sample_catalog: ServiceCatalog) -> None:
        desc = sample_catalog.by_tech_stack("fastapi")
        assert len(desc) == 1
        assert desc[0].name == "backend-api-expert"

    def test_by_lord(self, sample_catalog: ServiceCatalog) -> None:
        desc = sample_catalog.by_lord("docs-guard")
        assert len(desc) == 1
        assert desc[0].name == "backend-api-expert"

    def test_match_trigger(self, sample_catalog: ServiceCatalog) -> None:
        """match_trigger finds descriptors ranked by trigger match count."""
        matches = sample_catalog.match_trigger("build a flutter app with dart")
        assert len(matches) > 0
        # flutter-architect should be first (2 trigger matches: flutter, dart)
        assert matches[0].name == "flutter-architect"

    def test_match_trigger_no_matches(self, sample_catalog: ServiceCatalog) -> None:
        matches = sample_catalog.match_trigger("completely unrelated text about cooking")
        assert matches == []

    def test_match_tech_stack(self, sample_catalog: ServiceCatalog) -> None:
        matches = sample_catalog.match_tech_stack("using fastapi and django for backend")
        assert len(matches) > 0
        assert matches[0].name == "backend-api-expert"

    def test_all(self, sample_catalog: ServiceCatalog) -> None:
        all_descs = sample_catalog.all()
        assert len(all_descs) == 4

    def test_all_status_descriptors_excludes_disabled(self, sample_catalog: ServiceCatalog) -> None:
        """Status descriptors exclude disabled entries."""
        status = sample_catalog.all_status_descriptors()
        names = {d.name for d in status}
        assert "disabled-skill" not in names
        assert len(status) == 3

    def test_enabled_names(self, sample_catalog: ServiceCatalog) -> None:
        names = set(sample_catalog.enabled_names())
        assert "disabled-skill" not in names
        assert len(names) == 3

    def test_count_by_kind(self, sample_catalog: ServiceCatalog) -> None:
        counts = sample_catalog.count_by_kind()
        assert counts["skill"] == 3
        assert counts["workflow"] == 1

    def test_count_by_persona(self, sample_catalog: ServiceCatalog) -> None:
        counts = sample_catalog.count_by_persona()
        assert counts["ARCH"] == 2
        assert counts["MOBILE"] == 1

    def test_stats(self, sample_catalog: ServiceCatalog) -> None:
        stats = sample_catalog.stats()
        assert stats["total"] == 4
        assert stats["enabled"] == 3
        assert "by_kind" in stats
        assert "by_persona" in stats
        assert stats["personas_indexed"] > 0
        assert stats["triggers_indexed"] > 0


# -- build_catalog_from_directory ------------------------------------------


class TestBuildCatalogFromDirectory:
    def test_empty_dir(self, tmp_path: Path) -> None:
        catalog = build_catalog_from_directory(tmp_path)
        assert catalog.count() == 0

    def test_flat_layout(self, tmp_path: Path) -> None:
        (tmp_path / "skill1.md").write_text("# Skill 1", encoding="utf-8")
        (tmp_path / "skill2.md").write_text("# Skill 2", encoding="utf-8")
        catalog = build_catalog_from_directory(tmp_path)
        assert catalog.count() == 2
        assert catalog.by_name("skill1") is not None
        assert catalog.by_name("skill2") is not None

    def test_directory_layout(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# My Skill", encoding="utf-8")
        catalog = build_catalog_from_directory(tmp_path)
        assert catalog.count() == 1
        assert catalog.by_name("my-skill") is not None

    def test_mixed_layout(self, tmp_path: Path) -> None:
        (tmp_path / "flat.md").write_text("# Flat", encoding="utf-8")
        nested = tmp_path / "nested"
        nested.mkdir()
        (nested / "SKILL.md").write_text("# Nested", encoding="utf-8")
        catalog = build_catalog_from_directory(tmp_path)
        assert catalog.count() == 2

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        catalog = build_catalog_from_directory(tmp_path / "nonexistent")
        assert catalog.count() == 0

    def test_triggers_extracted_from_name(self, tmp_path: Path) -> None:
        (tmp_path / "flutter-architect.md").write_text("# Flutter", encoding="utf-8")
        catalog = build_catalog_from_directory(tmp_path)
        # Trigger should be derived from name (hyphens → spaces)
        descs = catalog.by_trigger("flutter architect")
        assert len(descs) == 1
