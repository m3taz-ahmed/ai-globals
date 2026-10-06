"""Tests for WS-H: Confidence gating (CONF-W1)."""

from __future__ import annotations

import pytest

from runtime.confidence_gate import ConfidenceGate, ConfidenceLevel, Evidence


class TestConfidenceGate:
    """Evidence-weighted confidence gate."""

    def test_all_evidence_pass_high_confidence(self) -> None:
        gate = ConfidenceGate(threshold=0.7)
        gate.add_evidence(Evidence("gate", True, 0.4, "allowed"))
        gate.add_evidence(Evidence("test", True, 0.3, "passed"))
        gate.add_evidence(Evidence("lint", True, 0.15, "clean"))
        gate.add_evidence(Evidence("mypy", True, 0.15, "ok"))
        v = gate.evaluate()
        assert v.score == 1.0
        assert v.confident
        assert v.level is ConfidenceLevel.HIGH

    def test_some_evidence_fail_low_confidence(self) -> None:
        gate = ConfidenceGate(threshold=0.8)
        gate.add_evidence(Evidence("gate", True, 0.4, "allowed"))
        gate.add_evidence(Evidence("test", False, 0.3, "failed"))
        gate.add_evidence(Evidence("lint", True, 0.15, "clean"))
        gate.add_evidence(Evidence("mypy", True, 0.15, "ok"))
        v = gate.evaluate()
        assert v.score < 1.0
        assert not v.confident  # 0.7 < 0.8 threshold
        assert "test" in v.reason

    def test_no_evidence_fail_closed(self) -> None:
        gate = ConfidenceGate(threshold=0.7)
        v = gate.evaluate()
        assert v.score == 0.0
        assert not v.confident
        assert v.level is ConfidenceLevel.CRITICAL

    def test_zero_weight_fail_closed(self) -> None:
        gate = ConfidenceGate(threshold=0.7)
        gate.add_evidence(Evidence("test", True, 0.0))
        v = gate.evaluate()
        assert v.score == 0.0
        assert not v.confident

    def test_confidence_levels(self) -> None:
        # HIGH: score >= 0.8
        gate = ConfidenceGate(threshold=0.5)
        gate.add_evidence(Evidence("a", True, 0.5))
        gate.add_evidence(Evidence("b", True, 0.5))
        assert gate.evaluate().level is ConfidenceLevel.HIGH

        # MEDIUM: 0.5 <= score < 0.8
        gate = ConfidenceGate(threshold=0.5)
        gate.add_evidence(Evidence("a", True, 0.5))
        gate.add_evidence(Evidence("b", False, 0.5))
        assert gate.evaluate().level is ConfidenceLevel.MEDIUM

        # LOW: 0.2 <= score < 0.5
        gate = ConfidenceGate(threshold=0.5)
        gate.add_evidence(Evidence("a", False, 0.8))
        gate.add_evidence(Evidence("b", True, 0.2))
        v = gate.evaluate()
        assert v.level is ConfidenceLevel.LOW

    def test_threshold_boundary(self) -> None:
        gate = ConfidenceGate(threshold=0.7)
        gate.add_evidence(Evidence("a", True, 0.7))
        gate.add_evidence(Evidence("b", True, 0.3))
        v = gate.evaluate()
        assert v.score == 1.0
        assert v.confident  # 1.0 >= 0.7

    def test_reset(self) -> None:
        gate = ConfidenceGate(threshold=0.7)
        gate.add_evidence(Evidence("a", True, 1.0))
        gate.reset()
        v = gate.evaluate()
        assert v.score == 0.0

    def test_to_dict(self) -> None:
        gate = ConfidenceGate(threshold=0.7)
        gate.add_evidence(Evidence("test", True, 1.0, "passed"))
        v = gate.evaluate()
        d = v.to_dict()
        assert "score" in d
        assert "confident" in d
        assert "level" in d
        assert "evidence" in d
        assert len(d["evidence"]) == 1

    def test_add_evidence_simple(self) -> None:
        gate = ConfidenceGate(threshold=0.7)
        gate.add_evidence_simple("test", True, 1.0, "passed")
        v = gate.evaluate()
        assert v.score == 1.0
        assert v.confident

    # --- Weight validation tests (review fix) ---

    def test_weight_validation_rejects_negative(self) -> None:
        gate = ConfidenceGate()
        with pytest.raises(ValueError, match="weight must be between"):
            gate.add_evidence(Evidence("test", True, -0.1))

    def test_weight_validation_rejects_above_one(self) -> None:
        gate = ConfidenceGate()
        with pytest.raises(ValueError, match="weight must be between"):
            gate.add_evidence(Evidence("test", True, 1.5))

    def test_weight_validation_simple_rejects_negative(self) -> None:
        gate = ConfidenceGate()
        with pytest.raises(ValueError, match="weight must be between"):
            gate.add_evidence_simple("test", True, -0.5)

    def test_weight_validation_accepts_boundary_zero(self) -> None:
        gate = ConfidenceGate()
        gate.add_evidence(Evidence("test", True, 0.0))
        assert len(gate._evidence) == 1

    def test_weight_validation_accepts_boundary_one(self) -> None:
        gate = ConfidenceGate()
        gate.add_evidence(Evidence("test", True, 1.0))
        assert len(gate._evidence) == 1

    def test_frozen_verdict(self) -> None:
        gate = ConfidenceGate(threshold=0.7)
        gate.add_evidence(Evidence("a", True, 1.0))
        v = gate.evaluate()
        try:
            v.score = 0.5  # type: ignore[misc]
            raise AssertionError("should be frozen")
        except AttributeError:
            pass
