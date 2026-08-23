"""Tests for aizee_mcp/tools/seo_multipage_checks.py — cross-page SEO checks.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

from aizee_mcp.tools.seo_multipage_checks import (
    find_broken_internal_links,
    find_duplicate_content,
    find_duplicate_meta_descriptions,
    find_duplicate_titles,
    find_orphan_pages,
    find_redirect_chains_and_loops,
    run_multipage_checks,
)
from aizee_mcp.tools.seo_page_reporters import PageData


class TestFindDuplicateTitles:
    def test_no_duplicates(self) -> None:
        pages = [
            PageData(url="https://a.com", title="Title A"),
            PageData(url="https://b.com", title="Title B"),
        ]
        issues = find_duplicate_titles(pages)
        assert issues == []

    def test_finds_duplicates(self) -> None:
        pages = [
            PageData(url="https://a.com", title="Same Title"),
            PageData(url="https://b.com", title="Same Title"),
        ]
        issues = find_duplicate_titles(pages)
        assert len(issues) == 2
        assert all(i["issue_type"] == "duplicate-title" for i in issues)

    def test_ignores_missing_titles(self) -> None:
        pages = [
            PageData(url="https://a.com", title=None),
            PageData(url="https://b.com", title=None),
        ]
        issues = find_duplicate_titles(pages)
        assert issues == []


class TestFindDuplicateMetaDescriptions:
    def test_finds_duplicates(self) -> None:
        pages = [
            PageData(url="https://a.com", meta_description="Same desc"),
            PageData(url="https://b.com", meta_description="Same desc"),
        ]
        issues = find_duplicate_meta_descriptions(pages)
        assert len(issues) == 2


class TestFindDuplicateContent:
    def test_finds_duplicates(self) -> None:
        pages = [
            PageData(url="https://a.com", content_hash="abc123"),
            PageData(url="https://b.com", content_hash="abc123"),
        ]
        issues = find_duplicate_content(pages)
        assert len(issues) == 2
        assert all(i["issue_type"] == "duplicate-content" for i in issues)


class TestFindRedirectChainsAndLoops:
    def test_redirect_chain(self) -> None:
        pages = [
            PageData(url="https://a.com", status_code=301, redirect_url="https://b.com"),
            PageData(url="https://b.com", status_code=301, redirect_url="https://c.com"),
            PageData(url="https://c.com", status_code=200),
        ]
        issues = find_redirect_chains_and_loops(pages)
        chain_issues = [i for i in issues if i["issue_type"] == "redirect-chain"]
        assert len(chain_issues) >= 1

    def test_redirect_loop(self) -> None:
        pages = [
            PageData(url="https://a.com", status_code=301, redirect_url="https://b.com"),
            PageData(url="https://b.com", status_code=301, redirect_url="https://a.com"),
        ]
        issues = find_redirect_chains_and_loops(pages)
        loop_issues = [i for i in issues if i["issue_type"] == "redirect-loop"]
        assert len(loop_issues) >= 1


class TestFindOrphanPages:
    def test_orphan_detected(self) -> None:
        pages = [
            PageData(url="https://a.com", status_code=200),
            PageData(url="https://b.com", status_code=200),
        ]
        # Only a links to b; b is not orphan, a is orphan (no inlinks)
        internal_links = {"https://a.com": ["https://b.com"]}
        issues = find_orphan_pages(pages, internal_links)
        orphan_urls = [i["page_url"] for i in issues]
        assert "https://a.com" in orphan_urls
        assert "https://b.com" not in orphan_urls

    def test_no_internal_links_returns_empty(self) -> None:
        pages = [PageData(url="https://a.com")]
        assert find_orphan_pages(pages, None) == []


class TestFindBrokenInternalLinks:
    def test_broken_link_detected(self) -> None:
        pages = [
            PageData(url="https://a.com", status_code=200),
            PageData(url="https://b.com", status_code=404),
        ]
        internal_links = {"https://a.com": ["https://b.com"]}
        issues = find_broken_internal_links(pages, internal_links)
        assert len(issues) == 1
        assert issues[0]["issue_type"] == "broken-internal-link"

    def test_no_internal_links_returns_empty(self) -> None:
        pages = [PageData(url="https://a.com", status_code=404)]
        assert find_broken_internal_links(pages, None) == []


class TestRunMultipageChecks:
    def test_combines_all_checks(self) -> None:
        pages = [
            PageData(url="https://a.com", title="Dup", meta_description="D",
                     content_hash="h1", status_code=200),
            PageData(url="https://b.com", title="Dup", meta_description="D",
                     content_hash="h1", status_code=200),
        ]
        issues = run_multipage_checks(pages)
        types = {i["issue_type"] for i in issues}
        assert "duplicate-title" in types
        assert "duplicate-meta-description" in types
        assert "duplicate-content" in types
