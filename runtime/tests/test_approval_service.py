"""Tests for runtime/approval_service.py."""

from __future__ import annotations

import time

import pytest

from runtime.approval_service import (
    ApprovalRequest,
    ApprovalService,
    ApprovalStatus,
    ConsoleChannel,
    NotificationChannel,
    WebhookChannel,
)


class TestApprovalRequest:
    def test_to_dict_roundtrip(self):
        r = ApprovalRequest(id="abc", action="deploy", args={"env": "prod"})
        d = r.to_dict()
        assert d["status"] == "pending"
        r2 = ApprovalRequest.from_dict(d)
        assert r2.status is ApprovalStatus.PENDING
        assert r2.action == "deploy"

    def test_from_dict_status_enum(self):
        r = ApprovalRequest.from_dict({
            "id": "x", "action": "a", "args": {}, "status": "approved",
            "created_at": 0, "resolved_at": None, "resolved_by": None,
            "expires_at": None, "reason": "", "metadata": {},
        })
        assert r.status is ApprovalStatus.APPROVED


class TestApprovalService:
    def test_create_request(self):
        svc = ApprovalService(channels=[])
        req = svc.create_request("deploy", {"env": "prod"}, reason="prod deploy")
        assert req.status is ApprovalStatus.PENDING
        assert req.action == "deploy"

    def test_mark_approved(self):
        svc = ApprovalService(channels=[])
        req = svc.create_request("deploy", {})
        result = svc.mark_resolved(req.id, approved=True, resolved_by="admin")
        assert result is not None
        assert svc.is_approved(req.id) is True

    def test_mark_denied(self):
        svc = ApprovalService(channels=[])
        req = svc.create_request("deploy", {})
        svc.mark_resolved(req.id, approved=False)
        assert svc.is_approved(req.id) is False

    def test_is_pending(self):
        svc = ApprovalService(channels=[])
        req = svc.create_request("deploy", {})
        assert svc.is_pending(req.id) is True
        svc.mark_resolved(req.id, True)
        assert svc.is_pending(req.id) is False

    def test_expiry(self):
        svc = ApprovalService(channels=[], default_ttl=0.01)
        req = svc.create_request("deploy", {})
        time.sleep(0.02)
        assert svc.is_approved(req.id) is False
        expired = svc._get(req.id)
        assert expired is not None
        assert expired.status is ApprovalStatus.EXPIRED

    def test_cancel(self):
        svc = ApprovalService(channels=[])
        req = svc.create_request("deploy", {})
        svc.cancel(req.id)
        cancelled = svc._get(req.id)
        assert cancelled is not None
        assert cancelled.status is ApprovalStatus.CANCELLED

    def test_list_pending(self):
        svc = ApprovalService(channels=[])
        r1 = svc.create_request("a", {})
        svc.create_request("b", {})
        svc.mark_resolved(r1.id, True)
        pending = svc.list_pending()
        assert len(pending) == 1
        assert pending[0].action == "b"

    def test_create_and_notify(self):
        svc = ApprovalService(channels=[ConsoleChannel()])
        req = svc.create_and_notify("deploy", {}, reason="test")
        assert req.status is ApprovalStatus.PENDING

    def test_unknown_request_returns_none(self):
        svc = ApprovalService(channels=[])
        assert svc.mark_resolved("nope", True) is None
        assert svc.is_approved("nope") is False


class TestChannels:
    def test_console_channel(self, capsys):
        ch = ConsoleChannel()
        req = ApprovalRequest(id="abc123def", action="deploy", args={})
        assert ch.send(req) is True
        captured = capsys.readouterr()
        assert "APPROVAL REQUIRED" in captured.out

    def test_webhook_channel_failure(self):
        ch = WebhookChannel("http://127.0.0.1:1/nope")
        req = ApprovalRequest(id="x", action="deploy", args={})
        # Should not raise, returns False on failure.
        assert ch.send(req) is False

    def test_custom_channel(self):
        class CountingChannel(NotificationChannel):
            name = "counting"
            def __init__(self):
                self.count = 0
            def send(self, request):
                self.count += 1
                return True
        ch = CountingChannel()
        svc = ApprovalService(channels=[ch])
        svc.create_and_notify("deploy", {})
        assert ch.count == 1
