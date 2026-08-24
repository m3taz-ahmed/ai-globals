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

import json
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from runtime.storage_backend import StorageBackend as _StorageBackend

_logger = logging.getLogger(__name__)


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
        import urllib.request

        payload = json.dumps(request.to_dict()).encode("utf-8")
        req = urllib.request.Request(self.url, data=payload, headers=self.headers, method="POST")
        try:
            urllib.request.urlopen(req, timeout=5)
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
        req = ApprovalRequest(
            id=uuid.uuid4().hex,
            action=action,
            args=args,
            reason=reason,
            expires_at=(time.time() + (ttl or self.default_ttl or 0)) if (ttl or self.default_ttl) else None,
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
        req = self._get(request_id)
        if req is None:
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
