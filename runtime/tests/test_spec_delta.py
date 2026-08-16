"""Tests for spec_engine enhancements — Delta Specs + Hash-Tracked Manifests."""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.spec_engine import (
    DeltaType,
    Requirement,
    Spec,
    SpecDelta,
    SpecEngine,
    SpecManifest,
)


@pytest.fixture
def engine(tmp_path: Path) -> SpecEngine:
    """Create a spec engine in a temp directory."""
    return SpecEngine(tmp_path / "specs")


class TestSpecDelta:
    """Tests for delta-based spec management (from OpenSpec)."""

    def test_delta_type_values(self) -> None:
        assert DeltaType.ADDED.value == "added"
        assert DeltaType.MODIFIED.value == "modified"
        assert DeltaType.REMOVED.value == "removed"

    def test_add_delta(self, engine: SpecEngine) -> None:
        engine.init_spec("test", "Test Spec")
        delta = engine.add_delta("test", "REQ-001", DeltaType.ADDED, "New requirement")
        assert delta.requirement_id == "REQ-001"
        assert delta.delta_type == DeltaType.ADDED
        spec = engine.load_spec("test")
        assert len(spec.deltas) == 1

    def test_apply_added_delta(self, engine: SpecEngine) -> None:
        engine.init_spec("test", "Test Spec")
        engine.add_delta("test", "REQ-001", DeltaType.ADDED, "New feature")
        engine.add_delta("test", "REQ-002", DeltaType.ADDED, "Another feature")
        applied = engine.apply_deltas("test")
        assert applied == 2
        spec = engine.load_spec("test")
        assert len(spec.requirements) == 2
        assert spec.requirements[0].id == "REQ-001"
        assert len(spec.deltas) == 0

    def test_apply_modified_delta(self, engine: SpecEngine) -> None:
        engine.init_spec("test", "Test Spec")
        engine.add_requirement("test", "Original desc")
        spec = engine.load_spec("test")
        req_id = spec.requirements[0].id
        engine.add_delta("test", req_id, DeltaType.MODIFIED, "Updated desc")
        engine.apply_deltas("test")
        spec = engine.load_spec("test")
        assert spec.requirements[0].description == "Updated desc"

    def test_apply_removed_delta(self, engine: SpecEngine) -> None:
        engine.init_spec("test", "Test Spec")
        engine.add_requirement("test", "To be removed")
        spec = engine.load_spec("test")
        req_id = spec.requirements[0].id
        engine.add_delta("test", req_id, DeltaType.REMOVED)
        engine.apply_deltas("test")
        spec = engine.load_spec("test")
        assert len(spec.requirements) == 0

    def test_delta_persistence(self, engine: SpecEngine) -> None:
        engine.init_spec("test", "Test Spec")
        engine.add_delta("test", "REQ-001", DeltaType.ADDED, "Persisted req")
        spec = engine.load_spec("test")
        assert len(spec.deltas) == 1
        assert spec.deltas[0].description == "Persisted req"

    def test_delta_in_to_dict(self, engine: SpecEngine) -> None:
        engine.init_spec("test", "Test Spec")
        engine.add_delta("test", "REQ-001", DeltaType.ADDED, "Test")
        spec = engine.load_spec("test")
        d = spec.to_dict()
        assert "deltas" in d
        assert len(d["deltas"]) == 1


class TestSpecManifest:
    """Tests for hash-tracked file manifests (from spec-kit)."""

    def test_record_and_check_unmodified(self) -> None:
        manifest = SpecManifest()
        manifest.record_file("spec.json", '{"id": "test"}')
        assert manifest.is_modified("spec.json", '{"id": "test"}') is False

    def test_detect_modification(self) -> None:
        manifest = SpecManifest()
        manifest.record_file("spec.json", '{"id": "test"}')
        assert manifest.is_modified("spec.json", '{"id": "modified"}') is True

    def test_new_file_is_modified(self) -> None:
        manifest = SpecManifest()
        assert manifest.is_modified("new.json", "content") is True

    def test_to_dict_and_from_dict(self) -> None:
        manifest = SpecManifest()
        manifest.record_file("a.json", "content-a")
        d = manifest.to_dict()
        restored = SpecManifest.from_dict(d)
        assert restored.is_modified("a.json", "content-a") is False

    def test_get_manifest_from_engine(self, engine: SpecEngine) -> None:
        engine.init_spec("test", "Test Spec")
        manifest = engine.get_manifest("test")
        assert manifest.size() if hasattr(manifest, "size") else len(manifest.files) > 0

    def test_is_file_modified_false_on_fresh(self, engine: SpecEngine) -> None:
        engine.init_spec("test", "Test Spec")
        # Fresh file should not be modified (just written)
        assert engine.is_file_modified("test", "json") is False
