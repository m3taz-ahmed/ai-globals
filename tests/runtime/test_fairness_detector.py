"""Tests for runtime/fairness_detector.py — EU AI Act fairness detection."""

from __future__ import annotations

import pytest

from runtime.fairness_detector import (
    FairnessDetector,
    FairnessDetectorError,
    FairnessStrategy,
    ProtectedAttribute,
)
from runtime.schemas import ValidationError


class TestProtectedAttributes:
    @pytest.mark.parametrize("field,attr", [
        ("age", ProtectedAttribute.AGE),
        ("date_of_birth", ProtectedAttribute.AGE),
        ("dob", ProtectedAttribute.AGE),
        ("gender", ProtectedAttribute.GENDER),
        ("sex", ProtectedAttribute.SEX),
        ("race", ProtectedAttribute.RACE),
        ("ethnicity", ProtectedAttribute.ETHNICITY),
        ("religion", ProtectedAttribute.RELIGION),
        ("disability", ProtectedAttribute.DISABILITY),
        ("nationality", ProtectedAttribute.NATIONALITY),
        ("marital_status", ProtectedAttribute.MARITAL_STATUS),
        ("political_opinion", ProtectedAttribute.POLITICAL_OPINION),
    ])
    def test_direct_match(self, field, attr):
        rep = FairnessDetector().detect({field: "str"})
        assert rep.protected_found == 1
        f = rep.findings[0]
        assert f.is_protected and f.severity == "high"
        assert attr.value in f.evidence

    def test_case_and_space_normalized(self):
        rep = FairnessDetector().detect({"  Age ": "int", "DATE OF BIRTH": "str"})
        assert rep.protected_found == 2


class TestProxyAttributes:
    @pytest.mark.parametrize("field,proxy_for", [
        ("zip_code", ProtectedAttribute.RACE),
        ("postcode", ProtectedAttribute.RACE),
        ("first_name", ProtectedAttribute.RACE),
        ("surname", ProtectedAttribute.ETHNICITY),
        ("credit_score", ProtectedAttribute.RACE),
        ("address", ProtectedAttribute.NATIONALITY),
        ("language", ProtectedAttribute.NATIONALITY),
    ])
    def test_proxy_match(self, field, proxy_for):
        rep = FairnessDetector().detect({field: "str"})
        assert rep.proxies_found == 1
        f = rep.findings[0]
        assert f.is_proxy and not f.is_protected
        assert f.proxy_for is proxy_for
        assert f.severity == "medium"

    def test_protected_wins_over_proxy(self):
        # "name" is a proxy for RACE but not protected; check priority path
        rep = FairnessDetector().detect({"name": "str"})
        assert rep.findings[0].is_proxy

    def test_clean_field_no_finding(self):
        rep = FairnessDetector().detect({"order_total": "float", "sku": "str"})
        assert rep.findings == []
        assert rep.protected_found == 0 and rep.proxies_found == 0


class TestReport:
    def test_empty_schema_raises(self):
        with pytest.raises(ValidationError):
            FairnessDetector().detect({})

    def test_counts(self):
        rep = FairnessDetector().detect({
            "age": "int", "zip_code": "str", "income": "float"})
        assert rep.total_attributes_checked == 3
        assert rep.protected_found == 1
        assert rep.proxies_found == 1

    def test_to_dict(self):
        rep = FairnessDetector().detect({"age": "int"})
        d = rep.to_dict()
        assert d["strategy_recommended"] == "differential_privacy"
        assert d["findings"][0]["proxy_for"] is None
        assert d["compliance_notes"]

    def test_strategy_recommendations(self):
        fd = FairnessDetector()
        assert fd.detect({"age": "int"}).strategy_recommended is \
            FairnessStrategy.DIFFERENTIAL_PRIVACY
        assert fd.detect({"zip_code": "str"}).strategy_recommended is \
            FairnessStrategy.EQUALIZED_ODDS
        assert fd.detect({"income": "f"}).strategy_recommended is \
            FairnessStrategy.DEMOGRAPHIC_PARITY


class TestComplianceNotes:
    def test_protected_note(self):
        rep = FairnessDetector().detect({"age": "int"})
        assert any("protected attributes detected" in n for n in rep.compliance_notes)
        assert any("Fairness Impossibility" in n for n in rep.compliance_notes)

    def test_proxy_note(self):
        rep = FairnessDetector().detect({"zip_code": "str"})
        assert any("proxy attributes detected" in n for n in rep.compliance_notes)

    def test_clean_note(self):
        rep = FairnessDetector().detect({"x": "int"})
        assert any("no protected or proxy" in n for n in rep.compliance_notes)


class TestImpossibility:
    def test_triple_impossible(self):
        fd = FairnessDetector()
        notes = fd.check_fairness_impossibility([
            FairnessStrategy.EQUALIZED_ODDS,
            FairnessStrategy.DIFFERENTIAL_PRIVACY,
            FairnessStrategy.PREDICTIVE_PARITY,
        ])
        assert any("cannot all be simultaneously satisfied" in n for n in notes)
        # pair EO+PP also flagged
        assert any("generally incompatible" in n for n in notes)

    def test_pair_impossible(self):
        fd = FairnessDetector()
        notes = fd.check_fairness_impossibility([
            FairnessStrategy.DEMOGRAPHIC_PARITY,
            FairnessStrategy.PREDICTIVE_PARITY,
        ])
        assert any("generally incompatible" in n for n in notes)

    def test_compatible_no_notes(self):
        fd = FairnessDetector()
        notes = fd.check_fairness_impossibility([
            FairnessStrategy.EQUALIZED_ODDS, FairnessStrategy.DEMOGRAPHIC_PARITY])
        assert notes == []

    def test_error_type(self):
        err = FairnessDetectorError("x")
        assert err.error_code == "FAIRNESS_ERROR"
