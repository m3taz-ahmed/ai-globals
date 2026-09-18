"""Gap coverage for aizee_mcp/tools/seo_tools.py internals."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
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


class TestPrivateIp:
    def test_ipv4_with_port(self):
        assert seo._is_private_ip("127.0.0.1:8080") is True

    def test_ipv6_brackets(self):
        assert seo._is_private_ip("[::1]") is True

    def test_unspecified(self):
        assert seo._is_private_ip("0.0.0.0") is True

    def test_empty(self):
        assert seo._is_private_ip("") is False

    def test_public_domain_resolves(self):
        with patch("socket.getaddrinfo",
                   return_value=[(0, 0, 0, "", ("8.8.8.8", 0))]):
            assert seo._is_private_ip("dns.google") is False

    def test_domain_resolves_private(self):
        with patch("socket.getaddrinfo",
                   return_value=[(0, 0, 0, "", ("10.0.0.1", 0))]):
            assert seo._is_private_ip("internal.example.com") is True

    def test_domain_dns_failure_fail_closed(self):
        with patch("socket.getaddrinfo", side_effect=socket.gaierror("no")):
            assert seo._is_private_ip("nonexistent.invalid") is True

    def test_ipv4_mapped_v6(self):
        with patch("socket.getaddrinfo",
                   return_value=[(0, 0, 0, "", ("::ffff:127.0.0.1", 0))]):
            assert seo._is_private_ip("mapped.example.com") is True

    def test_bad_sockaddr_ignored(self):
        with patch("socket.getaddrinfo",
                   return_value=[(0, 0, 0, "", ("not-an-ip", 0)),
                                 (0, 0, 0, "", ("8.8.8.8", 0))]):
            assert seo._is_private_ip("mixed.example.com") is False


class TestValidateUrl:
    def test_credentials_rejected(self):
        out = json.loads(seo._validate_url("http://user:pass@example.com"))
        assert out["ok"] is False and "credentials" in out["error"]

    def test_empty_url(self):
        out = json.loads(seo._validate_url(""))
        assert out["ok"] is False

    def test_blocked_scheme(self):
        out = json.loads(seo._validate_url("file:///etc/passwd"))
        assert out["ok"] is False


class TestFetch:
    def test_fetch_invalid_url(self):
        status, body, _ = seo._fetch("file:///etc")
        assert status is None and body == ""

    def test_fetch_non_html(self):
        resp = MagicMock()
        resp.headers = {"Content-Type": "image/png"}
        resp.status = 200
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        opener = MagicMock()
        opener.open.return_value = resp
        with patch.object(seo, "_get_opener", return_value=opener):
            status, body, _ = seo._fetch("http://example.com/x.png")
        assert status == 200 and body == ""

    def test_fetch_html_charset(self):
        resp = MagicMock()
        resp.headers = {"Content-Type": "text/html; charset=latin-1"}
        resp.status = 200
        resp.read.return_value = b"<html></html>"
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        opener = MagicMock()
        opener.open.return_value = resp
        with patch.object(seo, "_get_opener", return_value=opener):
            status, body, _ = seo._fetch("http://example.com/")
        assert status == 200 and "<html>" in body

    def test_fetch_url_error(self):
        opener = MagicMock()
        opener.open.side_effect = urllib.error.URLError("down")
        with patch.object(seo, "_get_opener", return_value=opener):
            status, _, _ = seo._fetch("http://example.com/")
        assert status is None

    def test_fetch_http_exception(self):
        import http.client

        opener = MagicMock()
        opener.open.side_effect = http.client.IncompleteRead(b"")
        with patch.object(seo, "_get_opener", return_value=opener):
            status, _, _ = seo._fetch("http://example.com/")
        assert status is None

    def test_opener_cached(self):
        seo._SEO_OPENER = None
        o1 = seo._get_opener()
        assert seo._get_opener() is o1
        seo._SEO_OPENER = None


class TestRedirectHandler:
    def test_blocked_redirect_raises(self):
        h = seo._SsrfSafeRedirectHandler()
        req = MagicMock()
        req.full_url = "http://example.com/a"
        with patch.object(seo, "_validate_url", return_value='{"ok": false}'):
            with pytest.raises(urllib.error.HTTPError):
                h.redirect_request(req, MagicMock(), 301, "m", {}, "http://10.0.0.1/")

    def test_allowed_redirect(self):
        h = seo._SsrfSafeRedirectHandler()
        req = MagicMock()
        req.full_url = "http://example.com/a"
        req.headers = {}
        req.unverifiable = False
        req.type = "http"
        req.origin_req_host = "example.com"
        with patch.object(seo, "_validate_url", return_value=None), \
             patch.object(urllib.request.HTTPRedirectHandler, "redirect_request",
                          return_value="newreq"):
            out = h.redirect_request(req, MagicMock(), 301, "m", {}, "/b")
        assert out == "newreq"


class TestFlesch:
    def test_empty(self):
        assert seo._flesch_reading_ease("") == 0.0

    def test_whitespace(self):
        assert seo._flesch_reading_ease("   ") == 0.0

    def test_normal(self):
        score = seo._flesch_reading_ease("The cat sat on the mat. It was happy.")
        assert 0.0 <= score <= 100.0


class TestAuditSite:
    def test_max_pages_bad_type(self):
        with patch.object(seo, "_fetch", return_value=(None, "", {})):
            out = json.loads(_call("seo_audit_site", "http://example.com", max_pages="x"))
        assert out["ok"] is True

    def test_crawl_skips_bad_pages(self):
        html = "<html><head><title>T</title></head><body>" + "word " * 400 + "</body></html>"

        def fake_fetch(url):
            if "bad" in url:
                raise RuntimeError("boom")
            return (200, html, {})

        with patch.object(seo, "_fetch", side_effect=fake_fetch):
            out = json.loads(_call("seo_audit_site", "http://example.com", max_pages=2))
        assert out["ok"] is True

    def test_crawl_deadline(self):
        with patch.object(seo, "_fetch", return_value=(200, "<html>x</html>", {})), \
             patch("time.monotonic", side_effect=[0, 1000, 1000, 1000, 1000, 1000]):
            out = json.loads(_call("seo_audit_site", "http://example.com"))
        assert out["ok"] is True


class TestCheckCwv:
    def test_api_failure(self):
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("down")):
            out = json.loads(_call("seo_check_cwv", "http://example.com"))
        assert out["ok"] is False and "PageSpeed" in out["error"]

    def test_no_lighthouse(self):
        resp = MagicMock()
        resp.read.return_value = b"{}"
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=resp):
            out = json.loads(_call("seo_check_cwv", "http://example.com"))
        assert out["ok"] is False and "lighthouseResult" in out["error"]

    def test_metrics_parsed(self):
        data = {"lighthouseResult": {"audits": {
            "largest-contentful-paint": {"numericValue": 2000},
            "cumulative-layout-shift": {"numericValue": 0.05},
            "first-contentful-paint": {"numericValue": 1500},
            "server-response-time": {"numericValue": 500},
        }}}
        resp = MagicMock()
        resp.read.return_value = json.dumps(data).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=resp):
            out = json.loads(_call("seo_check_cwv", "http://example.com"))
        assert out["ok"] is True and out["metrics"]["lcp"]["value"] == 2.0


class TestValidateSchema:
    def test_fetch_fail(self):
        with patch.object(seo, "_fetch", return_value=(None, "", {})):
            out = json.loads(_call("seo_validate_schema", "http://example.com"))
        assert out["ok"] is False

    def test_invalid_jsonld(self):
        html = '<html><head><script type="application/ld+json">{bad</script></head></html>'
        with patch.object(seo, "_fetch", return_value=(200, html, {})):
            out = json.loads(_call("seo_validate_schema", "http://example.com"))
        assert out["ok"] is True and out["schemas"][0]["status"] == "ERROR"


class TestAnalyzeContent:
    def test_fetch_fail(self):
        with patch.object(seo, "_fetch", return_value=(None, "", {})):
            out = json.loads(_call("seo_analyze_content", "http://example.com"))
        assert out["ok"] is False

    def test_no_paragraphs_fallback(self):
        html = "<html><body>single</body></html>"
        with patch.object(seo, "_fetch", return_value=(200, html, {})):
            out = json.loads(_call("seo_analyze_content", "http://example.com"))
        assert out["ok"] is True
