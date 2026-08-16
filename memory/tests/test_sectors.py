"""Tests for memory/sectors.py — cognitive sector classification."""

from __future__ import annotations

from memory.sectors import Sector, SectorClassifier


class TestSectorClassifier:
    def test_episodic_classification(self) -> None:
        clf = SectorClassifier()
        assert clf.classify("I remember when we deployed yesterday") == Sector.EPISODIC

    def test_procedural_classification(self) -> None:
        clf = SectorClassifier()
        assert clf.classify("How to deploy: first run build, then deploy") == Sector.PROCEDURAL

    def test_emotional_classification(self) -> None:
        clf = SectorClassifier()
        assert clf.classify("I feel happy about the amazing results") == Sector.EMOTIONAL

    def test_reflective_classification(self) -> None:
        clf = SectorClassifier()
        assert clf.classify("I realize the pattern here, I think") == Sector.REFLECTIVE

    def test_semantic_classification(self) -> None:
        clf = SectorClassifier()
        assert clf.classify("Docker is a containerization platform") == Sector.SEMANTIC

    def test_default_is_semantic(self) -> None:
        clf = SectorClassifier()
        assert clf.classify("xyz") == Sector.SEMANTIC

    def test_decay_score_decreases_over_time(self) -> None:
        clf = SectorClassifier()
        recent = clf.decay_score(Sector.EPISODIC, 1.0, days_since=1)
        old = clf.decay_score(Sector.EPISODIC, 1.0, days_since=100)
        assert recent > old

    def test_reflective_decays_slowest(self) -> None:
        clf = SectorClassifier()
        reflective = clf.decay_score(Sector.REFLECTIVE, 1.0, days_since=100)
        episodic = clf.decay_score(Sector.EPISODIC, 1.0, days_since=100)
        assert reflective > episodic

    def test_sector_weights(self) -> None:
        clf = SectorClassifier()
        assert clf.sector_weight(Sector.EMOTIONAL) == 1.3
        assert clf.sector_weight(Sector.SEMANTIC) == 1.0

    def test_cross_sector_boost(self) -> None:
        clf = SectorClassifier()
        boost = clf.cross_sector_boost(Sector.SEMANTIC, Sector.PROCEDURAL)
        assert boost == 0.8
