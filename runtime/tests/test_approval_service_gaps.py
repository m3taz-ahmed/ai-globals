"""Gap-coverage tests for runtime/approval_service.py — SSRF guard + lifecycle."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from runtime.approval_service import (
    ApprovalRequest,
    ApprovalService,
    ApprovalStatus,
    ConsoleChannel,
    NotificationChannel,
    WebhookChannel,
    _SsrfSafeRedirectHandler,
    _validate_webhook_url,
)


class TestSsrfGuard:
    def test_bad_scheme(self):
        assert _validate_webhook_url("file:///etc/passwd") is False
        assert _validate_webhook_url("gopher://x") is False
        assert _validate_webhook_url("ftp://x") is False

    def test_no_hostname(self):
        assert _validate_webhook_url("http://") is False

    def test_private_ip_literal(self):
        assert _validate_webhook_url("http://127.0.0.1/hook") is False
        assert _validate_webhook_url("http://10.0.0.1/hook") is False
        assert _validate_webhook_url("http://192.168.1.1/") is False
        assert _validate_webhook_url("http://[::1]/") is False
        assert _validate_webhook_url("http://169.254.1.1/") is False

    def test_public_ip_literal(self):
        assert _validate_webhook_url("http://8.8.8.8/hook") is True

    def test_dns_private_resolution(self):
        infos = [(2, 1, 6, "", ("192.168.0.1", 0))]
        with patch("socket.getaddrinfo", return_value=infos):
            assert _validate_webhook_url("https://evil.internal/hook") is False

    def test_dns_public(self):
        infos = [(2, 1, 6, "", ("93.184.216.34", 0))]
        with patch("socket.getaddrinfo", return_value=infos):
            assert _validate_webhook_url("https://example.com/hook") is True

    def test_dns_failure(self):
        import socket
        with patch("socket.getaddrinfo", side_effect=socket.gaierror("nx")):
            assert _validate_webhook_url("https://nonexistent.invalid/") is False

    def test_dns_unparseable_ip_skipped(self):
        infos = [(2, 1, 6, "", ("not-an-ip", 0)),
                 (2, 1, 6, "", ("8.8.8.8", 0))]
        with patch("socket.getaddrinfo", return_value=infos):
            assert _validate_webhook_url("https://x.example/") is True


class TestRedirectHandler:
    def test_blocked_redirect(self):
        handler = _SsrfSafeRedirectHandler()
        req = MagicMock()
        req.full_url = "https://good.example/x"
        import urllib.error
        with patch("socket.getaddrinfo",
                   return_value=[(2, 1, 6, "", ("10.0.0.1", 0))]):
            with pytest.raises(urllib.error.HTTPError):
                handler.redirect_request(req, None, 302, "m", {}, "http://internal/")

    def test_allowed_redirect(self):
        handler = _SsrfSafeRedirectHandler()
        req = MagicMock()
        req.full_url = "https://good.example/x"
        with patch("socket.getaddrinfo",
                   return_value=[(2, 1, 6, "", ("8.8.8.8", 0))]), \
             patch("urllib.request.HTTPRedirectHandler.redirect_request",
                   return_value="NEWREQ"):
            assert handler.redirect_request(req, None, 302, "m", {}, "/y") == "NEWREQ"


class TestWebhookChannel:
    def test_ssrf_url_skipped(self):
        ch = WebhookChannel("http://127.0.0.1/hook")
        assert ch.send(ApprovalRequest(id="x" * 8, action="a", args={})) is False

    def test_send_success(self):
        ch = WebhookChannel("https://8.8.8.8/hook")
        req = ApprovalRequest(id="x" * 8, action="a", args={})
        with patch("urllib.request.build_opener") as bo:
            bo.return_value.open = MagicMock()
            assert ch.send(req) is True

    def test_send_failure(self):
        ch = WebhookChannel("https://8.8.8.8/hook")
        req = ApprovalRequest(id="x" * 8, action="a", args={})
        with patch("urllib.request.build_opener") as bo:
            bo.return_value.open = MagicMock(side_effect=OSError("net"))
            assert ch.send(req) is False


class TestChannels:
    def test_console(self, capsys):
        ch = ConsoleChannel()
        req = ApprovalRequest(id="abc12345", action="deploy", args={},
                              reason="prod")
        assert ch.send(req) is True
        assert "APPROVAL REQUIRED" in capsys.readouterr().out

    def test_base_not_implemented(self):
        ch = NotificationChannel()
        with pytest.raises(NotImplementedError):
            ch.send(ApprovalRequest(id="x", action="a", args={}))


class TestService:
    def _svc(self, **kw) -> ApprovalService:
        return ApprovalService(channels=[], **kw)

    def test_create_and_ttl(self):
        svc = self._svc(default_ttl=60)
        r = svc.create_request("act", {}, reason="r", extra="meta")
        assert r.status is ApprovalStatus.PENDING
        assert r.expires_at is not None
        assert r.metadata["extra"] == "meta"

    def test_notify_success_and_failure(self):
        good = MagicMock()
        good.send.return_value = True
        good.name = "good"
        bad = MagicMock()
        bad.send.side_effect = RuntimeError("x")
        bad.name = "bad"
        svc = ApprovalService(channels=[good, bad])
        req = svc.create_request("a", {})
        assert svc.notify(req) == ["good"]

    def test_create_and_notify(self, capsys):
        svc = ApprovalService()  # default console channel
        r = svc.create_and_notify("a", {}, reason="why")
        assert "APPROVAL" in capsys.readouterr().out
        assert svc.is_pending(r.id)

    def test_is_approved_expiry(self):
        svc = self._svc()
        r = svc.create_request("a", {}, ttl=-1)  # already expired
        assert svc.is_approved(r.id) is False
        assert svc._get(r.id).status is ApprovalStatus.EXPIRED

    def test_is_approved_missing(self):
        assert self._svc().is_approved("nope") is False

    def test_mark_resolved(self):
        svc = self._svc()
        r = svc.create_request("a", {})
        out = svc.mark_resolved(r.id, approved=True, resolved_by="admin")
        assert out.status is ApprovalStatus.APPROVED
        assert out.resolved_by == "admin"
        assert svc.is_approved(r.id) is True
        # non-pending can't be re-resolved
        assert svc.mark_resolved(r.id, approved=False) is None

    def test_mark_resolved_missing(self):
        assert self._svc().mark_resolved("x", True) is None

    def test_cancel(self):
        svc = self._svc()
        r = svc.create_request("a", {})
        out = svc.cancel(r.id)
        assert out.status is ApprovalStatus.CANCELLED
        assert svc.cancel(r.id) is None  # already resolved

    def test_list_pending_and_all(self):
        svc = self._svc()
        r1 = svc.create_request("a", {})
        svc.create_request("b", {})
        svc.mark_resolved(r1.id, approved=False)
        assert len(svc.list_all()) == 2
        pend = svc.list_pending()
        assert len(pend) == 1 and pend[0].status is ApprovalStatus.PENDING


class TestPersistence:
    def test_store_roundtrip(self):
        store = MagicMock()
        saved = {}
        store.put.side_effect = lambda k, v: saved.__setitem__(k, v)
        store.get.side_effect = saved.get
        svc = ApprovalService(store=store, channels=[])
        r = svc.create_request("a", {"k": 1})
        assert f"approval:{r.id}" in saved
        # new service instance loads from store
        svc2 = ApprovalService(store=store, channels=[])
        loaded = svc2._get(r.id)
        assert loaded is not None and loaded.action == "a"

    def test_store_returns_none(self):
        store = MagicMock()
        store.get.return_value = None
        svc = ApprovalService(store=store, channels=[])
        assert svc._get("x") is None


class TestSerialization:
    def test_from_dict_status_str(self):
        r = ApprovalRequest(id="x", action="a", args={})
        d = r.to_dict()
        assert d["status"] == "pending"
        r2 = ApprovalRequest.from_dict(d)
        assert r2.status is ApprovalStatus.PENDING

    def test_from_dict_status_enum(self):
        r = ApprovalRequest(id="x", action="a", args={})
        d = r.to_dict()
        d["status"] = ApprovalStatus.APPROVED
        r2 = ApprovalRequest.from_dict(d)
        assert r2.status is ApprovalStatus.APPROVED
