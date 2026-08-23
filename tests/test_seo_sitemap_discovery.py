"""Tests for aizee_mcp/tools/seo_sitemap_discovery.py — robots.txt + sitemap discovery.

FAST tier — no MCP, no kernel, no model loading. No network calls.
"""

from __future__ import annotations

from aizee_mcp.tools.seo_sitemap_discovery import (
    RobotsResult,
    get_origin,
    is_crawlable_url,
    is_probably_sitemap,
    is_same_origin,
    normalize_url,
    parse_robots_txt,
)


class TestParseRobotsTxt:
    def test_none_text_allows_all(self) -> None:
        result = parse_robots_txt("https://example.com", None)
        assert result.is_allowed("https://example.com/any") is True
        assert result.sitemap_urls == []

    def test_extracts_sitemap_urls(self) -> None:
        text = "User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml\n"
        result = parse_robots_txt("https://example.com", text)
        assert "https://example.com/sitemap.xml" in result.sitemap_urls

    def test_multiple_sitemaps(self) -> None:
        text = "Sitemap: https://a.com/s1.xml\nSitemap: https://a.com/s2.xml\n"
        result = parse_robots_txt("https://a.com", text)
        assert len(result.sitemap_urls) == 2

    def test_comments_ignored(self) -> None:
        text = "# This is a comment\nSitemap: https://a.com/s.xml\n"
        result = parse_robots_txt("https://a.com", text)
        assert len(result.sitemap_urls) == 1


class TestIsProbablySitemap:
    def test_xml_content_type(self) -> None:
        assert is_probably_sitemap("application/xml", "<urlset>") is True

    def test_urlset_body(self) -> None:
        assert is_probably_sitemap(None, '<?xml version="1.0"?><urlset>') is True

    def test_sitemapindex_body(self) -> None:
        assert is_probably_sitemap(None, "<sitemapindex>") is True

    def test_html_body(self) -> None:
        assert is_probably_sitemap("text/html", "<html><body>") is False


class TestGetOrigin:
    def test_https(self) -> None:
        assert get_origin("https://example.com/path") == "https://example.com"

    def test_with_port(self) -> None:
        assert get_origin("http://localhost:8080/api") == "http://localhost:8080"


class TestIsSameOrigin:
    def test_same(self) -> None:
        assert is_same_origin("https://a.com/x", "https://a.com/y") is True

    def test_different(self) -> None:
        assert is_same_origin("https://a.com/x", "https://b.com/y") is False

    def test_different_scheme(self) -> None:
        assert is_same_origin("http://a.com/x", "https://a.com/y") is False


class TestNormalizeUrl:
    def test_strips_fragment(self) -> None:
        assert normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_preserves_query(self) -> None:
        assert normalize_url("https://example.com/page?q=1") == "https://example.com/page?q=1"


class TestIsCrawlableUrl:
    def test_no_robots_allows_all(self) -> None:
        assert is_crawlable_url("https://example.com/any", None) is True

    def test_with_robots(self) -> None:
        robots = RobotsResult(is_allowed=lambda url: False)
        assert is_crawlable_url("https://example.com/blocked", robots) is False
