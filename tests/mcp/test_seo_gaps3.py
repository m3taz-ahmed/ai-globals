"""Third gap pass for aizee_mcp/tools/seo_tools.py — remaining branches."""
from __future__ import annotations

import json
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import aizee_mcp.tools.seo_tools as seo
from aizee_mcp.tools.seo_tools import (
    _classify_schema,
    _flesch_reading_ease,
    _parse_html,
    register_seo_tools,
)

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


class TestFetchCharset:
    def test_no_charset_defaults_utf8(self):
        resp = MagicMock()
        resp.headers = {"Content-Type": "text/html"}
        resp.status = 200
        resp.read.return_value = b"<html></html>"
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        opener = MagicMock()
        opener.open.return_value = resp
        with patch.object(seo, "_get_opener", return_value=opener):
            status, body, _headers = seo._fetch("https://ex.com")
        assert status == 200
        assert body == "<html></html>"


class TestParserBranches:
    def test_whitespace_heading(self):
        p = _parse_html("<h1>   </h1><h1>Real</h1>")
        assert p.h1s == ["Real"]

    def test_selfclosing_other_tag(self):
        p = _parse_html("<div><br/><custom/></div>")
        assert p is not None

    def test_feed_exception_swallowed(self):
        p = _parse_html(None)  # type: ignore[arg-type]
        assert p is not None

    def test_flesch_empty(self):
        assert _flesch_reading_ease("") == 0.0
        assert _flesch_reading_ease("   ") == 0.0


class TestCrawlBranches:
    def test_rss_abort(self):
        t = _tool("seo_audit_site")
        proc = MagicMock()
        # baseline small, then huge spike -> abort at memory guard
        proc.memory_info.side_effect = [
            MagicMock(rss=1000), MagicMock(rss=10**13),
        ]
        fake = MagicMock()
        fake.Process.return_value = proc
        html = '<a href="https://ex.com/p2">p2</a>'
        with (
            patch.object(seo, "_fetch", return_value=(200, html, {})),
            patch.dict(sys.modules, {"psutil": fake}),
        ):
            out = json.loads(t("https://ex.com"))
        assert "memory limit" in out["error"]

    def test_duplicate_normalized_skipped(self):
        t = _tool("seo_audit_site")
        page = '<a href="https://ex.com/p2">a</a><a href="https://ex.com/p2">b</a>'
        pages = {"https://ex.com": page, "https://ex.com/p2": "<h1>P2</h1>"}
        with patch.object(seo, "_fetch",
                          side_effect=lambda u: (200, pages.get(u, ""), {})):
            out = json.loads(t("https://ex.com"))
        assert out["pages_crawled"] == 2


class TestCwvNoneValue:
    def test_audit_missing_numeric(self):
        t = _tool("seo_check_cwv")
        data = {"lighthouseResult": {"audits": {"largest-contentful-paint": {}}}}
        resp = MagicMock()
        resp.read.return_value = json.dumps(data).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=resp):
            out = json.loads(t("https://ex.com"))
        assert out["metrics"]["lcp"]["value"] is None


class TestContentBranches:
    def test_punctuation_only_body(self):
        t = _tool("seo_analyze_content")
        with patch.object(seo, "_fetch",
                          return_value=(200, "<html><body>!!!</body></html>", {})):
            out = json.loads(t("https://ex.com"))
        assert out["ok"] is True

    def test_has_date_signal(self):
        t = _tool("seo_analyze_content")
        words = " ".join(["word"] * 350)
        html = (f"<html><body><h2>Q?</h2><p>published date: 2024 {words}</p>"
                '<meta name="author" content="me"></body></html>')
        with patch.object(seo, "_fetch", return_value=(200, html, {})):
            out = json.loads(t("https://ex.com"))
        types = {i["rule_id"] for i in out["issues"]}
        assert "no-date" not in types


class TestOpportunitiesBranches:
    def test_invalid_query(self):
        t = _tool("seo_find_opportunities")
        out = json.loads(t(""))
        assert out["ok"] is False

    def test_rows_edge_cases(self):
        t = _tool("seo_find_opportunities")
        rows = [
            42,
            {"query": "", "page": ""},
            {"query": "q", "page": "p", "position": "abc", "impressions": 5},
            {"query": "q2", "page": "p2", "position": 10, "impressions": 50, "ctr": 0.001, "clicks": 1},
        ]
        out = json.loads(t(json.dumps({"rows": rows})))
        assert out["ok"] is True


class TestClassifySchema:
    def test_non_dict(self):
        out = _classify_schema("just a string")
        assert out["type"] == ""

    def test_graph_dict(self):
        out = _classify_schema({"@graph": {"@type": "Article"}})
        assert out["status"] == "ACTIVE"
