"""Gap coverage for aizee_mcp/adapters.py: redirect blocker, edge paths."""

from __future__ import annotations

import asyncio
import socket
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

import aizee_mcp.adapters as ad
from aizee_mcp.adapters import (
    AdapterError,
    RemoteA2AAdapter,
    Session,
    _a2a_open,
    _A2ARedirectBlocker,
    _is_loopback_ip,
    _is_private_or_reserved_ip,
    _positive_float,
    _validate_endpoint,
)

pytestmark = pytest.mark.mcp


class TestIpHelpers:
    def test_loopback_empty(self):
        assert _is_loopback_ip("") is False

    def test_loopback_v6(self):
        assert _is_loopback_ip("::1") is True

    def test_loopback_v4(self):
        assert _is_loopback_ip("127.0.0.1") is True

    def test_loopback_lookalike(self):
        assert _is_loopback_ip("127.0.0.1.evil.com") is False
        assert _is_loopback_ip("127.0.0.256") is False

    def test_private_empty(self):
        assert _is_private_or_reserved_ip("") is False

    def test_private_v6_loopback(self):
        assert _is_private_or_reserved_ip("::1") is True

    def test_private_ranges(self):
        assert _is_private_or_reserved_ip("10.0.0.1") is True
        assert _is_private_or_reserved_ip("169.254.169.254") is True
        assert _is_private_or_reserved_ip("8.8.8.8") is False


class TestRedirectBlocker:
    def _req(self, url="http://localhost:9000/a"):
        r = MagicMock()
        r.full_url = url
        return r

    def test_cross_origin_blocked(self):
        b = _A2ARedirectBlocker()
        with pytest.raises(urllib.error.HTTPError):
            b.redirect_request(self._req(), MagicMock(), 301, "m", {},
                               "http://evil.com/x")

    def test_bad_scheme_blocked(self):
        b = _A2ARedirectBlocker()
        with pytest.raises(urllib.error.HTTPError):
            b.redirect_request(self._req(), MagicMock(), 301, "m", {},
                               "file:///etc/passwd")

    def test_private_ip_redirect_blocked(self):
        b = _A2ARedirectBlocker()
        with pytest.raises(urllib.error.HTTPError):
            b.redirect_request(self._req(), MagicMock(), 301, "m", {},
                               "http://localhost:9000/redir-to-10.0.0.1")

    def test_same_origin_allowed(self):
        b = _A2ARedirectBlocker()
        with patch.object(urllib.request.HTTPRedirectHandler, "redirect_request",
                          return_value="newreq"):
            out = b.redirect_request(self._req(), MagicMock(), 301, "m", {},
                                     "/same-origin")
        assert out == "newreq"


class TestA2aOpen:
    def test_str_url(self):
        with patch("urllib.request.build_opener") as bo:
            opener = MagicMock()
            bo.return_value = opener
            _a2a_open("http://localhost:1/x", MagicMock(), 5)
        assert opener.open.called

    def test_request_obj(self):
        with patch("urllib.request.build_opener") as bo:
            opener = MagicMock()
            bo.return_value = opener
            _a2a_open(urllib.request.Request("http://localhost:1/x"), MagicMock(), 5)
        assert opener.open.called


class TestPositiveFloat:
    def test_bad_type(self):
        assert _positive_float("abc", 5.0) == 5.0

    def test_negative(self):
        assert _positive_float(-1, 5.0) == 5.0

    def test_nan(self):
        assert _positive_float(float("nan"), 5.0) == 5.0

    def test_clamped(self):
        assert _positive_float(99999, 5.0, maximum=100) == 100


class TestEndpointValidation:
    def test_dns_private_blocked(self):
        with patch("socket.getaddrinfo",
                   return_value=[(0, 0, 0, "", ("10.0.0.1", 0))]):
            with pytest.raises(AdapterError):
                _validate_endpoint("https://internal.example.com")

    def test_dns_gaierror_passes(self):
        with patch("socket.getaddrinfo", side_effect=socket.gaierror("no")):
            _validate_endpoint("https://example.com")  # no raise

    def test_ipv6_mapped_private(self):
        with patch("socket.getaddrinfo",
                   return_value=[(0, 0, 0, "", ("[::ffff:10.0.0.1]", 0))]):
            with pytest.raises(AdapterError):
                _validate_endpoint("https://mapped.example.com")


class TestLaunchPollEdges:
    def _adapter(self):
        return RemoteA2AAdapter({"endpoint": "http://localhost:9000"})

    def test_launch_malformed_json(self):
        a = self._adapter()
        resp = MagicMock()
        resp.read.return_value = b"{bad"
        with patch.object(ad, "_a2a_open", return_value=resp):
            with pytest.raises(AdapterError):
                asyncio.run(a.launch("task"))

    def test_launch_non_dict(self):
        a = self._adapter()
        resp = MagicMock()
        resp.read.return_value = b"[1,2]"
        with patch.object(ad, "_a2a_open", return_value=resp):
            with pytest.raises(AdapterError):
                asyncio.run(a.launch("task"))

    def test_poll_missing_remote_id(self):
        a = self._adapter()
        s = Session(session_id="x", backend=a.backend, profile="p")
        s.artifacts = {}  # no remote_session_id
        out = asyncio.run(a.poll(s))
        assert out.status == "failed"

    def test_poll_malformed_json(self):
        a = self._adapter()
        s = Session(session_id="x", backend=a.backend, profile="p")
        s.artifacts = {"remote_session_id": "r1"}
        resp = MagicMock()
        resp.read.return_value = b"{bad"
        with patch.object(ad, "_a2a_open", return_value=resp):
            out = asyncio.run(a.poll(s))
        assert out.status == "failed"

    def test_poll_non_dict(self):
        a = self._adapter()
        s = Session(session_id="x", backend=a.backend, profile="p")
        s.artifacts = {"remote_session_id": "r1"}
        resp = MagicMock()
        resp.read.return_value = b"42"
        with patch.object(ad, "_a2a_open", return_value=resp):
            out = asyncio.run(a.poll(s))
        assert out.status == "failed"
