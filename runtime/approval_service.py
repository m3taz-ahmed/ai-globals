#!/usr/bin/env python3
"""Persistent approval service with multi-channel notifications.

Inspired by Preloop's ``ApprovalService``: approval requests are
persisted to SQLite (via the existing MemoryStore abstraction), notified
through pluggable channels (console, webhook, Slack), and can be polled
asynchronously instead of blocking the caller.

This sits *on top of* ``runtime/approval_cache.py`` (which remains the
fast in-memory cache for already-approved actions). The service handles
the *request* lifecycle; the cache handles *replay suppression*.

Usage::

    from runtime.approval_service import ApprovalService, ConsoleChannel
    svc = ApprovalService(store=MemoryStore(...), channels=[ConsoleChannel()])
    req = svc.create_request("deploy", {"env": "prod"}, reason="production deploy")
    svc.notify(req)  # sends to all channels
    # ... agent polls ...
    if svc.is_approved(req.id):
        svc.mark_resolved(req.id, approved=True)
"""

from __future__ import annotations

import ipaddress
import json
import logging
import socket
import threading
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from runtime.storage_backend import StorageBackend as _StorageBackend

_logger = logging.getLogger(__name__)


def _is_private_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True if the IP is private, loopback, or link-local (SSRF guard)."""
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _validate_webhook_url(url: str) -> bool:
    """Validate a webhook URL to prevent SSRF attacks (B5).

    1. Rejects non-HTTP(S) schemes (file://, gopher://, ftp://, etc.).
    2. Resolves the hostname to an IP via ``socket.getaddrinfo``.
    3. Rejects private/loopback/link-local IP destinations.
    Returns True if safe, False otherwise.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except (ValueError, TypeError):
        return False
    if parsed.scheme not in ("http", "https"):
        _logger.warning("Webhook URL rejected: non-HTTP(S) scheme %r", parsed.scheme)
        return False
    hostname = parsed.hostname
    if not hostname:
        _logger.warning("Webhook URL rejected: no hostname in %r", url)
        return False
    # If the hostname is already an IP literal, validate directly.
    try:
        ip = ipaddress.ip_address(hostname)
        if _is_private_ip(ip):
            _logger.warning("Webhook URL rejected: private/loopback IP %s", ip)
            return False
        return True
    except ValueError:
        pass  # Not an IP literal — proceed to DNS resolution.
    # Resolve hostname to IP addresses; reject if any resolution fails or is private.
    try:
        infos = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, socket.herror, OSError) as exc:
        _logger.warning("Webhook URL rejected: DNS resolution failed for %r: %s", hostname, exc)
        return False
    for _family, _stype, _proto, _canon, sockaddr in infos:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if _is_private_ip(ip):
            _logger.warning("Webhook URL rejected: hostname %r resolves to private IP %s", hostname, ip)
            return False
    return True


class _SsrfSafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validate every redirect target (SSRF guard for urlopen's follow)."""

    def redirect_request(  # type: ignore[no-untyped-def]
        self, req, fp, code, msg, headers, newurl,
    ):
        target = urllib.parse.urljoin(req.full_url, newurl)
        if not _validate_webhook_url(target):
            raise urllib.error.HTTPError(
                req.full_url, code, f"redirect to {target!r} blocked by SSRF guard", headers, fp,
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class ApprovalStatus(str, Enum):
    """Lifecycle of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class ApprovalRequest:
    """A single approval request."""

    id: str
    action: str
    args: dict[str, Any]
    reason: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    resolved_at: float | None = None
    resolved_by: str | None = None
    expires_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalRequest:
        data = dict(data)
        if isinstance(data.get("status"), str):
            data["status"] = ApprovalStatus(data["status"])
        return cls(**data)


class NotificationChannel:
    """Base class for approval notification channels."""

    name: str = "base"

    def send(self, request: ApprovalRequest) -> bool:
        """Send a notification. Returns True on success."""
        raise NotImplementedError


class ConsoleChannel(NotificationChannel):
    """Prints approval requests to the console (default)."""

    name = "console"

    def send(self, request: ApprovalRequest) -> bool:
        print(
            f"[APPROVAL REQUIRED] {request.action} — {request.reason} "
            f"(id={request.id[:8]})"
        )
        return True


class WebhookChannel(NotificationChannel):
    """POSTs approval requests to a webhook URL."""

    name = "webhook"

    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}

    def send(self, request: ApprovalRequest) -> bool:
        if not _validate_webhook_url(self.url):
            _logger.warning(
                "Webhook notification skipped: URL failed SSRF validation %r", self.url
            )
            return False
        payload = json.dumps(request.to_dict()).encode("utf-8")
        req = urllib.request.Request(self.url, data=payload, headers=self.headers, method="POST")
        try:
            opener = urllib.request.build_opener(_SsrfSafeRedirectHandler())
            opener.open(req, timeout=5)
            return True
        except Exception as exc:
            _logger.debug("webhook notification failed: %s", exc, exc_info=True)
            return False


class ApprovalService:
    """Persistent approval request lifecycle manager.

    Args:
        store: Optional MemoryStore for persistence. If None, requests are
            kept in-memory only (useful for tests).
        channels: Notification channels to invoke on ``notify``.
        default_ttl: Default expiry in seconds (None = no expiry).
    """

    def __init__(
        self,
        store: _StorageBackend[str, str] | None = None,
        channels: list[NotificationChannel] | None = None,
        default_ttl: float | None = None,
    ) -> None:
        self._store = store
        self._channels = channels or [ConsoleChannel()]
        self.default_ttl = default_ttl
        self._lock = threading.RLock()
        self._cache: dict[str, ApprovalRequest] = {}

    def create_request(
        self,
        action: str,
        args: dict[str, Any],
        reason: str = "",
        ttl: float | None = None,
        **metadata: Any,
    ) -> ApprovalRequest:
        """Create a new pending approval request."""
        effective_ttl = ttl if ttl is not None else self.default_ttl
        req = ApprovalRequest(
            id=uuid.uuid4().hex,
            action=action,
            args=args,
            reason=reason,
            expires_at=(time.time() + effective_ttl) if effective_ttl else None,
            metadata=metadata,
        )
        with self._lock:
            self._cache[req.id] = req
            self._persist(req)
        return req

    def notify(self, request: ApprovalRequest) -> list[str]:
        """Send the request to all channels. Returns list of channel names that succeeded."""
        succeeded: list[str] = []
        for ch in self._channels:
            try:
                if ch.send(request):
                    succeeded.append(ch.name)
            except Exception as exc:
                _logger.debug("approval channel %s failed: %s", ch.name, exc, exc_info=True)
                continue
        return succeeded

    def create_and_notify(
        self,
        action: str,
        args: dict[str, Any],
        reason: str = "",
        ttl: float | None = None,
        **metadata: Any,
    ) -> ApprovalRequest:
        """Convenience: create + notify in one call."""
        req = self.create_request(action, args, reason, ttl, **metadata)
        self.notify(req)
        return req

    def is_approved(self, request_id: str) -> bool:
        """Check if a request is approved (polling-friendly)."""
        req = self._get(request_id)
        if req is None:
            return False
        if req.expires_at and time.time() > req.expires_at:
            self._update_status(req, ApprovalStatus.EXPIRED)
            return False
        return req.status is ApprovalStatus.APPROVED

    def is_pending(self, request_id: str) -> bool:
        req = self._get(request_id)
        return req is not None and req.status is ApprovalStatus.PENDING

    def mark_resolved(
        self,
        request_id: str,
        approved: bool,
        resolved_by: str | None = None,
    ) -> ApprovalRequest | None:
        """Resolve a pending request as approved or denied."""
        req = self._get(request_id)
        if req is None or req.status is not ApprovalStatus.PENDING:
            return None
        self._update_status(
            req,
            ApprovalStatus.APPROVED if approved else ApprovalStatus.DENIED,
            resolved_by=resolved_by,
        )
        return req

    def cancel(self, request_id: str) -> ApprovalRequest | None:
        """Cancel a PENDING request. Non-pending requests cannot be cancelled."""
        req = self._get(request_id)
        if req is None or req.status is not ApprovalStatus.PENDING:
            return None
        self._update_status(req, ApprovalStatus.CANCELLED)
        return req

    def list_pending(self) -> list[ApprovalRequest]:
        """List all pending requests."""
        with self._lock:
            return [r for r in self._cache.values() if r.status is ApprovalStatus.PENDING]

    def list_all(self) -> list[ApprovalRequest]:
        with self._lock:
            return list(self._cache.values())

    # --- internals ---

    def _get(self, request_id: str) -> ApprovalRequest | None:
        with self._lock:
            if request_id in self._cache:
                return self._cache[request_id]
            if self._store is not None:
                row = self._store.get(f"approval:{request_id}")
                if row and isinstance(row, str):
                    req = ApprovalRequest.from_dict(json.loads(row))
                    self._cache[request_id] = req
                    return req
            return None

    def _persist(self, req: ApprovalRequest) -> None:
        if self._store is None:
            return
        self._store.put(f"approval:{req.id}", json.dumps(req.to_dict()))

    def _update_status(
        self,
        req: ApprovalRequest,
        status: ApprovalStatus,
        resolved_by: str | None = None,
    ) -> None:
        with self._lock:
            req.status = status
            req.resolved_at = time.time()
            if resolved_by:
                req.resolved_by = resolved_by
            self._persist(req)
