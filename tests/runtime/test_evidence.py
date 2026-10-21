"""Tests for runtime/evidence.py and evidence tiers in security_scanner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from runtime.evidence import Evidence, EvidenceLedger, EvidenceTier
from runtime.security_scanner import ScanFinding, ScanReport, ScanSeverity, SecurityScanner


class TestEvidenceModel:
    def test_tier_values(self):
        assert EvidenceTier.OBSERVATION.value == "observation"
        assert EvidenceTier.DERIVATION.value == "derivation"
        assert EvidenceTier.INFERENCE.value == "inference"
        assert EvidenceTier.UNKNOWN.value == "unknown"

    def test_evidence_to_dict_roundtrip_fields(self):
        ev = Evidence(
            EvidenceTier.OBSERVATION, "hardcoded key found",
            source="SEC-KEY", location="app.py:12", limitations="pattern match only",
        )
        d = ev.to_dict()
        assert d["tier"] == "observation"
        assert d["claim"] == "hardcoded key found"
        assert d["source"] == "SEC-KEY"
        assert d["location"] == "app.py:12"
        assert d["limitations"] == "pattern match only"


class TestEvidenceLedger:
    def test_record_and_lookup_by_tier(self):
        ledger = EvidenceLedger()
        ledger.record(EvidenceTier.OBSERVATION, "seen")
        ledger.record(EvidenceTier.INFERENCE, "guessed")
        ledger.record(EvidenceTier.OBSERVATION, "seen2")
        assert len(ledger.by_tier(EvidenceTier.OBSERVATION)) == 2
        assert len(ledger.by_tier(EvidenceTier.INFERENCE)) == 1
        assert ledger.records[0].claim == "seen"

    def test_unknowns_are_retained(self):
        """Unresolved records must stay inspectable, never dropped."""
        ledger = EvidenceLedger()
        ledger.record(EvidenceTier.UNKNOWN, "unresolved target", source="probe")
        assert len(ledger.unknowns) == 1
        assert ledger.unknowns[0].claim == "unresolved target"

    def test_summary_zero_fills_all_tiers(self):
        ledger = EvidenceLedger()
        ledger.record(EvidenceTier.OBSERVATION, "x")
        s = ledger.summary()
        assert s == {
            "observation": 1, "derivation": 0, "inference": 0, "unknown": 0,
        }

    def test_to_dict_structure(self):
        ledger = EvidenceLedger()
        ledger.record(EvidenceTier.DERIVATION, "counted", source="agg")
        d = ledger.to_dict()
        assert d["summary"]["derivation"] == 1
        assert d["records"][0]["claim"] == "counted"


class TestScannerEvidence:
    def test_finding_defaults_to_observation(self):
        f = ScanFinding("R1", ScanSeverity.HIGH, "cat", "msg")
        assert f.evidence_tier is EvidenceTier.OBSERVATION
        assert f.to_dict()["evidence_tier"] == "observation"

    def test_report_evidence_summary_counts(self):
        report = ScanReport(target="t")
        report.findings.append(
            ScanFinding("R1", ScanSeverity.HIGH, "c", "m"))
        report.findings.append(
            ScanFinding("R2", ScanSeverity.LOW, "c", "m",
                        evidence_tier=EvidenceTier.DERIVATION))
        report.findings.append(
            ScanFinding("R3", ScanSeverity.LOW, "c", "m",
                        evidence_tier=EvidenceTier.DERIVATION))
        assert report.evidence_summary() == {
            "observation": 1, "derivation": 2, "inference": 0, "unknown": 0,
        }
        assert report.to_dict()["evidence"]["derivation"] == 2

    def test_builtin_scan_tags_gitignored_env_as_derivation(self, tmp_path: Path):
        """The severity-downgraded .env path is derived, not directly observed."""
        (tmp_path / ".env").write_text("SECRET=hunter2", encoding="utf-8")
        with patch.object(SecurityScanner, "_is_git_ignored", return_value=True):
            report = SecurityScanner().scan(tmp_path, use_tools=False)
        env_findings = [f for f in report.findings if f.rule_id == "SEC-ENVFILE"]
        assert env_findings
        assert all(f.evidence_tier is EvidenceTier.DERIVATION for f in env_findings)

    def test_builtin_scan_tags_plain_findings_as_observation(self, tmp_path: Path):
        (tmp_path / "app.py").write_text(
            'password = "supersecretvalue123"\n', encoding="utf-8"
        )
        report = SecurityScanner().scan(tmp_path, use_tools=False)
        assert report.findings
        assert any(f.evidence_tier is EvidenceTier.OBSERVATION for f in report.findings)
