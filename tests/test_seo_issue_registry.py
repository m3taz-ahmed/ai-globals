"""Tests for runtime/seo_issue_registry.py — typed SEO audit issue registry.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

from runtime.seo_issue_registry import (
    IssueSeverity,
    enrich_issue,
    get_all_issues,
    get_issue_descriptor,
    get_issues_by_severity,
    issue_count_by_severity,
    sort_issues_by_severity,
)


class TestIssueRegistry:
    def test_get_known_issue(self) -> None:
        desc = get_issue_descriptor("missing-title")
        assert desc is not None
        assert desc.severity == IssueSeverity.CRITICAL
        assert "title" in desc.title.lower()

    def test_get_unknown_issue_returns_none(self) -> None:
        assert get_issue_descriptor("nonexistent-issue") is None

    def test_get_all_issues_returns_copy(self) -> None:
        all_issues = get_all_issues()
        original_count = len(all_issues)
        all_issues.clear()
        assert len(get_all_issues()) == original_count

    def test_get_issues_by_severity(self) -> None:
        critical = get_issues_by_severity(IssueSeverity.CRITICAL)
        assert all(i.severity == IssueSeverity.CRITICAL for i in critical)
        assert len(critical) >= 3  # blocked-page, server-error, broken-internal-link, missing-title

    def test_issue_has_all_fields(self) -> None:
        desc = get_issue_descriptor("duplicate-title")
        assert desc is not None
        assert desc.id == "duplicate-title"
        assert desc.severity == IssueSeverity.WARNING
        assert desc.title
        assert desc.explanation
        assert desc.how_to_fix


class TestEnrichIssue:
    def test_enriches_known_issue(self) -> None:
        raw = {"issue_type": "missing-title", "page_url": "https://example.com"}
        enriched = enrich_issue(raw)
        assert enriched["severity"] == "critical"
        assert enriched["title"]
        assert enriched["explanation"]
        assert enriched["how_to_fix"]
        assert enriched["page_url"] == "https://example.com"

    def test_unknown_issue_passthrough(self) -> None:
        raw = {"issue_type": "unknown-xyz", "page_url": "https://example.com"}
        enriched = enrich_issue(raw)
        assert "severity" not in enriched
        assert enriched["issue_type"] == "unknown-xyz"


class TestSortAndCount:
    def test_sort_critical_first(self) -> None:
        issues = [
            {"issue_type": "duplicate-title"},
            {"issue_type": "missing-title"},
            {"issue_type": "deep-page"},
        ]
        sorted_issues = sort_issues_by_severity(issues)
        assert sorted_issues[0]["issue_type"] == "missing-title"  # critical
        assert sorted_issues[-1]["issue_type"] == "deep-page"  # info

    def test_count_by_severity(self) -> None:
        issues = [
            {"issue_type": "missing-title"},
            {"issue_type": "duplicate-title"},
            {"issue_type": "deep-page"},
        ]
        counts = issue_count_by_severity(issues)
        assert counts["critical"] == 1
        assert counts["warning"] == 1
        assert counts["info"] == 1
