"""Gap coverage batch 4 for aizee_mcp/tools/seo_tools.py."""

from __future__ import annotations

import json
import urllib.error
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import aizee_mcp.tools.seo_tools as seo

pytestmark = [pytest.mark.slow, pytest.mark.mcp]


class _FakeTool:
    def __call__(self, fn: Any | None = None) -> Any:
        if fn is not None:
            _captured[fn.__name__] = fn
            return fn

        def decorator(inner: Any) -> Any:
            _captured[inner.__name__] = inner
            return inner

        return decorator


class _FakeMCP:
    def __init__(self) -> None:
        self.tool = _FakeTool()


_captured: dict[str, Any] = {}
seo.register_seo_tools(_FakeMCP())


def _call(name: str, *args: Any, **kwargs: Any) -> Any:
    return _captured[name](*args, **kwargs)


def _fake_fetch(status: int | None = 200, body: str = "", headers: dict | None = None):
    return patch.object(seo, "_fetch", return_value=(status, body, headers or {}))


# ---------------------------------------------------------------------------
# _fetch charset branch (247->249)
# ---------------------------------------------------------------------------


class TestFetchCharset:
    def test_content_type_without_charset_defaults_utf8(self):
        resp = MagicMock()
        resp.status = 200
        resp.headers = {"Content-Type": "text/html"}  # no charset param
        resp.read.return_value = b"<html>hi</html>"
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value = resp
        with patch.object(seo, "_get_opener", return_value=opener):
            status, body, _ = seo._fetch("https://example.com")
        assert status == 200
        assert "hi" in body


# ---------------------------------------------------------------------------
# Parser branches
# ---------------------------------------------------------------------------


class TestParserGaps:
    def test_whitespace_only_heading_data(self):
        parser = seo._parse_html("<h1>   </h1><p>x</p>")
        assert parser.h1s == []

    def test_h3_data(self):
        parser = seo._parse_html("<h3>Sub head</h3>")
        assert parser.h3s == ["Sub head"]

    def test_selfclosing_link_and_other_tag(self):
        parser = seo._parse_html(
            '<link rel="canonical" href="https://x.com/p"/><br/>'
        )
        assert parser.canonical == "https://x.com/p"

    def test_parse_html_feed_error_returns_partial(self):
        with patch.object(seo._SeoHtmlParser, "feed", side_effect=RuntimeError("bad")):
            parser = seo._parse_html("<p>x</p>")
        assert isinstance(parser, seo._SeoHtmlParser)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_count_syllables_non_alpha(self):
        assert seo._count_syllables("123") == 0
        assert seo._count_syllables("") == 0

    def test_count_syllables_trailing_e(self):
        assert seo._count_syllables("table") >= 1

    def test_count_syllables_no_vowels(self):
        assert seo._count_syllables("crypt") == 1

    def test_content_hash(self):
        assert len(seo._content_hash("hello")) == 16

    def test_issue_shape(self):
        i = seo._issue("WARNING", "Core", "rid", "msg", "fix")
        assert i["severity"] == "WARNING" and i["rule_id"] == "rid"

    def test_health_score_unknown_severity(self):
        score = seo._compute_health_score([{"severity": "BOGUS"}])
        assert score == 99  # unknown severity applies -1 default

    def test_cwv_status_variants(self):
        assert seo._cwv_status("lcp", None) == "UNKNOWN"
        assert seo._cwv_status("nonexistent-metric", 1.0) == "UNKNOWN"
        assert seo._cwv_status("lcp", 1.0) == "GOOD"
        assert seo._cwv_status("lcp", 9.0) == "POOR"
        assert seo._cwv_status("lcp", 3.0) == "NEEDS_IMPROVEMENT"


# ---------------------------------------------------------------------------
# _parser_to_page_data + _audit_page_issues
# ---------------------------------------------------------------------------


class TestAuditPageIssues:
    def test_audit_page_issues_legacy_checks(self):
        body = (
            '<html><head><meta name="robots" content="nofollow">'
            "</head><body><h1>t</h1></body></html>"
        )
        parser = seo._parse_html(body)
        issues = seo._audit_page_issues(parser, body, "https://x.com")
        ids = {i["rule_id"] for i in issues}
        assert "og-title-missing" in ids
        assert "viewport-missing" in ids
        assert "nofollow" in ids

    def test_parser_to_page_data_fields(self):
        body = '<html><body><img src="a.png"><h1>T</h1></body></html>'
        parser = seo._parse_html(body)
        pd = seo._parser_to_page_data(parser, body, "https://x.com", 200)
        assert pd.images_missing_alt == 1
        assert pd.images_missing_dims == 1


# ---------------------------------------------------------------------------
# seo_audit_page branches
# ---------------------------------------------------------------------------


class TestSeoAuditPage:
    def test_fetch_failure(self):
        with _fake_fetch(None):
            out = json.loads(_call("seo_audit_page", "https://example.com"))
        assert out["ok"] is False

    def test_empty_body(self):
        with _fake_fetch(404, ""):
            out = json.loads(_call("seo_audit_page", "https://example.com"))
        assert out["ok"] is False
        assert "No HTML" in out["error"]

    def test_success(self):
        html = (
            '<html><head><title>T</title>'
            '<meta name="description" content="d">'
            '<meta property="og:title" content="o">'
            '<meta name="viewport" content="w">'
            '<script type="application/ld+json">{"@type":"Article"}</script>'
            "</head><body><h1>H</h1><h2>What?</h2>"
            '<a href="/p">L</a><img src="i.png" alt="a" width="1" height="1">'
            "</body></html>"
        )
        with _fake_fetch(200, html):
            out = json.loads(_call("seo_audit_page", "https://example.com"))
        assert out["ok"] is True
        assert out["json_ld_count"] == 1
        assert out["image_count"] == 1


# ---------------------------------------------------------------------------
# seo_audit_site
# ---------------------------------------------------------------------------


class TestSeoAuditSite:
    _PAGE = (
        '<html><head><title>T</title></head><body>'
        '<a href="/a">A</a><a href="https://other.com/x">X</a>'
        '<a href="#frag">F</a><a href="mailto:a@b.c">M</a>'
        '<a href="javascript:v">J</a><a href="tel:1">T</a><a href="">E</a>'
        '<a href="/">self</a>'
        "</body></html>"
    )

    def test_invalid_start_url(self):
        out = _call("seo_audit_site", "notaurl")
        assert "error" in out or '"ok": false' in out

    def test_bad_max_pages_defaults(self):
        with _fake_fetch(200, "<html></html>"):
            out = json.loads(_call("seo_audit_site", "https://example.com", max_pages="junk"))
        assert out["ok"] is True

    def test_crawl_dedup_and_link_filters(self):
        def fetch(url: str):
            if url == "https://example.com/":
                return 200, self._PAGE, {}
            return 200, "<html><body><h1>x</h1></body></html>", {}

        with patch.object(seo, "_fetch", side_effect=fetch):
            out = json.loads(
                _call("seo_audit_site", "https://example.com/", max_pages=10)
            )
        assert out["ok"] is True
        assert out["pages_crawled"] >= 2  # / and /a

    def test_fetch_exception_skips_page(self):
        def fetch(url: str):
            if url.endswith("/bad"):
                raise RuntimeError("net down")
            return 200, '<html><body><a href="/bad">b</a></body></html>', {}

        with patch.object(seo, "_fetch", side_effect=fetch):
            out = json.loads(
                _call("seo_audit_site", "https://example.com", max_pages=5)
            )
        assert out["ok"] is True
        assert out["pages_skipped"] >= 1

    def test_fetch_none_status_skips(self):
        with _fake_fetch(None):
            out = json.loads(
                _call("seo_audit_site", "https://example.com", max_pages=5)
            )
        assert out["pages_crawled"] == 1  # visited incremented, page skipped

    def test_parse_error_skips_page(self):
        with _fake_fetch(200, "<html>x</html>"), \
             patch.object(seo, "_parse_html", side_effect=ValueError("bad html")):
            out = json.loads(
                _call("seo_audit_site", "https://example.com", max_pages=3)
            )
        assert out["pages_skipped"] == 1

    def test_deadline_breaks_crawl(self):
        # monotonic: deadline setup -> 0, loop check -> far future -> break
        calls = iter([0.0, 1e9])
        page = '<html><body><a href="/x">x</a></body></html>'
        with patch.object(seo, "_fetch", return_value=(200, page, {})), \
             patch("time.monotonic", side_effect=lambda: next(calls, 1e9)):
            out = json.loads(
                _call("seo_audit_site", "https://example.com", max_pages=10)
            )
        assert out["pages_crawled"] == 0

    def test_memory_guard_aborts(self):
        baseline = MagicMock()
        baseline.memory_info.return_value.rss = 100
        grown = MagicMock()
        grown.memory_info.return_value.rss = 100 + seo._MAX_CRAWL_RSS_BYTES + 1
        page = '<html><body><a href="/x">x</a></body></html>'
        with patch.object(seo, "_fetch", return_value=(200, page, {})), \
             patch("psutil.Process", side_effect=[baseline, grown]):
            out = json.loads(
                _call("seo_audit_site", "https://example.com", max_pages=10)
            )
        assert out["ok"] is False
        assert "memory limit" in out["error"]

    def test_psutil_missing_skips_guards(self):
        page = "<html><body><h1>x</h1></body></html>"
        with patch.object(seo, "_fetch", return_value=(200, page, {})), \
             patch.dict("sys.modules", {"psutil": None}):
            out = json.loads(
                _call("seo_audit_site", "https://example.com", max_pages=3)
            )
        assert out["ok"] is True


# ---------------------------------------------------------------------------
# seo_check_cwv
# ---------------------------------------------------------------------------


def _urlopen_json(payload: dict[str, Any]):
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    ctx = MagicMock()
    ctx.__enter__.return_value = resp
    return ctx


class TestSeoCheckCwv:
    def test_invalid_strategy(self):
        out = json.loads(_call("seo_check_cwv", "https://example.com", "wrist"))
        assert out["ok"] is False

    def test_urlopen_failure(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("x")):
            out = json.loads(_call("seo_check_cwv", "https://example.com"))
        assert out["ok"] is False

    def test_no_lighthouse_result(self):
        with patch("urllib.request.urlopen", return_value=_urlopen_json({})):
            out = json.loads(_call("seo_check_cwv", "https://example.com"))
        assert out["ok"] is False
        assert "lighthouseResult" in out["error"]

    def test_full_metrics(self):
        payload = {
            "lighthouseResult": {
                "audits": {
                    "largest-contentful-paint": {"numericValue": 2000},
                    "cumulative-layout-shift": {"numericValue": 0.05},
                    "first-contentful-paint": {"numericValue": 1500},
                    "server-response-time": {"numericValue": 400},
                }
            },
            "loadingExperience": {
                "metrics": {"INTERACTION_TO_NEXT_PAINT": {"percentile": 150}}
            },
        }
        with patch("urllib.request.urlopen", return_value=_urlopen_json(payload)):
            out = json.loads(_call("seo_check_cwv", "https://example.com"))
        assert out["ok"] is True
        assert out["metrics"]["lcp"]["value"] == 2.0
        assert out["metrics"]["ttfb"]["value"] == 400
        assert out["metrics"]["inp"]["value"] == 150
        assert out["all_good"] is True

    def test_missing_audits_and_no_inp(self):
        payload = {"lighthouseResult": {"audits": {}}}
        with patch("urllib.request.urlopen", return_value=_urlopen_json(payload)):
            out = json.loads(_call("seo_check_cwv", "https://example.com"))
        assert out["metrics"]["lcp"]["value"] is None
        assert out["metrics"]["inp"]["value"] is None
        assert out["all_good"] is False


# ---------------------------------------------------------------------------
# seo_validate_schema + _classify_schema
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    def test_validate_schema_variants(self):
        html = (
            '<html><head>'
            '<script type="application/ld+json">{"@type":"Article"}</script>'
            '<script type="application/ld+json">[{"@type":"FAQPage"},{"@type":"Weird"}]</script>'
            '<script type="application/ld+json">{invalid json</script>'
            '<script type="application/ld+json">{"@graph":[]}</script>'
            '<script type="application/ld+json">{"@graph":[{"@type":"Person"}]}</script>'
            '<script type="application/ld+json">{"@graph":{"@type":"Course"}}</script>'
            '<script type="application/ld+json">{"@type":["Article","X"]}</script>'
            '<script type="application/ld+json">{"@type":[]}</script>'
            "</head></html>"
        )
        with _fake_fetch(200, html):
            out = json.loads(_call("seo_validate_schema", "https://example.com"))
        assert out["ok"] is True
        statuses = [s["status"] for s in out["schemas"]]
        assert "ACTIVE" in statuses
        assert "DEPRECATED" in statuses
        assert "UNKNOWN" in statuses
        assert "ERROR" in statuses
        assert "EMPTY" in statuses
        assert "CONTAINER" in statuses
        assert out["active"] >= 3

    def test_validate_schema_fetch_fail(self):
        with _fake_fetch(None):
            out = json.loads(_call("seo_validate_schema", "https://example.com"))
        assert out["ok"] is False

    def test_classify_schema_non_dict(self):
        out = seo._classify_schema("just a string")
        assert out["status"] == "UNKNOWN"
        assert out["type"] == ""


# ---------------------------------------------------------------------------
# seo_analyze_content
# ---------------------------------------------------------------------------


class TestAnalyzeContent:
    def test_thin_content_no_signals(self):
        html = "<html><body><p>short text</p></body></html>"
        with _fake_fetch(200, html):
            out = json.loads(_call("seo_analyze_content", "https://example.com"))
        assert out["ok"] is True
        ids = {i["rule_id"] for i in out["issues"]}
        assert "thin-content" in ids
        assert "no-author" in ids
        assert "no-date" in ids

    def test_rich_content(self):
        words = " ".join(["The quick brown fox jumps over lazy dogs."] * 60)
        html = (
            '<html><head>'
            '<meta name="author" content="A">'
            '<meta property="article:published_time" content="2024-01-01">'
            "</head><body>"
            "<h2>What is it?</h2>"
            f"<p>{words}</p>"
            "</body></html>"
        )
        with _fake_fetch(200, html):
            out = json.loads(_call("seo_analyze_content", "https://example.com"))
        assert out["question_headings"] == 1
        assert out["has_author_signal"] is True
        assert out["has_date_signal"] is True
        assert out["word_count"] >= 300

    def test_fetch_fail(self):
        with _fake_fetch(None):
            out = json.loads(_call("seo_analyze_content", "https://example.com"))
        assert out["ok"] is False


# ---------------------------------------------------------------------------
# seo_check_geo
# ---------------------------------------------------------------------------


class TestCheckGeo:
    def _fetch_map(self, url: str):
        if url.endswith("/robots.txt"):
            return 200, "User-agent: GPTBot\nDisallow: /\n", {}
        if url.endswith("/llms.txt"):
            return 200, "# llms\n", {}
        return (
            200,
            '<html><body><article><h1>T</h1></article>'
            '<script type="application/ld+json">{"@type":"Article"}</script>'
            "</body></html>",
            {},
        )

    def test_geo_full(self):
        with patch.object(seo, "_fetch", side_effect=self._fetch_map):
            out = json.loads(_call("seo_check_geo", "https://example.com"))
        assert out["ok"] is True
        assert out["ai_crawler_access"]["GPTBot"] is False
        assert out["has_llms_txt"] is True
        assert out["has_semantic_html"] is True
        assert out["has_schema"] is True

    def test_geo_no_robots_no_llms(self):
        def fetch(url: str):
            if url.endswith(("/robots.txt", "/llms.txt")):
                return None, "", {}
            return 200, "<html><body><p>x</p></body></html>", {}

        with patch.object(seo, "_fetch", side_effect=fetch):
            out = json.loads(_call("seo_check_geo", "https://example.com"))
        assert out["has_llms_txt"] is False
        assert all(out["ai_crawler_access"].values())
        assert out["has_semantic_html"] is False

    def test_fetch_fail(self):
        with _fake_fetch(None):
            out = json.loads(_call("seo_check_geo", "https://example.com"))
        assert out["ok"] is False


# ---------------------------------------------------------------------------
# seo_get_gsc_data + seo_find_opportunities
# ---------------------------------------------------------------------------


class TestGscTools:
    def test_gsc_data_invalid_url(self):
        out = _call("seo_get_gsc_data", "ftp://x")
        assert '"ok": false' in out

    def test_gsc_data_instructions(self):
        out = json.loads(_call("seo_get_gsc_data", "https://example.com", days=500))
        assert out["ok"] is False
        assert out["days"] == 90  # clamped
        assert "OAuth2" in out["instructions"]

    def test_find_opportunities_empty(self):
        out = _call("seo_find_opportunities", "")
        assert '"ok": false' in out

    def test_find_opportunities_bad_json(self):
        out = json.loads(_call("seo_find_opportunities", "{not json"))
        assert out["ok"] is False

    def test_find_opportunities_rows_not_list(self):
        out = json.loads(_call("seo_find_opportunities", '{"rows": {}}'))
        assert out["ok"] is False

    def test_find_opportunities_full(self):
        rows = {
            "rows": [
                "not-a-dict-row",
                {"query": "q1", "page": "/p1", "clicks": 5, "impressions": 100,
                 "ctr": 0.001, "position": 5},
                {"query": "q1", "page": "/p2", "clicks": 3, "impressions": 90,
                 "ctr": 0.03, "position": 6},
                {"query": "q2", "page": "/p3", "clicks": 0, "impressions": 50,
                 "ctr": 0.0, "position": "junk"},
                {"query": "q3", "page": "/p4", "clicks": 1, "impressions": 40,
                 "ctr": 0.9, "position": 1},
            ]
        }
        out = json.loads(
            _call("seo_find_opportunities", json.dumps(rows))
        )
        assert out["ok"] is True
        assert out["striking_distance_count"] >= 1
        assert out["low_ctr_count"] >= 1
        assert out["cannibalization_count"] == 1
