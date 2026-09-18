"""Gap coverage: runtime/seo_issue_registry.py public API."""

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


def test_registry_populated() -> None:
    issues = get_all_issues()
    assert len(issues) > 20
    d = get_issue_descriptor("blocked-page")
    assert d is not None and d.severity is IssueSeverity.CRITICAL
    assert d.to_dict()["id"] == "blocked-page"
    assert get_issue_descriptor("nonexistent-id") is None


def test_by_severity() -> None:
    crit = get_issues_by_severity(IssueSeverity.CRITICAL)
    warn = get_issues_by_severity(IssueSeverity.WARNING)
    info = get_issues_by_severity(IssueSeverity.INFO)
    assert crit and warn and info
    assert all(d.severity is IssueSeverity.CRITICAL for d in crit)


def test_sort_and_count() -> None:
    issues = [
        {"issue_type": "nonexistent-xyz"},
        {"issue_type": "blocked-page"},
        {"id": "title-too-long"},
    ]
    sorted_issues = sort_issues_by_severity(issues)
    # critical (blocked-page) sorts first; unknown sorts last
    assert sorted_issues[0]["issue_type"] == "blocked-page"
    assert sorted_issues[-1]["issue_type"] == "nonexistent-xyz"
    counts = issue_count_by_severity(issues)
    assert counts["critical"] >= 1
    assert sum(counts.values()) == 2  # unknown id not counted


def test_enrich_issue() -> None:
    out = enrich_issue({"issue_type": "blocked-page", "url": "http://x"})
    assert out["severity"] == "critical" and "title" in out and "how_to_fix" in out
    untouched = enrich_issue({"issue_type": "unknown-abc"})
    assert "severity" not in untouched
