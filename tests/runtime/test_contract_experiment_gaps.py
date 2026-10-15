"""Gap tests for contract_emitter.py + experiment_tracker.py."""
from __future__ import annotations

import pytest

from runtime.experiment_tracker import (
    _srm_p_value,
    _two_proportion_z,
    analyze_ab_test,
    analyze_ab_test_dict,
)
from runtime.schemas import ValidationError


class TestExperimentTracker:
    def test_unpooled_se_fallback(self):
        # a_conv=0 -> pooled_se collapses -> unpooled path
        p_a, p_b, _z, _pv = _two_proportion_z(0, 100, 50, 100)
        assert p_a == 0.0 and p_b == 0.5

    def test_srm_zero_total_and_zero_expected(self):
        assert _srm_p_value(0, 0) == 1.0
        assert _srm_p_value(100, 0, expected_ratio=1.0) == 1.0

    def test_getitem_and_get(self):
        r = analyze_ab_test(50, 1000, 60, 1000)
        assert r["p_a"] == r.p_a
        assert r.get("winner") == r.winner
        assert r.get("nope", "d") == "d"

    def test_method_not_implemented(self):
        with pytest.raises(ValidationError):
            analyze_ab_test(1, 10, 1, 10, method="cuped")

    def test_bad_visitors_and_confidence(self):
        with pytest.raises(ValidationError):
            analyze_ab_test(1, 0, 1, 10)
        with pytest.raises(ValidationError):
            analyze_ab_test(1, 10, 1, 10, confidence=1.5)
        with pytest.raises(ValidationError):
            analyze_ab_test(1, 10, 1, 10, confidence=0.0)

    def test_negative_and_overflow_conv(self):
        with pytest.raises(ValidationError):
            analyze_ab_test(-1, 10, 1, 10)
        with pytest.raises(ValidationError):
            analyze_ab_test(20, 10, 1, 10)

    def test_winner_a_and_b(self):
        ra = analyze_ab_test(90, 100, 10, 100)  # A wins clearly
        assert ra.significant and ra.winner == "A"
        rb = analyze_ab_test(10, 100, 90, 100)
        assert rb.significant and rb.winner == "B"

    def test_not_significant_no_winner(self):
        r = analyze_ab_test(50, 1000, 51, 1000)
        assert r.winner is None

    def test_dict_alias(self):
        d = analyze_ab_test_dict(50, 1000, 60, 1000)
        assert "p_value" in d and d["method"] == "z_test"

    def test_srm_mismatch_flag(self):
        # extreme split (1000 vs 10 visitors) -> srm p tiny -> srm_ok False
        r = analyze_ab_test(500, 1000, 5, 10)
        assert r.srm_ok is False
