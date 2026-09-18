"""Tests for runtime/approval_channels.py — Slack/Discord/Email webhooks."""

from __future__ import annotations

import json
from unittest import mock

from runtime.approval_channels import (
    DiscordChannel,
    EmailChannel,
    SlackChannel,
    _escape_html,
    _iso_timestamp,
    _post_json,
)
from runtime.approval_service import ApprovalRequest, ApprovalStatus


def _req(status: ApprovalStatus = ApprovalStatus.PENDING, **kw) -> ApprovalRequest:
    return ApprovalRequest(
        id=kw.pop("id", "abcdef1234567890"),
        action=kw.pop("action", "deploy_prod"),
        args=kw.pop("args", {}),
        reason=kw.pop("reason", "risky"),
        status=status,
        **kw,
    )


class TestPostJson:
    def test_ssrf_rejected(self):
        # file:// scheme fails validation without touching the network
        assert _post_json("file:///etc/passwd", {}) is False

    def test_private_ip_rejected(self):
        assert _post_json("http://127.0.0.1:9999/hook", {}) is False
        assert _post_json("http://169.254.169.254/latest", {}) is False

    def test_success_2xx(self):
        with mock.patch("runtime.approval_channels._validate_webhook_url", return_value=True), \
             mock.patch("runtime.approval_channels.urllib.request.build_opener") as bo:
            bo.return_value.open.return_value = mock.Mock(status=200)
            assert _post_json("https://hooks.example.com/x", {"a": 1}) is True

    def test_non_2xx(self):
        with mock.patch("runtime.approval_channels._validate_webhook_url", return_value=True), \
             mock.patch("runtime.approval_channels.urllib.request.build_opener") as bo:
            bo.return_value.open.return_value = mock.Mock(status=500)
            assert _post_json("https://hooks.example.com/x", {}) is False

    def test_network_error(self):
        with mock.patch("runtime.approval_channels._validate_webhook_url", return_value=True), \
             mock.patch("runtime.approval_channels.urllib.request.build_opener") as bo:
            bo.return_value.open.side_effect = OSError("conn refused")
            assert _post_json("https://hooks.example.com/x", {}) is False


class TestSlackChannel:
    def _send_capture(self, request, **kw):
        ch = SlackChannel("https://hooks.slack.com/x", **kw)
        with mock.patch("runtime.approval_channels._post_json", return_value=True) as pj:
            assert ch.send(request) is True
        return json.loads((pj.call_args[0][1].__str__() and pj.call_args[1].get("payload")) or pj.call_args[0][1] if isinstance(pj.call_args[0][1], dict) else pj.call_args[0][1])

    def test_pending_has_buttons(self):
        ch = SlackChannel("https://hooks.slack.com/x")
        captured = {}
        def fake_post(url, payload, headers=None):
            captured["payload"] = payload
            return True
        with mock.patch("runtime.approval_channels._post_json", side_effect=fake_post):
            assert ch.send(_req()) is True
        payload = captured["payload"]
        actions = [b for b in payload["blocks"] if b["type"] == "actions"]
        assert len(actions) == 1
        btns = actions[0]["elements"]
        assert btns[0]["value"].startswith("approve:")
        assert btns[1]["value"].startswith("deny:")
        assert "Approval Required: deploy_prod" in payload["blocks"][0]["text"]["text"]

    def test_approved_no_buttons(self):
        ch = SlackChannel("https://hooks.slack.com/x")
        captured = {}
        with mock.patch("runtime.approval_channels._post_json",
                        side_effect=lambda u, p, h=None: captured.update(p=p) or True):
            ch.send(_req(ApprovalStatus.APPROVED))
        assert not any(b["type"] == "actions" for b in captured["p"]["blocks"])

    def test_channel_override(self):
        ch = SlackChannel("https://hooks.slack.com/x", channel="#approvals")
        captured = {}
        with mock.patch("runtime.approval_channels._post_json",
                        side_effect=lambda u, p, h=None: captured.update(p=p) or True):
            ch.send(_req())
        assert captured["p"]["channel"] == "#approvals"

    def test_args_field_truncated(self):
        ch = SlackChannel("https://hooks.slack.com/x")
        captured = {}
        big_args = {"data": "x" * 2000}
        with mock.patch("runtime.approval_channels._post_json",
                        side_effect=lambda u, p, h=None: captured.update(p=p) or True):
            ch.send(_req(args=big_args))
        fields = captured["p"]["blocks"][1]["fields"]
        args_field = next(f for f in fields if "*Args:*" in f["text"])
        assert args_field["text"].endswith("...```")

    def test_status_emojis(self):
        assert SlackChannel._status_emoji("pending") == ":hourglass:"
        assert SlackChannel._status_emoji("approved") == ":white_check_mark:"
        assert SlackChannel._status_emoji("denied") == ":x:"
        assert SlackChannel._status_emoji("weird") == ":question:"


class TestDiscordChannel:
    def test_embed_structure(self):
        ch = DiscordChannel("https://discord.com/api/webhooks/x")
        captured = {}
        with mock.patch("runtime.approval_channels._post_json",
                        side_effect=lambda u, p, h=None: captured.update(p=p) or True):
            assert ch.send(_req(reason="test reason", args={"k": 1})) is True
        payload = captured["p"]
        assert payload["username"] == "aiZee Approvals"
        embed = payload["embeds"][0]
        assert embed["title"] == "Approval Required: deploy_prod"
        assert embed["color"] == 16776960  # pending yellow
        names = [f["name"] for f in embed["fields"]]
        assert "Action" in names and "Reason" in names and "Args" in names

    def test_color_map(self):
        ch = DiscordChannel("https://discord.com/api/webhooks/x")
        assert ch._build_embed(_req(ApprovalStatus.APPROVED))["color"] == 3066993
        assert ch._build_embed(_req(ApprovalStatus.DENIED))["color"] == 15158332

    def test_no_reason_no_field(self):
        ch = DiscordChannel("https://discord.com/api/webhooks/x")
        embed = ch._build_embed(_req(reason=""))
        names = [f["name"] for f in embed["fields"]]
        assert "Reason" not in names

    def test_args_truncated(self):
        ch = DiscordChannel("https://discord.com/api/webhooks/x")
        embed = ch._build_embed(_req(args={"d": "y" * 2000}))
        args_field = next(f for f in embed["fields"] if f["name"] == "Args")
        assert "..." in args_field["value"]


class TestEmailChannel:
    def test_payload_structure(self):
        ch = EmailChannel("https://api.example.com/mail", to="ops@x.com")
        captured = {}
        with mock.patch("runtime.approval_channels._post_json",
                        side_effect=lambda u, p, h=None: captured.update(p=p) or True):
            assert ch.send(_req(reason="why", args={"a": 1})) is True
        p = captured["p"]
        assert p["to"] == "ops@x.com"
        assert p["subject"] == "[aiZee] Approval Required: deploy_prod"
        assert "deploy_prod" in p["html"]
        assert "deploy_prod" in p["text"]

    def test_no_to(self):
        ch = EmailChannel("https://api.example.com/mail")
        captured = {}
        with mock.patch("runtime.approval_channels._post_json",
                        side_effect=lambda u, p, h=None: captured.update(p=p) or True):
            ch.send(_req())
        assert "to" not in captured["p"]

    def test_html_escapes_injection(self):
        ch = EmailChannel("https://api.example.com/mail")
        html = ch._build_html(_req(action="<script>alert(1)</script>"))
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_text_body(self):
        ch = EmailChannel("https://api.example.com/mail")
        text = ch._build_text(_req(args={"k": 1}))
        assert "Request ID: abcdef12" in text
        assert "Arguments:" in text


class TestHelpers:
    def test_escape_html(self):
        assert _escape_html('<a href="x">&\'</a>') == \
            "&lt;a href=&quot;x&quot;&gt;&amp;&#39;&lt;/a&gt;"

    def test_iso_timestamp(self):
        ts = _iso_timestamp(1700000000.0)
        assert ts.startswith("2023-") and "+00:00" in ts
