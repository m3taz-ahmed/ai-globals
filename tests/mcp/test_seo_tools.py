"""Tests for aizee_mcp/tools/seo_tools.py MCP tools."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from aizee_mcp.tools.seo_tools import (  # pyright: ignore[reportMissingImports]
    _classify_schema,
    _compute_health_score,
    _content_hash,
    _count_syllables,
    _cwv_status,
    _flesch_reading_ease,
    _is_private_ip,
    _issue,
    _normalize_url,
    _parse_html,
    _SeoHtmlParser,
    _strip_html,
    _validate_url,
    _word_count,
    register_seo_tools,
)

pytestmark = pytest.mark.slow


# --- Helper to capture tool functions from a fake MCP ----------------------


class _FakeTool:
    def __call__(self, fn: Any | None = None) -> Any:
        # Support both @mcp.tool() (no-arg factory) and @mcp.tool (direct)
        if fn is not None:
            _captured_tools[fn.__name__] = fn
            return fn

        def decorator(inner_fn: Any) -> Any:
            _captured_tools[inner_fn.__name__] = inner_fn
            return inner_fn

        return decorator


class _FakeMCP:
    def __init__(self) -> None:
        self.tool = _FakeTool()


_captured_tools: dict[str, Any] = {}


def _get_tool(name: str) -> Any:
    """Register tools on a fresh fake MCP and return the named tool function."""
    _captured_tools.clear()
    fake = _FakeMCP()
    register_seo_tools(fake)
    return _captured_tools[name]


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

class TestValidateUrl:
    def test_valid_https(self):
        assert _validate_url("https://example.com") is None

    def test_valid_http(self):
        assert _validate_url("http://example.com/page") is None

    def test_invalid_scheme(self):
        result = _validate_url("ftp://example.com")
        assert result is not None
        data = json.loads(result)
        assert data["ok"] is False

    def test_no_domain(self):
        result = _validate_url("https://")
        assert result is not None

    def test_empty(self):
        result = _validate_url("")
        assert result is not None

    def test_too_long(self):
        result = _validate_url("https://example.com/" + "a" * 200000)
        assert result is not None


# ---------------------------------------------------------------------------
# HTML parser
# ---------------------------------------------------------------------------

class TestSeoHtmlParser:
    def test_extracts_title(self):
        parser = _SeoHtmlParser()
        parser.feed("<html><head><title>Test Page</title></head></html>")
        parser.close()
        assert parser.title == "Test Page"

    def test_extracts_meta_description(self):
        parser = _SeoHtmlParser()
        parser.feed('<meta name="description" content="A test page">')
        parser.close()
        assert parser.meta["description"] == "A test page"

    def test_extracts_canonical(self):
        parser = _SeoHtmlParser()
        parser.feed('<link rel="canonical" href="https://example.com/page">')
        parser.close()
        assert parser.canonical == "https://example.com/page"

    def test_extracts_h1s(self):
        parser = _SeoHtmlParser()
        parser.feed("<h1>Main Title</h1><h1>Second H1</h1>")
        parser.close()
        assert len(parser.h1s) == 2

    def test_extracts_json_ld(self):
        parser = _SeoHtmlParser()
        parser.feed('<script type="application/ld+json">{"@type":"Article","name":"Test"}</script>')
        parser.close()
        assert len(parser.json_ld) == 1
        assert "Article" in parser.json_ld[0]

    def test_extracts_og_tags(self):
        parser = _SeoHtmlParser()
        parser.feed('<meta property="og:title" content="OG Title">')
        parser.close()
        assert parser.og_tags["og:title"] == "OG Title"

    def test_extracts_images(self):
        parser = _SeoHtmlParser()
        parser.feed('<img src="test.jpg" alt="Test" width="100" height="50">')
        parser.close()
        assert len(parser.images) == 1
        assert parser.images[0]["alt"] == "Test"

    def test_extracts_links(self):
        parser = _SeoHtmlParser()
        parser.feed('<a href="/page">Link</a>')
        parser.close()
        assert len(parser.links) == 1
        assert parser.links[0]["href"] == "/page"


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

class TestTextHelpers:
    def test_strip_html(self):
        result = _strip_html("<p>Hello <b>World</b></p>")
        assert "Hello" in result and "World" in result

    def test_strip_html_removes_scripts(self):
        result = _strip_html("<script>alert('xss')</script><p>Safe</p>")
        assert "alert" not in result and "Safe" in result

    def test_word_count(self):
        assert _word_count("one two three") == 3
        assert _word_count("") == 0

    def test_count_syllables(self):
        assert _count_syllables("hello") == 2
        assert _count_syllables("world") == 1
        assert _count_syllables("") == 0

    def test_flesch_reading_ease(self):
        score = _flesch_reading_ease("The cat sat on the mat. It was a sunny day.")
        assert 0 <= score <= 100

    def test_flesch_empty(self):
        assert _flesch_reading_ease("") == 0.0


# ---------------------------------------------------------------------------
# Issue + scoring
# ---------------------------------------------------------------------------

class TestIssueAndScoring:
    def test_issue_structure(self):
        issue = _issue("CRITICAL", "Core", "title-missing", "Title missing", "Add title")
        assert issue["severity"] == "CRITICAL"
        assert issue["rule_id"] == "title-missing"

    def test_health_score_no_issues(self):
        assert _compute_health_score([]) == 100

    def test_health_score_critical(self):
        issues = [_issue("CRITICAL", "Core", "test", "msg")]
        assert _compute_health_score(issues) == 92

    def test_health_score_warning(self):
        issues = [_issue("WARNING", "Core", "test", "msg")]
        assert _compute_health_score(issues) == 97

    def test_health_score_info(self):
        issues = [_issue("INFO", "Core", "test", "msg")]
        assert _compute_health_score(issues) == 99

    def test_health_score_floor(self):
        issues = [_issue("CRITICAL", "Core", f"test-{i}", "msg") for i in range(20)]
        assert _compute_health_score(issues) == 0

    def test_health_score_ceiling(self):
        issues = [_issue("INFO", "Core", f"test-{i}", "msg") for i in range(200)]
        assert _compute_health_score(issues) == 0


# ---------------------------------------------------------------------------
# CWV status
# ---------------------------------------------------------------------------

class TestCwvStatus:
    def test_lcp_good(self):
        assert _cwv_status("lcp", 1.5) == "GOOD"

    def test_lcp_poor(self):
        assert _cwv_status("lcp", 5.0) == "POOR"

    def test_lcp_needs_improvement(self):
        assert _cwv_status("lcp", 3.0) == "NEEDS_IMPROVEMENT"

    def test_cls_good(self):
        assert _cwv_status("cls", 0.05) == "GOOD"

    def test_inp_poor(self):
        assert _cwv_status("inp", 600) == "POOR"

    def test_unknown_metric(self):
        assert _cwv_status("unknown", 100) == "UNKNOWN"

    def test_none_value(self):
        assert _cwv_status("lcp", None) == "UNKNOWN"


# ---------------------------------------------------------------------------
# Schema classification
# ---------------------------------------------------------------------------

class TestSchemaClassification:
    def test_active_type(self):
        result = _classify_schema({"@type": "Article", "name": "Test"})
        assert result["status"] == "ACTIVE"
        assert result["type"] == "Article"

    def test_deprecated_type(self):
        result = _classify_schema({"@type": "HowTo"})
        assert result["status"] == "DEPRECATED"

    def test_deprecated_faqpage(self):
        result = _classify_schema({"@type": "FAQPage"})
        assert result["status"] == "DEPRECATED"

    def test_unknown_type(self):
        result = _classify_schema({"@type": "SomethingNew"})
        assert result["status"] == "UNKNOWN"

    def test_list_type(self):
        result = _classify_schema({"@type": ["Article", "NewsArticle"]})
        assert result["type"] == "Article"


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

class TestToolRegistration:
    def test_register_seo_tools(self):
        from unittest.mock import MagicMock

        mcp_mock = MagicMock()
        register_seo_tools(mcp_mock)
        # Should have called mcp.tool() at least 8 times (8 SEO tools)
        assert mcp_mock.tool.call_count >= 8


# ---------------------------------------------------------------------------
# Tool calls with mocked fetch
# ---------------------------------------------------------------------------

_SAMPLE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<title>Test Page - SEO Example</title>
<meta name="description" content="This is a test page for SEO auditing with sufficient length.">
<link rel="canonical" href="https://example.com/test">
<meta property="og:title" content="Test Page">
<meta property="og:description" content="A test page">
<script type="application/ld+json">{"@type":"Article","name":"Test"}</script>
</head>
<body>
<h1>Main Heading</h1>
<h2>What is SEO?</h2>
<p>This is a paragraph with enough words to pass the thin content check. It contains multiple sentences about search engine optimization and how it works in practice for modern websites.</p>
<img src="/image.jpg" alt="Test Image" width="200" height="100">
<a href="/other-page">Other Page</a>
</body>
</html>
"""

_SAMPLE_HTML_BAD = """\
<!DOCTYPE html>
<html>
<head><title>Bad</title></head>
<body>
<h1>One</h1><h1>Two</h1><h1>Three</h1>
<img src="/no-alt.jpg">
<img src="/no-dims.jpg" alt="Has alt">
</body>
</html>
"""


class TestSeoAuditPage:
    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_audit_good_page(self, mock_fetch):
        mock_fetch.return_value = (200, _SAMPLE_HTML, {"Content-Type": "text/html"})
        fn = _get_tool("seo_audit_page")
        result = json.loads(fn(url="https://example.com/test"))
        assert result["ok"] is True
        assert result["status"] == 200
        assert result["h1_count"] == 1
        assert result["json_ld_count"] == 1

    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_audit_bad_page(self, mock_fetch):
        mock_fetch.return_value = (200, _SAMPLE_HTML_BAD, {"Content-Type": "text/html"})
        fn = _get_tool("seo_audit_page")
        result = json.loads(fn(url="https://example.com/bad"))
        assert result["ok"] is True
        assert result["h1_count"] == 3  # multiple H1 = issue
        issue_rules = [i["rule_id"] for i in result["issues"]]
        assert "multiple-h1" in issue_rules

    def test_audit_invalid_url(self):
        fn = _get_tool("seo_audit_page")
        result = json.loads(fn(url="invalid"))
        assert result["ok"] is False


class TestSeoValidateSchema:
    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_validate_active_schema(self, mock_fetch):
        mock_fetch.return_value = (200, _SAMPLE_HTML, {"Content-Type": "text/html"})
        fn = _get_tool("seo_validate_schema")
        result = json.loads(fn(url="https://example.com/test"))
        assert result["ok"] is True
        assert result["schema_count"] == 1
        assert result["active"] == 1
        assert result["deprecated"] == 0


class TestSeoAnalyzeContent:
    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_analyze_content(self, mock_fetch):
        mock_fetch.return_value = (200, _SAMPLE_HTML, {"Content-Type": "text/html"})
        fn = _get_tool("seo_analyze_content")
        result = json.loads(fn(url="https://example.com/test"))
        assert result["ok"] is True
        assert result["word_count"] > 0
        assert "flesch_reading_ease" in result
        assert "citability_score" in result


class TestSeoFindOpportunities:
    def test_striking_distance(self):
        fn = _get_tool("seo_find_opportunities")
        gsc_data = json.dumps({
            "rows": [
                {"query": "test keyword", "page": "https://example.com/page1", "clicks": 5, "impressions": 50, "ctr": 0.10, "position": 8},
                {"query": "low ctr keyword", "page": "https://example.com/page2", "clicks": 1, "impressions": 100, "ctr": 0.01, "position": 2},
            ]
        })
        result = json.loads(fn(gsc_data=gsc_data))
        assert result["ok"] is True
        assert result["striking_distance_count"] >= 1
        assert result["low_ctr_count"] >= 1

    def test_invalid_json(self):
        fn = _get_tool("seo_find_opportunities")
        result = json.loads(fn(gsc_data="not json"))
        assert result["ok"] is False

    def test_empty_rows(self):
        """Empty rows now returns success with empty lists (v5.4.0 fix)."""
        fn = _get_tool("seo_find_opportunities")
        result = json.loads(fn(gsc_data='{"rows": []}'))
        assert result["ok"] is True
        assert result["striking_distance"] == []


class TestSeoGetGscData:
    def test_returns_instructions_without_credentials(self):
        fn = _get_tool("seo_get_gsc_data")
        result = json.loads(fn(site_url="https://example.com"))
        assert result["ok"] is False
        assert "instructions" in result


# ---------------------------------------------------------------------------
# New tests: edge cases + missing tool coverage (v5.4.0 review fixes)
# ---------------------------------------------------------------------------

class TestValidateUrlEdgeCases:
    def test_javascript_scheme_blocked(self):
        result = _validate_url("javascript:alert(1)")
        assert result is not None
        data = json.loads(result)
        assert "not allowed" in data["error"]

    def test_data_scheme_blocked(self):
        result = _validate_url("data:text/html,<h1>test</h1>")
        assert result is not None
        data = json.loads(result)
        assert "not allowed" in data["error"]

    def test_file_scheme_blocked(self):
        result = _validate_url("file:///etc/passwd")
        assert result is not None
        data = json.loads(result)
        assert "not allowed" in data["error"]

    def test_ftp_scheme_blocked(self):
        result = _validate_url("ftp://example.com/file")
        assert result is not None
        data = json.loads(result)
        assert "not allowed" in data["error"]


class TestNormalizeUrl:
    def test_strips_utm_params(self):
        result = _normalize_url("https://example.com/page?utm_source=google&utm_medium=cpc&id=123")
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "id=123" in result

    def test_strips_fbclid(self):
        result = _normalize_url("https://example.com/page?fbclid=abc123&content=x")
        assert "fbclid" not in result
        assert "content=x" in result

    def test_strips_fragment(self):
        result = _normalize_url("https://example.com/page#section")
        assert "#" not in result

    def test_preserves_clean_url(self):
        result = _normalize_url("https://example.com/page")
        assert result == "https://example.com/page"


class TestStripHtmlEdgeCases:
    def test_cdata_removed(self):
        result = _strip_html("<![CDATA[<p>hidden</p>]]><p>visible</p>")
        assert "hidden" not in result
        assert "visible" in result

    def test_html_comments_removed(self):
        result = _strip_html("<!-- comment --><p>visible</p>")
        assert "comment" not in result
        assert "visible" in result

    def test_conditional_comments_removed(self):
        result = _strip_html("<!--[if IE]><p>ie only</p><![endif]--><p>visible</p>")
        assert "ie only" not in result
        assert "visible" in result


class TestCountSyllablesEdgeCases:
    def test_numbers_return_zero(self):
        assert _count_syllables("123") == 0

    def test_symbols_return_zero(self):
        assert _count_syllables("!!!") == 0

    def test_empty_returns_zero(self):
        assert _count_syllables("") == 0

    def test_alpha_returns_positive(self):
        assert _count_syllables("hello") >= 1


class TestParseHtmlMalformed:
    def test_malformed_html_no_crash(self):
        # Unclosed tags should not crash
        parser = _parse_html("<html><head><title>Test</title><body><h1>Hi")
        assert parser.title == "Test"
        assert len(parser.h1s) == 1

    def test_empty_body(self):
        parser = _parse_html("")
        assert parser.title == ""

    def test_nested_divs(self):
        parser = _parse_html("<div><div><h1>Deep</h1></div></div>")
        assert len(parser.h1s) == 1


class TestSeoHtmlParserAnchorText:
    def test_captures_anchor_text(self):
        parser = _SeoHtmlParser()
        parser.feed('<a href="/page">Click here</a>')
        parser.close()
        assert len(parser.links) == 1
        assert parser.links[0]["text"] == "Click here"
        assert parser.links[0]["href"] == "/page"

    def test_captures_multiline_anchor_text(self):
        parser = _SeoHtmlParser()
        parser.feed("<a href=\"/page\">Click\n  here</a>")
        parser.close()
        assert len(parser.links) == 1
        assert "Click" in parser.links[0]["text"]

    def test_empty_anchor_text(self):
        parser = _SeoHtmlParser()
        parser.feed('<a href="/page"></a>')
        parser.close()
        assert len(parser.links) == 1
        assert parser.links[0]["text"] == ""


class TestSeoHtmlParserTagReset:
    def test_current_tag_reset_after_h1(self):
        parser = _SeoHtmlParser()
        parser.feed("<h1>Title</h1>Some text after")
        parser.close()
        # "Some text after" should NOT be added to h1s
        assert len(parser.h1s) == 1
        assert parser.h1s[0] == "Title"


class TestClassifySchemaGraph:
    def test_graph_container(self):
        item = {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "Organization", "name": "Example"},
                {"@type": "WebSite", "name": "Example.com"},
            ],
        }
        result = _classify_schema(item)
        assert result["status"] == "CONTAINER"
        assert result["type"] == "@graph"
        assert result["count"] == 2

    def test_graph_single_item(self):
        item = {"@graph": [{"@type": "Article"}]}
        result = _classify_schema(item)
        assert result["status"] == "CONTAINER"


class TestSeoAuditSite:
    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_site_crawl_basic(self, mock_fetch):
        # First call returns page with link, second returns linked page
        page1 = '<html><head><title>Page 1</title></head><body><h1>Home</h1><a href="/page2">Page 2</a></body></html>'
        page2 = '<html><head><title>Page 2</title></head><body><h1>About</h1></body></html>'
        mock_fetch.side_effect = [
            (200, page1, {"Content-Type": "text/html"}),
            (200, page2, {"Content-Type": "text/html"}),
            (200, page2, {"Content-Type": "text/html"}),  # robots/llms not fetched here
        ]
        fn = _get_tool("seo_audit_site")
        result = json.loads(fn(start_url="https://example.com", max_pages=5))
        assert result["ok"] is True
        assert result["pages_crawled"] >= 1

    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_site_crawl_max_pages(self, mock_fetch):
        # Return same page repeatedly to test max_pages limit
        page = '<html><head><title>Loop</title></head><body><h1>Loop</h1><a href="/page1">P1</a></body></html>'
        mock_fetch.return_value = (200, page, {"Content-Type": "text/html"})
        fn = _get_tool("seo_audit_site")
        result = json.loads(fn(start_url="https://example.com", max_pages=3))
        assert result["ok"] is True
        assert result["pages_crawled"] <= 3

    def test_site_crawl_invalid_url(self):
        fn = _get_tool("seo_audit_site")
        result = json.loads(fn(start_url="invalid"))
        assert result["ok"] is False


class TestSeoCheckCwv:
    @patch("aizee_mcp.tools.seo_tools.urllib.request.urlopen")
    def test_cwv_success(self, mock_urlopen):
        # Mock PageSpeed API response
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({
            "lighthouseResult": {
                "audits": {
                    "largest-contentful-paint": {"numericValue": 2500},
                    "cumulative-layout-shift": {"numericValue": 0.05},
                    "first-contentful-paint": {"numericValue": 1800},
                    "server-response-time": {"numericValue": 600},
                }
            },
            "loadingExperience": {
                "metrics": {
                    "INTERACTION_TO_NEXT_PAINT": {"percentile": 150}
                }
            }
        }).encode()
        mock_urlopen.return_value = mock_resp
        fn = _get_tool("seo_check_cwv")
        result = json.loads(fn(url="https://example.com", strategy="mobile"))
        assert result["ok"] is True
        assert "lcp" in result["metrics"]
        assert "inp" in result["metrics"]

    def test_cwv_invalid_strategy(self):
        fn = _get_tool("seo_check_cwv")
        result = json.loads(fn(url="https://example.com", strategy="tablet"))
        assert result["ok"] is False

    def test_cwv_invalid_url(self):
        fn = _get_tool("seo_check_cwv")
        result = json.loads(fn(url="invalid", strategy="mobile"))
        assert result["ok"] is False


class TestSeoCheckGeo:
    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_geo_basic(self, mock_fetch):
        page = '<html><head><title>Test</title></head><body><article><h1>Test</h1></article></body></html>'
        robots = "User-agent: *\nAllow: /"
        # Page fetch, robots.txt fetch, llms.txt fetch
        mock_fetch.side_effect = [
            (200, page, {"Content-Type": "text/html"}),
            (200, robots, {"Content-Type": "text/plain"}),
            (None, "", {}),  # llms.txt not found
        ]
        fn = _get_tool("seo_check_geo")
        result = json.loads(fn(url="https://example.com"))
        assert result["ok"] is True
        assert "geo_score" in result
        assert "ai_crawler_access" in result
        assert result["has_semantic_html"] is True

    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_geo_blocked_crawler(self, mock_fetch):
        page = '<html><head><title>Test</title></head><body></body></html>'
        robots = "User-agent: GPTBot\nDisallow: /\n"
        mock_fetch.side_effect = [
            (200, page, {"Content-Type": "text/html"}),
            (200, robots, {"Content-Type": "text/plain"}),
            (None, "", {}),
        ]
        fn = _get_tool("seo_check_geo")
        result = json.loads(fn(url="https://example.com"))
        assert result["ok"] is True
        assert result["ai_crawler_access"]["GPTBot"] is False

    def test_geo_invalid_url(self):
        fn = _get_tool("seo_check_geo")
        result = json.loads(fn(url="invalid"))
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# v5.4.0 review round 2: SSRF + syllables + position=0 + nested tags
# ---------------------------------------------------------------------------

class TestSsrfProtection:
    def test_localhost_blocked(self):
        result = _validate_url("http://localhost/admin")
        assert result is not None
        data = json.loads(result)
        assert "Private" in data["error"] or "private" in data["error"]

    def test_loopback_ip_blocked(self):
        result = _validate_url("http://127.0.0.1/admin")
        assert result is not None

    def test_aws_metadata_blocked(self):
        result = _validate_url("http://169.254.169.254/latest/meta-data/")
        assert result is not None

    def test_private_ip_10_blocked(self):
        result = _validate_url("http://10.0.0.1/internal")
        assert result is not None

    def test_private_ip_172_blocked(self):
        result = _validate_url("http://172.16.0.1/internal")
        assert result is not None

    def test_private_ip_192_blocked(self):
        result = _validate_url("http://192.168.1.1/admin")
        assert result is not None

    def test_public_ip_allowed(self):
        result = _validate_url("https://example.com/page")
        assert result is None

    def test_ipv6_loopback_blocked(self):
        result = _validate_url("http://[::1]/admin")
        assert result is not None


class TestCountSyllablesVowels:
    def test_fly_returns_one(self):
        assert _count_syllables("fly") == 1

    def test_my_returns_one(self):
        assert _count_syllables("my") == 1

    def test_crypt_returns_one(self):
        assert _count_syllables("crypt") == 1

    def test_the_returns_one(self):
        assert _count_syllables("the") == 1

    def test_hello_returns_positive(self):
        assert _count_syllables("hello") >= 1


class TestSeoFindOpportunitiesPositionZero:
    def test_position_zero_skipped_in_low_ctr(self):
        fn = _get_tool("seo_find_opportunities")
        gsc_data = json.dumps({
            "rows": [
                {"query": "test", "page": "https://example.com", "clicks": 0, "impressions": 100, "ctr": 0.001, "position": 0},
            ]
        })
        result = json.loads(fn(gsc_data=gsc_data))
        assert result["ok"] is True
        # position=0 should not appear in low_ctr (it's invalid/missing data)
        assert result["low_ctr_count"] == 0

    def test_negative_position_skipped(self):
        fn = _get_tool("seo_find_opportunities")
        gsc_data = json.dumps({
            "rows": [
                {"query": "test", "page": "https://example.com", "clicks": 0, "impressions": 100, "ctr": 0.001, "position": -1},
            ]
        })
        result = json.loads(fn(gsc_data=gsc_data))
        assert result["ok"] is True
        assert result["low_ctr_count"] == 0


class TestNestedTagHandling:
    def test_nested_divs_no_data_leakage(self):
        parser = _parse_html("<div><div><h1>Inner</h1></div></div>Some text")
        assert len(parser.h1s) == 1
        assert parser.h1s[0] == "Inner"

    def test_nested_h1_only_inner_captured(self):
        # Nested h1 is invalid HTML but should not crash
        parser = _parse_html("<h1>Outer<h1>Inner</h1></h1>")
        assert len(parser.h1s) >= 1

    def test_div_then_h1_after_close(self):
        parser = _parse_html("<div>text</div><h1>After</h1>")
        assert len(parser.h1s) == 1
        assert parser.h1s[0] == "After"

    def test_self_closing_img_not_on_stack(self):
        parser = _parse_html("<img src='x' alt='y'/><h1>After img</h1>")
        assert len(parser.h1s) == 1
        assert parser.h1s[0] == "After img"


# ---------------------------------------------------------------------------
# v5.4.0 review round 3: SSRF edge cases + logic fixes + missing tests
# ---------------------------------------------------------------------------

class TestSsrfEdgeCases:
    def test_unspecified_ip_blocked(self):
        """0.0.0.0 should be blocked (unspecified address)."""
        result = _validate_url("http://0.0.0.0/")
        assert result is not None

    def test_is_private_ip_unspecified(self):
        assert _is_private_ip("0.0.0.0") is True

    def test_is_private_ip_ipv6_brackets(self):
        """IPv6 with brackets should be handled."""
        assert _is_private_ip("[::1]") is True

    def test_is_private_ip_empty(self):
        assert _is_private_ip("") is False

    def test_is_private_ip_public_domain(self):
        """Public domains should not be flagged as private (no DNS rebinding false positive)."""
        # example.com resolves to public IP — should return False
        assert _is_private_ip("example.com") is False


class TestSeoCheckCwvEmptyLighthouse:
    @patch("aizee_mcp.tools.seo_tools.urllib.request.urlopen")
    def test_cwv_missing_lighthouse_result(self, mock_urlopen):
        """PSI API returning error JSON (no lighthouseResult) should return error."""
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({"error": {"code": 400, "message": "Invalid URL"}}).encode()
        mock_resp.status = 200
        mock_urlopen.return_value = mock_resp
        fn = _get_tool("seo_check_cwv")
        result = json.loads(fn(url="https://example.com", strategy="mobile"))
        assert result["ok"] is False
        assert "lighthouseResult" in result["error"]


class TestSeoCheckGeoEmptyBody:
    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_geo_empty_body_returns_error(self, mock_fetch):
        """Empty body (status 200 but no content) should return error."""
        mock_fetch.return_value = (200, "", {"Content-Type": "text/html"})
        fn = _get_tool("seo_check_geo")
        result = json.loads(fn(url="https://example.com"))
        assert result["ok"] is False


class TestSeoFindOpportunitiesEmptyRows:
    def test_empty_rows_returns_success(self):
        """Empty rows (no GSC data) should return success with empty lists, not error."""
        fn = _get_tool("seo_find_opportunities")
        result = json.loads(fn(gsc_data='{"rows": []}'))
        assert result["ok"] is True
        assert result["striking_distance"] == []
        assert result["low_ctr"] == []
        assert result["cannibalization"] == []

    def test_missing_rows_key_returns_success(self):
        """Missing rows key should return success with empty lists."""
        fn = _get_tool("seo_find_opportunities")
        result = json.loads(fn(gsc_data='{}'))
        assert result["ok"] is True

    def test_non_list_rows_returns_error(self):
        """Non-list rows value should return error."""
        fn = _get_tool("seo_find_opportunities")
        result = json.loads(fn(gsc_data='{"rows": "not a list"}'))
        assert result["ok"] is False


class TestClassifySchemaEmptyGraph:
    def test_empty_graph_array(self):
        """Empty @graph array should return EMPTY status, not CONTAINER."""
        item = {"@graph": []}
        result = _classify_schema(item)
        assert result["status"] == "EMPTY"
        assert result["count"] == 0


class TestContentHash:
    def test_same_input_same_hash(self):
        """Same input should produce same hash."""
        h1 = _content_hash("test content")
        h2 = _content_hash("test content")
        assert h1 == h2

    def test_different_input_different_hash(self):
        """Different input should produce different hash."""
        h1 = _content_hash("test content 1")
        h2 = _content_hash("test content 2")
        assert h1 != h2

    def test_hash_length(self):
        """Hash should be 16 characters (truncated SHA256)."""
        h = _content_hash("test")
        assert len(h) == 16

    def test_empty_input(self):
        """Empty input should not crash."""
        h = _content_hash("")
        assert len(h) == 16


class TestSeoValidateSchemaEdgeCases:
    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_invalid_json_ld(self, mock_fetch):
        """Invalid JSON in JSON-LD script should return INVALID_JSON status."""
        html = '<html><head><script type="application/ld+json">{invalid json}</script></head></html>'
        mock_fetch.return_value = (200, html, {"Content-Type": "text/html"})
        fn = _get_tool("seo_validate_schema")
        result = json.loads(fn(url="https://example.com"))
        assert result["ok"] is True
        assert any(s["status"] == "ERROR" or s["type"] == "INVALID_JSON" for s in result["schemas"])

    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_multiple_schemas_in_one_script(self, mock_fetch):
        """JSON-LD as array (multiple schemas in one script) should be parsed."""
        html = '<html><head><script type="application/ld+json">[{"@type":"Article"},{"@type":"Product"}]</script></head></html>'
        mock_fetch.return_value = (200, html, {"Content-Type": "text/html"})
        fn = _get_tool("seo_validate_schema")
        result = json.loads(fn(url="https://example.com"))
        assert result["ok"] is True
        assert result["schema_count"] == 2

    def test_invalid_url(self):
        fn = _get_tool("seo_validate_schema")
        result = json.loads(fn(url="invalid"))
        assert result["ok"] is False


class TestSeoAnalyzeContentEdgeCases:
    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_thin_content(self, mock_fetch):
        """Page with < 300 words should flag thin-content issue."""
        html = '<html><head><title>Thin</title></head><body><h1>Short</h1><p>Very short page.</p></body></html>'
        mock_fetch.return_value = (200, html, {"Content-Type": "text/html"})
        fn = _get_tool("seo_analyze_content")
        result = json.loads(fn(url="https://example.com"))
        assert result["ok"] is True
        assert result["word_count"] < 300
        assert any(i["rule_id"] == "thin-content" for i in result["issues"])

    def test_invalid_url(self):
        fn = _get_tool("seo_analyze_content")
        result = json.loads(fn(url="invalid"))
        assert result["ok"] is False


class TestSeoGetGscDataEdgeCases:
    def test_invalid_url(self):
        fn = _get_tool("seo_get_gsc_data")
        result = json.loads(fn(site_url="invalid"))
        assert result["ok"] is False

    def test_days_clamped(self):
        """Days should be clamped to [1, 90]."""
        fn = _get_tool("seo_get_gsc_data")
        result = json.loads(fn(site_url="https://example.com", days=0))
        # days=0 gets clamped to 1
        assert result["days"] == 1
        result2 = json.loads(fn(site_url="https://example.com", days=100))
        assert result2["days"] == 90


# ---------------------------------------------------------------------------
# v5.4.0 review round 4: paragraph splitting + nofollow + viewport + @graph dict + cannibalization
# ---------------------------------------------------------------------------

class TestSeoAnalyzeContentParagraphs:
    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_paragraphs_split_by_sentences(self, mock_fetch):
        """Paragraphs should be split by sentence boundaries (not newlines, which _strip_html collapses)."""
        html = '<html><head><title>Test</title></head><body><p>First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence. Seventh sentence. Eighth sentence. Ninth sentence.</p></body></html>'
        mock_fetch.return_value = (200, html, {"Content-Type": "text/html"})
        fn = _get_tool("seo_analyze_content")
        result = json.loads(fn(url="https://example.com"))
        assert result["ok"] is True
        # With 9 sentences grouped by 3, should have 3 paragraphs
        assert result["total_paragraphs"] >= 2


class TestSeoAuditPageNofollowViewport:
    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_nofollow_detected(self, mock_fetch):
        """Page with nofollow directive should flag it."""
        html = '<html><head><title>Test</title><meta name="robots" content="nofollow"></head><body><h1>Test</h1></body></html>'
        mock_fetch.return_value = (200, html, {"Content-Type": "text/html"})
        fn = _get_tool("seo_audit_page")
        result = json.loads(fn(url="https://example.com"))
        assert result["ok"] is True
        assert any(i["rule_id"] == "nofollow" for i in result["issues"])

    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_viewport_missing_detected(self, mock_fetch):
        """Page without viewport meta should flag it."""
        html = '<html><head><title>Test</title></head><body><h1>Test</h1></body></html>'
        mock_fetch.return_value = (200, html, {"Content-Type": "text/html"})
        fn = _get_tool("seo_audit_page")
        result = json.loads(fn(url="https://example.com"))
        assert result["ok"] is True
        assert any(i["rule_id"] == "viewport-missing" for i in result["issues"])

    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_viewport_present_no_issue(self, mock_fetch):
        """Page with viewport meta should NOT flag viewport-missing."""
        html = '<html><head><title>Test</title><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><h1>Test</h1></body></html>'
        mock_fetch.return_value = (200, html, {"Content-Type": "text/html"})
        fn = _get_tool("seo_audit_page")
        result = json.loads(fn(url="https://example.com"))
        assert result["ok"] is True
        assert not any(i["rule_id"] == "viewport-missing" for i in result["issues"])


class TestClassifySchemaGraphDict:
    def test_graph_as_dict_recurses(self):
        """@graph as a single dict (not list) should recurse and classify the inner item."""
        item = {"@graph": {"@type": "Article", "name": "Test"}}
        result = _classify_schema(item)
        assert result["type"] == "Article"
        assert result["status"] == "ACTIVE"


class TestSeoFindOpportunitiesCannibalization:
    def test_cannibalization_deduplicates_pages(self):
        """Same query+page multiple times should NOT trigger false cannibalization."""
        fn = _get_tool("seo_find_opportunities")
        gsc = json.dumps({"rows": [
            {"query": "test", "page": "https://example.com/a", "clicks": 10, "impressions": 100, "ctr": 0.1, "position": 5},
            {"query": "test", "page": "https://example.com/a", "clicks": 5, "impressions": 50, "ctr": 0.1, "position": 5},
        ]})
        result = json.loads(fn(gsc_data=gsc))
        assert result["ok"] is True
        assert result["cannibalization_count"] == 0  # same page, not cannibalization

    def test_cannibalization_detects_different_pages(self):
        """Same query, different pages should trigger cannibalization."""
        fn = _get_tool("seo_find_opportunities")
        gsc = json.dumps({"rows": [
            {"query": "test", "page": "https://example.com/a", "clicks": 10, "impressions": 100, "ctr": 0.1, "position": 5},
            {"query": "test", "page": "https://example.com/b", "clicks": 5, "impressions": 50, "ctr": 0.1, "position": 7},
        ]})
        result = json.loads(fn(gsc_data=gsc))
        assert result["ok"] is True
        assert result["cannibalization_count"] == 1


class TestSeoAuditSiteLinkFiltering:
    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_tel_links_filtered(self, mock_fetch):
        """tel: links should be filtered out during crawl."""
        html = '<html><body><a href="tel:+1234567890">Call</a><a href="/page2">Page 2</a></body></html>'
        mock_fetch.side_effect = [
            (200, html, {"Content-Type": "text/html"}),
            (200, "<html><body><h1>Page 2</h1></body></html>", {"Content-Type": "text/html"}),
        ]
        fn = _get_tool("seo_audit_site")
        result = json.loads(fn(start_url="https://example.com", max_pages=5))
        assert result["ok"] is True
        # Should crawl 2 pages (main + page2), tel: link should not cause errors

    @patch("aizee_mcp.tools.seo_tools._fetch")
    def test_mailto_uppercase_filtered(self, mock_fetch):
        """MAILTO: (uppercase) should be filtered out during crawl."""
        html = '<html><body><a href="MAILTO:test@example.com">Email</a><a href="/page2">Page 2</a></body></html>'
        mock_fetch.side_effect = [
            (200, html, {"Content-Type": "text/html"}),
            (200, "<html><body><h1>Page 2</h1></body></html>", {"Content-Type": "text/html"}),
        ]
        fn = _get_tool("seo_audit_site")
        result = json.loads(fn(start_url="https://example.com", max_pages=5))
        assert result["ok"] is True
