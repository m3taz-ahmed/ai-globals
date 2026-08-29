"""Social post queue with per-channel normalization and X cost gate.

A robust scheduler that truncates posts to each channel's character limit
and enforces X (Twitter) cost-gate policy (the 2026 paid-posting model at
~$0.015/post, 2.7.6). Raises ``ValidationError`` when a post exceeds the
free X allowance or an unknown channel is used.
"""

from __future__ import annotations

from dataclasses import dataclass

from runtime.schemas import ValidationError

DEFAULT_CHAR_LIMITS: dict[str, int] = {
    "x": 280,
    "facebook": 63206,
    "instagram": 2200,
    "linkedin": 3000,
    "youtube": 5000,
}

X_FREE_MONTHLY_LIMIT = 0  # X is paid-only from 2026; no free posts.


@dataclass
class QueuedPost:
    """A normalized post awaiting publish."""

    channel: str
    text: str
    original_length: int


class PostQueue:
    """Queues normalized social posts with channel-aware limits."""

    def __init__(
        self,
        char_limits: dict[str, int] | None = None,
        x_free_monthly_limit: int = X_FREE_MONTHLY_LIMIT,
    ) -> None:
        self._limits = dict(char_limits or DEFAULT_CHAR_LIMITS)
        self._x_limit = x_free_monthly_limit
        self._queue: list[QueuedPost] = []
        self._x_count = 0

    def enqueue(self, channel: str, text: str) -> QueuedPost:
        """Normalize and queue a post for ``channel``.

        Truncates ``text`` to the channel's character limit. For ``x``,
        enforces the free monthly allowance and raises ``ValidationError``
        if exceeded (cost gate).
        """
        if channel not in self._limits:
            raise ValidationError(
                "unknown channel", context={"channel": channel}
            )
        if not isinstance(text, str):
            raise ValidationError(
                "text must be a string", context={"channel": channel}
            )

        limit = self._limits[channel]
        normalized = text[:limit]
        if channel == "x":
            self._x_count += 1
            if self._x_count > self._x_limit:
                raise ValidationError(
                    "X free-post allowance exceeded; paid posting required",
                    context={
                        "used": self._x_count,
                        "limit": self._x_limit,
                    },
                )

        post = QueuedPost(
            channel=channel,
            text=normalized,
            original_length=len(text),
        )
        self._queue.append(post)
        return post

    def pending(self) -> list[QueuedPost]:
        """Return queued posts (oldest first)."""
        return list(self._queue)

    def pop(self) -> QueuedPost | None:
        """Remove and return the oldest queued post, if any."""
        if not self._queue:
            return None
        return self._queue.pop(0)
