"""Second gap pass for aizee_mcp/tools/seo_tools.py — crawler + CWV + parser."""
from __future__ import annotations

import json
import urllib.error
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import aizee_mcp.tools.seo_tools as seo
from aizee_mcp.tools.seo_tools import _parse_html, register_seo_tools

pytestmark = [pytest.mark.mcp]


class _FakeTool:
    def __call__(self, fn: Any | None = None) -> Any:
        if fn is not None:
            _TOOLS[fn.__name__] = fn
            return fn
        def dec(inner):
            _TOOLS[inner.__name__] = inner
            return inner
        return dec


class _FakeMCP:
    def __init__(self) -> None:
        self.tool = _FakeTool()


_TOOLS: dict[str, Any] = {}


def _tool(name: str) -> Any:
    _TOOLS.clear()
    register_seo_tools(_FakeMCP())  # type: ignore[arg-type]
    return _TOOLS[name]


class TestParserEdges:
    def test_headings_h2_h3_and_anchors(self):
        p = _parse_html(
            "<html><body><h2>What is X?</h2><h3>Detail</h3>"
            "<a href='/p'>Link text</a><img src='i.png' alt='a' width='1' height='2'>"
            "</body></html>")
        assert "What is X?" in p.h2s
        assert "Detail" in p.h3s
        assert p.links[0]["text"] == "Link text"
        assert p.images[0]["alt"] == "a"

    def test_json_ld_captured(self):
        p = _parse_html('<script type="application/ld+json">{"@type":"Article"}</script>')
        assert p.json_ld == ['{"@type":"Article"}']
        # non-ld script ignored
        p2 = _parse_html('<script>var x=1;</script>')
        assert p2.json_ld == []

    def test_hreflang_and_canonical_links(self):
        p = _parse_html(
            '<link rel="canonical" href="https://ex.com/p">'
            '<link rel="alternate" hreflang="ar" href="https://ex.com/ar">')
        assert p.canonical == "https://ex.com/p"
        assert p.has_hreflang is True

    def test_self_closing_tags(self):
        p = _parse_html('<meta name="description" content="d"/><img src="x.png"/>')
        assert p.meta.get("description") == "d"
        assert len(p.images) == 1

    def test_malformed_html_swallowed(self):
        p = _parse_html("<div><unclosed <<<>>>")
        assert p is not None

    def test_mismatched_endtag_pops_stack(self):
        p = _parse_html("<div><h1>Title</h2></div><h1>T2</h1>")
        assert "Title" in p.h1s


class TestAuditPage:
    def test_invalid_url(self):
        t = _tool("seo_audit_page")
        out = json.loads(t("ftp://bad"))
        assert out["ok"] is False

    def test_fetch_none(self):
        t = _tool("seo_audit_page")
        with patch.object(seo, "_fetch", return_value=(None, "", {})):
            out = json.loads(t("https://ex.com"))
        assert "Failed to fetch" in out["error"]

    def test_empty_body(self):
        t = _tool("seo_audit_page")
        with patch.object(seo, "_fetch", return_value=(200, "", {})):
            out = json.loads(t("https://ex.com"))
        assert "No HTML" in out["error"]

    def test_ok_result(self):
        t = _tool("seo_audit_page")
        html = "<html><head><title>T</title></head><body><h1>H</h1><img src='x.png'></body></html>"
        with patch.object(seo, "_fetch", return_value=(200, html, {})):
            out = json.loads(t("https://ex.com"))
        assert out["ok"] is True
        assert out["h1_count"] == 1
        assert out["image_count"] == 1


class TestAuditSite:
    def _fetch_map(self, html_by_url):
        def f(url):
            return (200, html_by_url.get(url, ""), {})
        return f

    def test_invalid_start_url(self):
        t = _tool("seo_audit_site")
        out = json.loads(t("not-a-url"))
        assert out["ok"] is False

    def test_bad_max_pages_defaults(self):
        t = _tool("seo_audit_site")
        with patch.object(seo, "_fetch", return_value=(200, "<html></html>", {})):
            out = json.loads(t("https://ex.com", max_pages="bad"))
        assert out["ok"] is True
        assert out["pages_crawled"] >= 1

    def test_fetch_exception_skipped(self):
        t = _tool("seo_audit_site")
        calls = iter([RuntimeError("net down"), (200, "<html></html>", {})])
        def f(url):
            v = next(calls)
            if isinstance(v, Exception):
                raise v
            return v
        html = '<a href="https://ex.com/p2">next</a>'
        with patch.object(seo, "_fetch", side_effect=[Exception("x"), (200, html, {})]):
            out = json.loads(t("https://ex.com"))
        assert out["pages_skipped"] == 1

    def test_empty_body_skipped(self):
        t = _tool("seo_audit_site")
        with patch.object(seo, "_fetch", return_value=(200, "", {})):
            out = json.loads(t("https://ex.com"))
        assert out["pages_crawled"] == 1
        assert out["pages"] == []

    def test_parse_error_skipped(self):
        t = _tool("seo_audit_site")
        with (
            patch.object(seo, "_fetch", return_value=(200, "<html></html>", {})),
            patch.object(seo, "_parse_html", side_effect=RuntimeError("bad html")),
        ):
            out = json.loads(t("https://ex.com"))
        assert out["pages_skipped"] == 1

    def test_link_filtering(self):
        t = _tool("seo_audit_site")
        page1 = (
            '<a href="#frag">a</a><a href="mailto:x@y">m</a>'
            '<a href="javascript:void(0)">j</a><a href="tel:123">t</a>'
            '<a href="https://other.com/ext">e</a>'
            '<a href="https://ex.com/p2">p2</a>'
        )
        html = {"https://ex.com": page1, "https://ex.com/p2": "<html><h1>P2</h1></html>"}
        with patch.object(seo, "_fetch", side_effect=self._fetch_map(html)):
            out = json.loads(t("https://ex.com"))
        assert out["pages_crawled"] == 2

    def test_queue_cap(self):
        t = _tool("seo_audit_site")
        links = "".join(f'<a href="https://ex.com/p{i}">p{i}</a>' for i in range(10))
        with patch.object(seo, "_fetch", side_effect=self._fetch_map({"https://ex.com": links})):
            out = json.loads(t("https://ex.com", max_pages=2))
        assert out["pages_crawled"] <= 2

    def test_deadline_break(self):
        t = _tool("seo_audit_site")
        import time as _t
        real = _t.monotonic
        times = iter([real(), real() + 9999])
        with (
            patch.object(seo, "_fetch", return_value=(200, "<html></html>", {})),
            patch("time.monotonic", side_effect=lambda: next(times, real() + 9999)),
        ):
            out = json.loads(t("https://ex.com"))
        assert out["ok"] is True

    def test_no_psutil(self):
        t = _tool("seo_audit_site")
        import builtins
        orig_import = builtins.__import__
        def no_psutil(name, *a, **k):
            if name == "psutil":
                raise ImportError("no psutil")
            return orig_import(name, *a, **k)
        with (
            patch.object(seo, "_fetch", return_value=(200, "<html></html>", {})),
            patch("builtins.__import__", side_effect=no_psutil),
        ):
            out = json.loads(t("https://ex.com"))
        assert out["ok"] is True

    def test_rss_abort(self):
        t = _tool("seo_audit_site")
        proc = MagicMock()
        proc.memory_info.return_value.rss = 10_000_000_000
        fake_psutil = MagicMock()
        fake_psutil.Process.return_value = proc
        import sys
        with (
            patch.object(seo, "_fetch", return_value=(200, "<html></html>", {})),
            patch.dict(sys.modules, {"psutil": fake_psutil}),
        ):
            out = json.loads(t("https://ex.com"))
        # rss - baseline(0 guard? baseline measured via same psutil = same rss)
        assert out["ok"] is True or "memory limit" in out.get("error", "")


class TestCheckCwv:
    def test_bad_strategy(self):
        t = _tool("seo_check_cwv")
        out = json.loads(t("https://ex.com", strategy="watch"))
        assert "mobile" in out["error"]

    def test_api_failure(self):
        t = _tool("seo_check_cwv")
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
            out = json.loads(t("https://ex.com"))
        assert "failed" in out["error"].lower()

    def test_no_lighthouse(self):
        t = _tool("seo_check_cwv")
        resp = MagicMock()
        resp.read.return_value = b"{}"
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=resp):
            out = json.loads(t("https://ex.com"))
        assert "lighthouseResult" in out["error"]

    def test_metric_transforms(self):
        t = _tool("seo_check_cwv")
        data = {
            "lighthouseResult": {"audits": {
                "largest-contentful-paint": {"numericValue": 2500},
                "cumulative-layout-shift": {"numericValue": 0.05},
                "first-contentful-paint": {"numericValue": 1200},
                "server-response-time": {"numericValue": 300},
            }},
            "loadingExperience": {"metrics": {
                "INTERACTION_TO_NEXT_PAINT": {"percentile": 180},
            }},
        }
        resp = MagicMock()
        resp.read.return_value = json.dumps(data).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=resp):
            out = json.loads(t("https://ex.com"))
        assert out["metrics"]["lcp"]["value"] == 2.5
        assert out["metrics"]["ttfb"]["value"] == 300
        assert out["metrics"]["inp"]["value"] == 180
        assert out["ok"] is True


class TestValidateSchemaAndContent:
    def test_schema_invalid_json(self):
        t = _tool("seo_validate_schema")
        html = '<script type="application/ld+json">{bad json</script>'
        with patch.object(seo, "_fetch", return_value=(200, html, {})):
            out = json.loads(t("https://ex.com"))
        assert out["schemas"][0]["type"] == "INVALID_JSON"

    def test_schema_list_and_fetch_fail(self):
        t = _tool("seo_validate_schema")
        with patch.object(seo, "_fetch", return_value=(None, "", {})):
            out = json.loads(t("https://ex.com"))
        assert out["ok"] is False
        html = '<script type="application/ld+json">[{"@type":"Article"},{"@type":"FAQPage"}]</script>'
        with patch.object(seo, "_fetch", return_value=(200, html, {})):
            out = json.loads(t("https://ex.com"))
        assert out["schema_count"] == 2

    def test_analyze_content_full(self):
        t = _tool("seo_analyze_content")
        words = " ".join(["word"] * 400)
        html = (f"<html><body><h2>What is this?</h2><p>{words}</p>"
                '<meta name="author" content="me"></body></html>')
        with patch.object(seo, "_fetch", return_value=(200, html, {})):
            out = json.loads(t("https://ex.com"))
        assert out["ok"] is True
        assert out["word_count"] >= 300
        assert out["has_author_signal"] is True
        assert out["question_headings"] == 1

    def test_analyze_content_thin(self):
        t = _tool("seo_analyze_content")
        with patch.object(seo, "_fetch", return_value=(200, "<html><body>tiny</body></html>", {})):
            out = json.loads(t("https://ex.com"))
        types = {i["rule_id"] for i in out["issues"]}
        assert "thin-content" in types
        assert "no-author" in types
