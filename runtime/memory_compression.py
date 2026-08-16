#!/usr/bin/env python3
"""Three-zone memory compression for LLM context (from open-code-review).

Manages context window by partitioning messages into:
- Frozen zone: First 2 messages (system + initial user) — kept intact
- Compress zone: Middle messages — summarized into one message
- Active zone: K most recent complete rounds — kept intact

Thresholds:
- 60% of max tokens: async background compression
- 80% of max tokens: immediate sync compression

Usage::

    from runtime.memory_compression import MemoryCompressor

    compressor = MemoryCompressor(max_tokens=8000)
    result = compressor.partition(messages)
    print(f"Frozen: {len(result.frozen)}, Compress: {len(result.compress)}, Active: {len(result.active)}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PartitionResult:
    """Result of partitioning messages into three zones."""

    frozen: list[dict[str, Any]] = field(default_factory=list)
    compress: list[dict[str, Any]] = field(default_factory=list)
    active: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class MemoryCompressor:
    """Three-zone memory compression (from open-code-review).

    Prevents context overflow while maintaining responsiveness.
    """

    max_tokens: int = 8000
    token_soft_threshold: float = 0.60   # async compression
    token_warning_threshold: float = 0.80  # sync compression
    frozen_zone_size: int = 2  # First N messages are frozen
    active_zone_rounds: int = 3  # K most recent rounds kept intact

    @property
    def soft_limit(self) -> int:
        return int(self.max_tokens * self.token_soft_threshold)

    @property
    def warning_limit(self) -> int:
        return int(self.max_tokens * self.token_warning_threshold)

    def should_compress_async(self, token_count: int) -> bool:
        """Check if async background compression should be triggered."""
        return token_count >= self.soft_limit

    def should_compress_sync(self, token_count: int) -> bool:
        """Check if immediate sync compression is needed."""
        return token_count >= self.warning_limit

    def partition(
        self,
        messages: list[dict[str, Any]],
        token_estimate: int | None = None,
    ) -> PartitionResult:
        """Partition messages into frozen, compress, and active zones."""
        if len(messages) <= self.frozen_zone_size + self.active_zone_rounds:
            # Not enough messages to compress
            return PartitionResult(
                frozen=messages[:self.frozen_zone_size],
                compress=[],
                active=messages[self.frozen_zone_size:],
            )
        frozen = messages[:self.frozen_zone_size]
        active = messages[-(self.active_zone_rounds * 2):]  # K rounds = K*2 messages
        compress = messages[self.frozen_zone_size:-len(active)]
        return PartitionResult(frozen=frozen, compress=compress, active=active)

    def estimate_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Rough token estimate: ~4 chars per token."""
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        return total_chars // 4

    def compress_messages(
        self,
        messages: list[dict[str, Any]],
        summary: str = "",
    ) -> list[dict[str, Any]]:
        """Replace compress zone with a single summary message."""
        if not messages:
            return []
        result = self.partition(messages)
        compressed: list[dict[str, Any]] = list(result.frozen)
        if result.compress and summary:
            compressed.append({"role": "user", "content": f"[Summary] {summary}"})
        compressed.extend(result.active)
        return compressed


if __name__ == "__main__":
    compressor = MemoryCompressor(max_tokens=1000)
    msgs = [{"role": "user", "content": f"Message {i}"} for i in range(20)]
    result = compressor.partition(msgs)
    print(f"Frozen: {len(result.frozen)}, Compress: {len(result.compress)}, Active: {len(result.active)}")
