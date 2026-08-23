"""Tests for runtime/sarif_emitter.py — SARIF 2.1.0 emission.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

import json

from runtime.sarif_emitter import (
    build_sarif,
    sarif_to_json,
    write_sarif,
)


class TestBuildSarif:
    def test_empty_findings(self) -> None:
        sarif = build_sarif([])
        assert sarif["version"] == "2.1.0"
        assert sarif["$schema"] == "https://json.schemastore.org/sarif-2.1.0.json"
        assert len(sarif["runs"]) == 1
        assert sarif["runs"][0]["results"] == []

    def test_single_finding(self) -> None:
        findings = [{
            "issue_type": "missing-title",
            "severity": "critical",
            "title": "Missing title tag",
            "explanation": "Page has no title.",
            "how_to_fix": "Add a title tag.",
            "page_url": "https://example.com/page",
        }]
        sarif = build_sarif(findings)
        run = sarif["runs"][0]
        assert len(run["results"]) == 1
        result = run["results"][0]
        assert result["ruleId"] == "missing-title"
        assert result["level"] == "error"  # critical → error
        assert result["properties"]["aizee"]["severity"] == "critical"

    def test_warning_severity(self) -> None:
        findings = [{
            "issue_type": "duplicate-title",
            "severity": "warning",
            "title": "Duplicate title",
            "page_url": "https://example.com",
        }]
        sarif = build_sarif(findings)
        assert sarif["runs"][0]["results"][0]["level"] == "warning"

    def test_info_severity(self) -> None:
        findings = [{
            "issue_type": "deep-page",
            "severity": "info",
            "title": "Deep page",
            "page_url": "https://example.com",
        }]
        sarif = build_sarif(findings)
        assert sarif["runs"][0]["results"][0]["level"] == "note"

    def test_file_location(self) -> None:
        findings = [{
            "issue_type": "missing-title",
            "severity": "critical",
            "title": "Missing title",
            "file": "src/page.html",
            "line": 5,
        }]
        sarif = build_sarif(findings)
        result = sarif["runs"][0]["results"][0]
        assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "src/page.html"
        assert result["locations"][0]["physicalLocation"]["region"]["startLine"] == 5

    def test_synthetic_location(self) -> None:
        findings = [{
            "issue_type": "missing-title",
            "severity": "critical",
            "title": "Missing title",
        }]
        sarif = build_sarif(findings)
        result = sarif["runs"][0]["results"][0]
        assert result["properties"]["synthetic_location"] is True
        assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "SECURITY.md"

    def test_version_control_provenance(self) -> None:
        findings = []
        sarif = build_sarif(
            findings,
            repo_url="https://github.com/user/repo",
            commit_sha="abc123",
            branch="main",
        )
        run = sarif["runs"][0]
        assert "versionControlProvenance" in run
        assert run["versionControlProvenance"][0]["repositoryUri"] == "https://github.com/user/repo"
        assert run["versionControlProvenance"][0]["revisionId"] == "abc123"
        assert run["versionControlProvenance"][0]["branch"] == "main"

    def test_rules_registered(self) -> None:
        findings = [
            {"issue_type": "missing-title", "severity": "critical", "title": "T1"},
            {"issue_type": "duplicate-title", "severity": "warning", "title": "T2"},
        ]
        sarif = build_sarif(findings)
        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        assert len(rules) == 2  # Two unique issue types

    def test_dedup_rules(self) -> None:
        findings = [
            {"issue_type": "missing-title", "severity": "critical", "title": "T1", "page_url": "https://a.com"},
            {"issue_type": "missing-title", "severity": "critical", "title": "T1", "page_url": "https://b.com"},
        ]
        sarif = build_sarif(findings)
        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        assert len(rules) == 1  # Same issue type → one rule
        assert len(sarif["runs"][0]["results"]) == 2  # Two results


class TestSarifToJson:
    def test_valid_json(self) -> None:
        findings = [{"issue_type": "missing-title", "severity": "critical", "title": "T"}]
        json_str = sarif_to_json(findings)
        parsed = json.loads(json_str)
        assert parsed["version"] == "2.1.0"


class TestWriteSarif:
    def test_writes_file(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        findings = [{"issue_type": "missing-title", "severity": "critical", "title": "T"}]
        output_path = str(tmp_path / "findings.sarif")
        write_sarif(findings, output_path)
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["version"] == "2.1.0"
