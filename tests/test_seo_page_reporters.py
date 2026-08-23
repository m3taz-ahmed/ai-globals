"""Tests for aizee_mcp/tools/seo_page_reporters.py — per-page SEO checks.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

from aizee_mcp.tools.seo_page_reporters import (
    THIN_CONTENT_WORDS,
    TITLE_MAX_CHARS,
    PageData,
    run_page_reporters,
)


class TestRunPageReporters:
    def test_clean_page_no_issues(self) -> None:
        page = PageData(
            url="https://example.com",
            title="A Good Title Tag",
            meta_description="A good meta description for the page that is long enough to pass the minimum length check.",
            canonical_url="https://example.com",
            h1_count=1,
            heading_order=[1, 2, 3],
            is_indexable=True,
            word_count=500,
            has_structured_data=True,
            has_hreflang=True,
        )
        issues = run_page_reporters(page)
        assert issues == []

    def test_missing_title(self) -> None:
        page = PageData(url="https://example.com", title=None)
        issues = run_page_reporters(page)
        types = [i["issue_type"] for i in issues]
        assert "missing-title" in types

    def test_title_too_long(self) -> None:
        page = PageData(
            url="https://example.com",
            title="A" * (TITLE_MAX_CHARS + 10),
            meta_description="x" * 100,
            canonical_url="https://example.com",
            h1_count=1,
            word_count=500,
            has_structured_data=True,
            has_hreflang=True,
        )
        issues = run_page_reporters(page)
        types = [i["issue_type"] for i in issues]
        assert "title-too-long" in types

    def test_missing_meta_description(self) -> None:
        page = PageData(url="https://example.com", title="Good Title", meta_description=None)
        issues = run_page_reporters(page)
        types = [i["issue_type"] for i in issues]
        assert "missing-meta-description" in types

    def test_missing_h1(self) -> None:
        page = PageData(
            url="https://example.com", title="T", meta_description="M" * 80,
            canonical_url="https://example.com", h1_count=0, word_count=500,
            has_structured_data=True, has_hreflang=True,
        )
        issues = run_page_reporters(page)
        types = [i["issue_type"] for i in issues]
        assert "missing-h1" in types

    def test_multiple_h1(self) -> None:
        page = PageData(
            url="https://example.com", title="T", meta_description="M" * 80,
            canonical_url="https://example.com", h1_count=3, word_count=500,
            has_structured_data=True, has_hreflang=True,
        )
        issues = run_page_reporters(page)
        types = [i["issue_type"] for i in issues]
        assert "multiple-h1" in types

    def test_thin_content(self) -> None:
        page = PageData(
            url="https://example.com", title="T", meta_description="M" * 80,
            canonical_url="https://example.com", h1_count=1, word_count=THIN_CONTENT_WORDS - 10,
            has_structured_data=True, has_hreflang=True,
        )
        issues = run_page_reporters(page)
        types = [i["issue_type"] for i in issues]
        assert "thin-content" in types

    def test_blocked_page(self) -> None:
        page = PageData(url="https://example.com", status_code=403, fetch_class="blocked")
        issues = run_page_reporters(page)
        assert len(issues) == 1
        assert issues[0]["issue_type"] == "blocked-page"

    def test_server_error(self) -> None:
        page = PageData(url="https://example.com", status_code=500)
        issues = run_page_reporters(page)
        types = [i["issue_type"] for i in issues]
        assert "server-error" in types

    def test_broken_page(self) -> None:
        page = PageData(url="https://example.com", status_code=404)
        issues = run_page_reporters(page)
        types = [i["issue_type"] for i in issues]
        assert "broken-page" in types

    def test_noindex_page(self) -> None:
        page = PageData(
            url="https://example.com", title="T", meta_description="M" * 80,
            canonical_url="https://example.com", h1_count=1, word_count=500,
            is_indexable=False, robots_meta="noindex",
            has_structured_data=True, has_hreflang=True,
        )
        issues = run_page_reporters(page)
        types = [i["issue_type"] for i in issues]
        assert "noindex-page" in types

    def test_heading_order_skip(self) -> None:
        page = PageData(
            url="https://example.com", title="T", meta_description="M" * 80,
            canonical_url="https://example.com", h1_count=1,
            heading_order=[1, 3], word_count=500,
            has_structured_data=True, has_hreflang=True,
        )
        issues = run_page_reporters(page)
        types = [i["issue_type"] for i in issues]
        assert "heading-order-skip" in types

    def test_issues_are_enriched(self) -> None:
        page = PageData(url="https://example.com", title=None)
        issues = run_page_reporters(page)
        assert len(issues) > 0
        issue = issues[0]
        assert "severity" in issue
        assert "title" in issue
        assert "explanation" in issue
        assert "how_to_fix" in issue
