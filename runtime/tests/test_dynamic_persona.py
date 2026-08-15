"""Tests for runtime/dynamic_persona.py — dynamic evolving personas."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from runtime.dynamic_persona import (
    ACCUMULATION_THRESHOLD,
    CONTEXT_HISTORY_LIMIT,
    DEEP_THRESHOLD,
    EXPERTISE_INCREMENT,
    EXPERTISE_MAX,
    DynamicPersonaManager,
    PersonaExperience,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def manager(tmp_path: Path) -> DynamicPersonaManager:
    """Return a fresh manager rooted in a temporary directory."""
    return DynamicPersonaManager(tmp_path)


def _record_n(
    mgr: DynamicPersonaManager,
    persona_id: str,
    n: int,
    success: bool = True,
    area: str | None = None,
) -> None:
    """Record ``n`` interactions for a persona."""
    for _ in range(n):
        ctx = {"area": area} if area else None
        mgr.record_interaction(persona_id, success=success, context=ctx)


# ---------------------------------------------------------------------------
# PersonaExperience dataclass
# ---------------------------------------------------------------------------


class TestPersonaExperienceDataclass:
    def test_defaults(self):
        exp = PersonaExperience(persona_id="ARCH")
        assert exp.persona_id == "ARCH"
        assert exp.interactions == 0
        assert exp.successes == 0
        assert exp.expertise_areas == {}
        assert exp.learned_patterns == {}
        assert exp.context_history == []
        assert exp.success_rate == 0.0
        assert exp.evolution_level == "core"

    def test_success_rate_with_interactions(self):
        exp = PersonaExperience(persona_id="DEV", interactions=10, successes=7)
        assert exp.success_rate == pytest.approx(0.7)

    def test_evolution_level_accumulation(self):
        exp = PersonaExperience(persona_id="QA", interactions=ACCUMULATION_THRESHOLD)
        assert exp.evolution_level == "accumulation"

    def test_evolution_level_deep(self):
        exp = PersonaExperience(persona_id="SEC", interactions=DEEP_THRESHOLD)
        assert exp.evolution_level == "deep"

    def test_to_dict_roundtrip_fields(self):
        exp = PersonaExperience(
            persona_id="GAME",
            interactions=5,
            successes=3,
            expertise_areas={"rendering": 25.0},
            learned_patterns={"cache-shaders": 2},
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-02T00:00:00+00:00",
        )
        d = exp.to_dict()
        assert d["persona_id"] == "GAME"
        assert d["interactions"] == 5
        assert d["successes"] == 3
        assert d["expertise_areas"]["rendering"] == 25.0
        assert d["learned_patterns"]["cache-shaders"] == 2


# ---------------------------------------------------------------------------
# record_interaction
# ---------------------------------------------------------------------------


class TestRecordInteraction:
    def test_creates_persona_on_first_interaction(self, manager):
        exp = manager.record_interaction("ARCH", success=True)
        assert exp.persona_id == "ARCH"
        assert exp.interactions == 1
        assert exp.successes == 1
        assert exp.created_at != ""
        assert exp.updated_at != ""

    def test_failure_not_counted_as_success(self, manager):
        manager.record_interaction("DEV", success=False)
        exp = manager.get_experience("DEV")
        assert exp is not None
        assert exp.interactions == 1
        assert exp.successes == 0
        assert exp.success_rate == 0.0

    def test_multiple_interactions_accumulate(self, manager):
        for _ in range(5):
            manager.record_interaction("QA", success=True)
        exp = manager.get_experience("QA")
        assert exp.interactions == 5
        assert exp.successes == 5
        assert exp.success_rate == 1.0

    def test_context_area_increases_expertise(self, manager):
        manager.record_interaction("ML", success=True, context={"area": "pytorch"})
        exp = manager.get_experience("ML")
        assert exp.expertise_areas["pytorch"] == pytest.approx(EXPERTISE_INCREMENT)

    def test_repeated_success_area_accumulates(self, manager):
        for _ in range(3):
            manager.record_interaction("ML", success=True, context={"area": "pytorch"})
        exp = manager.get_experience("ML")
        assert exp.expertise_areas["pytorch"] == pytest.approx(EXPERTISE_INCREMENT * 3)

    def test_failure_decays_expertise(self, manager):
        manager.record_interaction("ML", success=True, context={"area": "pytorch"})
        manager.record_interaction("ML", success=False, context={"area": "pytorch"})
        exp = manager.get_experience("ML")
        assert exp.expertise_areas["pytorch"] == pytest.approx(EXPERTISE_INCREMENT - 1.0)

    def test_expertise_capped_at_max(self, manager):
        for _ in range(30):
            manager.record_interaction("ML", success=True, context={"area": "pytorch"})
        exp = manager.get_experience("ML")
        assert exp.expertise_areas["pytorch"] <= EXPERTISE_MAX

    def test_expertise_never_below_zero(self, manager):
        for _ in range(5):
            manager.record_interaction("ML", success=False, context={"area": "pytorch"})
        exp = manager.get_experience("ML")
        assert exp.expertise_areas["pytorch"] >= 0.0

    def test_learned_pattern_counted(self, manager):
        manager.record_interaction(
            "ARCH", success=True, context={"pattern": "layered-design"}
        )
        exp = manager.get_experience("ARCH")
        assert exp.learned_patterns["layered-design"] == 1

    def test_context_history_recorded(self, manager):
        manager.record_interaction(
            "DEV", success=True, context={"area": "api", "task_type": "build"}
        )
        exp = manager.get_experience("DEV")
        assert len(exp.context_history) == 1
        entry = exp.context_history[0]
        assert entry["success"] is True
        assert entry["area"] == "api"
        assert entry["task_type"] == "build"

    def test_context_history_bounded(self, manager):
        for i in range(CONTEXT_HISTORY_LIMIT + 20):
            manager.record_interaction("DEV", success=True, context={"task_type": f"t{i}"})
        exp = manager.get_experience("DEV")
        assert len(exp.context_history) == CONTEXT_HISTORY_LIMIT


# ---------------------------------------------------------------------------
# Evolution levels
# ---------------------------------------------------------------------------


class TestEvolutionLevels:
    def test_core_for_new_persona(self, manager):
        assert manager.get_evolution_level("ARCH") == "core"

    def test_core_at_threshold_boundary(self, manager):
        _record_n(manager, "ARCH", 10)
        assert manager.get_evolution_level("ARCH") == "core"

    def test_accumulation_at_eleven(self, manager):
        _record_n(manager, "ARCH", ACCUMULATION_THRESHOLD)
        assert manager.get_evolution_level("ARCH") == "accumulation"

    def test_accumulation_at_fifty(self, manager):
        _record_n(manager, "ARCH", 50)
        assert manager.get_evolution_level("ARCH") == "accumulation"

    def test_deep_at_fifty_one(self, manager):
        _record_n(manager, "ARCH", DEEP_THRESHOLD)
        assert manager.get_evolution_level("ARCH") == "deep"

    def test_deep_grows_with_more(self, manager):
        _record_n(manager, "ARCH", 200)
        assert manager.get_evolution_level("ARCH") == "deep"


# ---------------------------------------------------------------------------
# Persona recommendation
# ---------------------------------------------------------------------------


class TestRecommendedPersona:
    def test_no_candidates_returns_empty(self, manager):
        assert manager.get_recommended_persona("pytorch") == ""

    def test_recommends_highest_expertise(self, manager):
        _record_n(manager, "ML", 3, area="pytorch")
        _record_n(manager, "DATA", 1, area="pytorch")
        assert manager.get_recommended_persona("pytorch") == "ML"

    def test_tiebreak_by_success_rate(self, manager):
        # Both have same expertise score (1 success each in pytorch).
        manager.record_interaction("ML", success=True, context={"area": "pytorch"})
        manager.record_interaction("ML", success=False, context={"area": "pytorch"})
        manager.record_interaction("DATA", success=True, context={"area": "pytorch"})
        # DATA has higher success rate (1.0 vs 0.5).
        assert manager.get_recommended_persona("pytorch") == "DATA"

    def test_ignores_personas_without_area(self, manager):
        _record_n(manager, "ML", 5, area="pytorch")
        _record_n(manager, "DEV", 10)  # no area
        assert manager.get_recommended_persona("pytorch") == "ML"

    def test_different_areas_isolated(self, manager):
        _record_n(manager, "SEC", 3, area="firewall")
        _record_n(manager, "ML", 3, area="pytorch")
        assert manager.get_recommended_persona("firewall") == "SEC"
        assert manager.get_recommended_persona("pytorch") == "ML"


# ---------------------------------------------------------------------------
# Export / import
# ---------------------------------------------------------------------------


class TestExportImport:
    def test_export_nonexistent_returns_empty(self, manager):
        assert manager.export_experience("NOPE") == {}

    def test_export_returns_full_dict(self, manager):
        _record_n(manager, "ARCH", 3, area="design")
        d = manager.export_experience("ARCH")
        assert d["persona_id"] == "ARCH"
        assert d["interactions"] == 3
        assert d["expertise_areas"]["design"] > 0

    def test_import_creates_persona(self, manager):
        data = {
            "persona_id": "IMPORTED",
            "interactions": 42,
            "successes": 30,
            "expertise_areas": {"x": 80.0},
            "learned_patterns": {"p": 5},
            "context_history": [],
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-02T00:00:00+00:00",
        }
        exp = manager.import_experience(data)
        assert exp.persona_id == "IMPORTED"
        assert exp.interactions == 42
        assert manager.get_experience("IMPORTED") is exp

    def test_import_overwrites_existing(self, manager):
        _record_n(manager, "ARCH", 5)
        manager.import_experience(
            {"persona_id": "ARCH", "interactions": 100, "successes": 100}
        )
        exp = manager.get_experience("ARCH")
        assert exp.interactions == 100

    def test_import_missing_persona_id_raises(self, manager):
        with pytest.raises(ValueError):
            manager.import_experience({"interactions": 5})

    def test_import_export_roundtrip(self, manager):
        _record_n(manager, "DEV", 7, area="api")
        exported = manager.export_experience("DEV")
        manager.reset()
        manager.import_experience(exported)
        exp = manager.get_experience("DEV")
        assert exp is not None
        assert exp.interactions == 7
        assert exp.expertise_areas["api"] == exported["expertise_areas"]["api"]


# ---------------------------------------------------------------------------
# Save / load
# ---------------------------------------------------------------------------


class TestSaveLoad:
    def test_save_creates_state_file(self, manager, tmp_path):
        _record_n(manager, "ARCH", 3, area="design")
        manager.save()
        assert (tmp_path / "state" / "persona_experiences.json").exists()

    def test_load_restores_experiences(self, tmp_path):
        m1 = DynamicPersonaManager(tmp_path)
        _record_n(m1, "ARCH", 12, area="design")
        m1.save()
        m2 = DynamicPersonaManager(tmp_path)
        exp = m2.get_experience("ARCH")
        assert exp is not None
        assert exp.interactions == 12
        assert exp.expertise_areas["design"] > 0

    def test_load_preserves_evolution_level(self, tmp_path):
        m1 = DynamicPersonaManager(tmp_path)
        _record_n(m1, "ARCH", 60)
        m1.save()
        m2 = DynamicPersonaManager(tmp_path)
        assert m2.get_evolution_level("ARCH") == "deep"

    def test_load_missing_file_is_empty(self, tmp_path):
        m = DynamicPersonaManager(tmp_path)
        assert m.list_personas() == []

    def test_load_corrupt_file_is_empty(self, tmp_path):
        state = tmp_path / "state"
        state.mkdir(parents=True)
        (state / "persona_experiences.json").write_text("{not valid json", encoding="utf-8")
        m = DynamicPersonaManager(tmp_path)
        assert m.list_personas() == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_get_experience_nonexistent_returns_none(self, manager):
        assert manager.get_experience("GHOST") is None

    def test_record_with_none_context(self, manager):
        exp = manager.record_interaction("ARCH", success=True, context=None)
        assert exp.interactions == 1
        assert exp.context_history[0]["success"] is True

    def test_record_with_empty_context(self, manager):
        exp = manager.record_interaction("ARCH", success=True, context={})
        assert exp.interactions == 1
        assert exp.expertise_areas == {}

    def test_thread_safety(self, manager):
        def worker(pid: str) -> None:
            for _ in range(50):
                manager.record_interaction(pid, success=True, context={"area": "x"})

        threads = [threading.Thread(target=worker, args=(f"P{i}",)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        for i in range(4):
            exp = manager.get_experience(f"P{i}")
            assert exp is not None
            assert exp.interactions == 50

    def test_root_resolved_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AGENT_OS_ROOT", str(tmp_path))
        m = DynamicPersonaManager()
        assert m.root == tmp_path

    def test_list_personas(self, manager):
        _record_n(manager, "ARCH", 1)
        _record_n(manager, "DEV", 1)
        assert sorted(manager.list_personas()) == ["ARCH", "DEV"]

    def test_reset_clears_in_memory(self, manager):
        _record_n(manager, "ARCH", 5)
        manager.reset()
        assert manager.list_personas() == []
        assert manager.get_experience("ARCH") is None

    def test_learned_patterns_trimmed_when_over_limit(self, manager):
        """Cover lines 224-229: learned patterns exceeding LEARNED_PATTERNS_LIMIT are trimmed."""
        from runtime.dynamic_persona import LEARNED_PATTERNS_LIMIT

        for i in range(LEARNED_PATTERNS_LIMIT + 20):
            manager.record_interaction(
                "ARCH", success=True, context={"pattern": f"pattern-{i}"}
            )
        exp = manager.get_experience("ARCH")
        assert len(exp.learned_patterns) == LEARNED_PATTERNS_LIMIT

    def test_root_resolved_by_walking_parents(self, tmp_path, monkeypatch):
        """Cover lines 128-132: root resolved by walking up to find .ai marker."""
        monkeypatch.delenv("AGENT_OS_ROOT", raising=False)
        # Create a .ai directory structure under tmp_path
        ai_dir = tmp_path / ".ai"
        (ai_dir / "state").mkdir(parents=True)
        # Place a fake module file inside .ai/runtime/ to simulate __file__
        fake_runtime = ai_dir / "runtime"
        fake_runtime.mkdir(parents=True)
        fake_file = fake_runtime / "dynamic_persona.py"
        fake_file.write_text("# placeholder", encoding="utf-8")
        # Monkeypatch __file__ to point inside the .ai tree
        import runtime.dynamic_persona as mod

        original_file = mod.__file__
        monkeypatch.setattr(mod, "__file__", str(fake_file))
        try:
            m = DynamicPersonaManager()
            assert m.root == ai_dir
        finally:
            monkeypatch.setattr(mod, "__file__", original_file)

    def test_root_fallback_when_no_ai_marker(self, tmp_path, monkeypatch):
        """Cover line 132: _resolve_root falls back to here.parent when no .ai found."""
        monkeypatch.delenv("AGENT_OS_ROOT", raising=False)
        # Place a fake module file in a directory with no .ai ancestor
        fake_dir = tmp_path / "some_pkg"
        fake_dir.mkdir(parents=True)
        fake_file = fake_dir / "dynamic_persona.py"
        fake_file.write_text("# placeholder", encoding="utf-8")
        import runtime.dynamic_persona as mod

        original_file = mod.__file__
        monkeypatch.setattr(mod, "__file__", str(fake_file))
        try:
            m = DynamicPersonaManager()
            assert m.root == fake_dir
        finally:
            monkeypatch.setattr(mod, "__file__", original_file)
