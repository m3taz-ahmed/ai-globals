#!/usr/bin/env python3
"""Multi-channel approval notifications: Slack, Discord, Email.

Extends the :class:`~runtime.approval_service.NotificationChannel` base
class from ``runtime/approval_service.py`` with three webhook-based
channels that POST formatted messages to external services.

All channels use ``urllib.request`` (no external HTTP dependencies) and
reuse the SSRF validation from ``approval_service.py`` to prevent
server-side request forgery.

Channels:
* :class:`SlackChannel` — Slack incoming webhook with approve/deny
  buttons (Block Kit).
* :class:`DiscordChannel` — Discord webhook with a rich embed.
* :class:`EmailChannel` — Generic email webhook API (e.g. SendGrid)
  with a JSON payload.

Usage::

    from runtime.approval_channels import SlackChannel, DiscordChannel
    from runtime.approval_service import ApprovalService

    channels = [SlackChannel("https://hooks.slack.com/..."), DiscordChannel("https://discord.com/api/webhooks/...")]
    svc = ApprovalService(channels=channels)
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

from runtime.approval_service import (
    ApprovalRequest,
    NotificationChannel,
    _SsrfSafeRedirectHandler,
    _validate_webhook_url,
)

_logger = logging.getLogger(__name__)

# Default HTTP timeout for webhook calls (seconds).
_HTTP_TIMEOUT: float = 5.0


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> bool:
    """POST a JSON payload to *url* with SSRF-safe handling.

    Returns ``True`` on HTTP 2xx, ``False`` on any failure (network
    error, non-2xx response, or SSRF validation failure).
    """
    if not _validate_webhook_url(url):
        _logger.warning("Webhook URL failed SSRF validation: %r", url)
        return False
    body = json.dumps(payload).encode("utf-8")
    req_headers = headers or {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
    try:
        opener = urllib.request.build_opener(_SsrfSafeRedirectHandler())
        resp = opener.open(req, timeout=_HTTP_TIMEOUT)
        return bool(200 <= resp.status < 300)
    except Exception as exc:
        _logger.debug("webhook POST to %s failed: %s", url, exc, exc_info=True)
        return False


class SlackChannel(NotificationChannel):
    """Slack incoming webhook channel with approve/deny buttons.

    Posts a Block Kit message containing the approval request details
    and interactive buttons for approve/deny actions. The button
    ``value`` fields carry the request ID so the Slack interaction
    handler can route the response back to the approval service.

    Args:
        webhook_url: Slack incoming webhook URL
            (``https://hooks.slack.com/services/...``).
        channel: Optional channel override (``#approvals``). If
            ``None``, the webhook's default channel is used.
    """

    name = "slack"

    def __init__(self, webhook_url: str, channel: str | None = None) -> None:
        self.webhook_url = webhook_url
        self.channel = channel

    def send(self, request: ApprovalRequest) -> bool:
        """POST a Slack Block Kit message with approve/deny buttons."""
        blocks = self._build_blocks(request)
        payload: dict[str, Any] = {"blocks": blocks}
        if self.channel:
            payload["channel"] = self.channel
        return _post_json(self.webhook_url, payload)

    def _build_blocks(self, request: ApprovalRequest) -> list[dict[str, Any]]:
        """Build the Slack Block Kit blocks for the approval message."""
        emoji = self._status_emoji(request.status.value)
        header_text = f"{emoji} Approval Required: {request.action}"
        fields = self._build_fields(request)
        blocks: list[dict[str, Any]] = [
            {"type": "header", "text": {"type": "plain_text", "text": header_text}},
            {"type": "section", "fields": fields},
        ]
        if request.status.value == "pending":
            blocks.append(self._action_buttons(request))
        return blocks

    @staticmethod
    def _status_emoji(status: str) -> str:
        """Return Slack emoji for an approval status."""
        return {"pending": ":hourglass:", "approved": ":white_check_mark:", "denied": ":x:"}.get(status, ":question:")

    @staticmethod
    def _build_fields(request: ApprovalRequest) -> list[dict[str, Any]]:
        """Build the section fields for the Slack message."""
        fields: list[dict[str, Any]] = [
            {"type": "mrkdwn", "text": f"*Request ID:*\n`{request.id[:8]}`"},
            {"type": "mrkdwn", "text": f"*Action:*\n{request.action}"},
            {"type": "mrkdwn", "text": f"*Reason:*\n{request.reason or 'N/A'}"},
            {"type": "mrkdwn", "text": f"*Status:*\n{request.status.value}"},
        ]
        if request.args:
            args_str = json.dumps(request.args, indent=2, default=str)
            if len(args_str) > 800:
                args_str = args_str[:800] + "..."
            fields.append({"type": "mrkdwn", "text": f"*Args:*\n```{args_str}```"})
        return fields

    @staticmethod
    def _action_buttons(request: ApprovalRequest) -> dict[str, Any]:
        """Build approve/deny action buttons block for pending requests."""
        return {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve", "emoji": True},
                    "style": "primary",
                    "value": f"approve:{request.id}",
                    "action_id": f"approve_{request.id[:8]}",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Deny", "emoji": True},
                    "style": "danger",
                    "value": f"deny:{request.id}",
                    "action_id": f"deny_{request.id[:8]}",
                },
            ],
        }

class DiscordChannel(NotificationChannel):
    """Discord webhook channel with a rich embed.

    Posts a Discord message containing an embed with the approval
    request details. Discord webhooks do not support interactive
    buttons natively, so the message includes the request ID for
    manual resolution via the approval service API.

    Args:
        webhook_url: Discord webhook URL
            (``https://discord.com/api/webhooks/...``).
    """

    name = "discord"

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def send(self, request: ApprovalRequest) -> bool:
        """POST a Discord embed message."""
        embed = self._build_embed(request)
        payload: dict[str, Any] = {
            "username": "aiZee Approvals",
            "embeds": [embed],
        }
        return _post_json(self.webhook_url, payload)

    def _build_embed(self, request: ApprovalRequest) -> dict[str, Any]:
        """Build the Discord embed for the approval message."""
        color_map = {"pending": 16776960, "approved": 3066993, "denied": 15158332}
        color = color_map.get(request.status.value, 16776960)
        fields: list[dict[str, Any]] = [
            {"name": "Action", "value": request.action, "inline": True},
            {"name": "Status", "value": request.status.value, "inline": True},
            {"name": "Request ID", "value": f"`{request.id[:8]}`", "inline": False},
        ]
        if request.reason:
            fields.append({"name": "Reason", "value": request.reason, "inline": False})
        if request.args:
            args_str = json.dumps(request.args, indent=2, default=str)
            if len(args_str) > 1000:
                args_str = args_str[:1000] + "..."
            fields.append({"name": "Args", "value": f"```json\n{args_str}```", "inline": False})
        return {
            "title": f"Approval Required: {request.action}",
            "color": color,
            "fields": fields,
            "footer": {"text": "aiZee HITL Approval System"},
            "timestamp": _iso_timestamp(request.created_at),
        }


class EmailChannel(NotificationChannel):
    """Email webhook channel (e.g. SendGrid, Mailgun, custom API).

    Posts a JSON payload to an email-sending webhook API. The payload
    format is generic and compatible with most email API gateways
    that accept ``to``, ``subject``, and ``html`` fields.

    Args:
        webhook_url: Email API webhook URL.
        to: Recipient email address (optional, can be set by the
            webhook's default configuration).
    """

    name = "email"

    def __init__(self, webhook_url: str, to: str | None = None) -> None:
        self.webhook_url = webhook_url
        self.to = to

    def send(self, request: ApprovalRequest) -> bool:
        """POST an email payload to the webhook."""
        subject = f"[aiZee] Approval Required: {request.action}"
        html = self._build_html(request)
        payload: dict[str, Any] = {
            "subject": subject,
            "html": html,
            "text": self._build_text(request),
        }
        if self.to:
            payload["to"] = self.to
        return _post_json(self.webhook_url, payload)

    def _build_html(self, request: ApprovalRequest) -> str:
        """Build the HTML email body for the approval message."""
        args_html = ""
        if request.args:
            args_json = json.dumps(request.args, indent=2, default=str)
            args_html = f"<h3>Arguments</h3><pre>{_escape_html(args_json)}</pre>"
        return (
            f"<h2>Approval Required: {_escape_html(request.action)}</h2>"
            f"<p><strong>Request ID:</strong> <code>{_escape_html(request.id[:8])}</code></p>"
            f"<p><strong>Status:</strong> {_escape_html(request.status.value)}</p>"
            f"<p><strong>Reason:</strong> {_escape_html(request.reason or 'N/A')}</p>"
            f"{args_html}"
            f"<hr><p><em>aiZee HITL Approval System</em></p>"
        )

    def _build_text(self, request: ApprovalRequest) -> str:
        """Build the plain-text email body for the approval message."""
        args_text = ""
        if request.args:
            args_text = f"\n\nArguments:\n{json.dumps(request.args, indent=2, default=str)}"
        return (
            f"Approval Required: {request.action}\n"
            f"Request ID: {request.id[:8]}\n"
            f"Status: {request.status.value}\n"
            f"Reason: {request.reason or 'N/A'}"
            f"{args_text}\n\n-- aiZee HITL Approval System"
        )


def _escape_html(text: str) -> str:
    """Escape HTML special characters to prevent injection in email."""
    escaped = text.replace("&", "&amp;")
    escaped = escaped.replace("<", "&lt;")
    escaped = escaped.replace(">", "&gt;")
    escaped = escaped.replace(chr(34), "&quot;")
    escaped = escaped.replace(chr(39), "&#39;")
    return escaped


def _iso_timestamp(epoch: float) -> str:
    """Convert an epoch timestamp to ISO-8601 string."""
    from datetime import datetime, timezone

    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
