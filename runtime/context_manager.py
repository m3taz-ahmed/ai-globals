#!/usr/bin/env python3
"""3-level context window manager for long-running sessions.

Inspired by Omnigent's ``context.py``: when a conversation exceeds a
token budget, messages are trimmed in three tiers:

- **Level 1 (preserved):** System prompt, plan, and profile — never trimmed.
- **Level 2 (compressed):** Middle messages are heuristically compressed
  (summarized to a single line each, or dropped if redundant).
- **Level 3 (intact):** The most recent N messages are kept verbatim.

Atomic message groups (assistant + tool_result pairs) are never split,
preventing LLM API validation errors.

This is a pure-data module — no LLM calls. Semantic compression via an
LLM is a separate concern (call ``compress_with_llm`` from outside).

Usage::

    from runtime.context_manager import ContextManager, Message
    cm = ContextManager(max_tokens=8000, recent_window=6)
    trimmed = cm.trim(messages)
    assert cm.estimate_tokens(trimmed) <= 8000
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Role(str, Enum):
    """Message roles in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A single conversation message."""

    role: Role
    content: str
    tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    # Group ID links assistant+tool pairs so they are never split.
    group_id: str | None = None

    def __post_init__(self) -> None:
        if self.tokens == 0:
            self.tokens = _estimate_tokens(self.content)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token, min 1."""
    return max(1, len(text) // 4)


def _is_atomic_group(messages: list[Message], idx: int) -> bool:
    """Check if message at idx is part of an atomic group (assistant+tool)."""
    msg = messages[idx]
    if msg.group_id is None:
        return False
    return any(m.group_id == msg.group_id for j, m in enumerate(messages) if j != idx)


class ContextManager:
    """3-level context trimming for conversation histories.

    Args:
        max_tokens: Target maximum token count after trimming.
        recent_window: Number of most-recent messages to keep verbatim (Level 3).
        compression_ratio: Fraction of tokens to keep per compressed message (Level 2).
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        recent_window: int = 6,
        compression_ratio: float = 0.3,
    ) -> None:
        if max_tokens < 100:
            raise ValueError("max_tokens must be >= 100")
        if recent_window < 1:
            raise ValueError("recent_window must be >= 1")
        if not 0 < compression_ratio <= 1:
            raise ValueError("compression_ratio must be in (0, 1]")
        self.max_tokens = max_tokens
        self.recent_window = recent_window
        self.compression_ratio = compression_ratio

    def estimate_tokens(self, messages: list[Message]) -> int:
        """Total token count of a message list."""
        return sum(m.tokens for m in messages)

    def trim(self, messages: list[Message]) -> list[Message]:
        """Trim messages to fit within max_tokens using 3-level strategy."""
        if self.estimate_tokens(messages) <= self.max_tokens:
            return list(messages)
        # Level 1: preserve system messages.
        system, rest = self._split_system(messages)
        # Level 3: preserve recent window (respecting atomic groups).
        recent, middle = self._split_recent(rest, self.recent_window)
        # Level 2: compress middle until we fit.
        budget = self.max_tokens - self.estimate_tokens(system) - self.estimate_tokens(recent)
        compressed = self._compress_middle(middle, budget)
        return system + compressed + recent

    def _split_system(self, messages: list[Message]) -> tuple[list[Message], list[Message]]:
        """Split into (system messages, rest). System messages are leading."""
        system: list[Message] = []
        rest: list[Message] = []
        seen_non_system = False
        for msg in messages:
            if msg.role is Role.SYSTEM and not seen_non_system:
                system.append(msg)
            else:
                seen_non_system = True
                rest.append(msg)
        return system, rest

    def _split_recent(
        self, messages: list[Message], window: int
    ) -> tuple[list[Message], list[Message]]:
        """Split into (recent window, middle). Respects atomic groups."""
        if len(messages) <= window:
            return list(messages), []
        # Find a split point that doesn't break an atomic group.
        split = len(messages) - window
        # Walk backward to avoid splitting a group.
        while split > 0 and _is_atomic_group(messages, split - 1) and _is_atomic_group(messages, split):
            if messages[split - 1].group_id == messages[split].group_id:
                split -= 1
            else:
                break
        return list(messages[split:]), list(messages[:split])

    def _compress_middle(self, middle: list[Message], budget: int) -> list[Message]:
        """Compress middle messages to fit within budget."""
        if not middle:
            return []
        if budget <= 0:
            # No budget — keep only a single summary message.
            return [self._summarize_all(middle)]
        compressed: list[Message] = []
        current_tokens = 0
        for msg in middle:
            target = max(1, int(msg.tokens * self.compression_ratio))
            if current_tokens + target > budget and compressed:
                # Stop adding — remaining messages get summarized into the last one.
                compressed[-1] = self._merge(compressed[-1], msg)
                continue
            compressed.append(self._compress_one(msg, target))
            current_tokens += target
        return compressed

    def _compress_one(self, msg: Message, target_tokens: int) -> Message:
        """Compress a single message to approximately target_tokens."""
        if msg.tokens <= target_tokens:
            return msg
        # Heuristic: keep first sentence + last sentence.
        content = msg.content
        sentences = re.split(r"(?<=[.!?])\s+", content)
        if len(sentences) <= 2:
            # Truncate to target chars.
            keep = content[: target_tokens * 4]
            return Message(role=msg.role, content=keep + "…", tokens=target_tokens, group_id=msg.group_id)
        first, last = sentences[0], sentences[-1]
        merged = f"{first} […] {last}"
        return Message(role=msg.role, content=merged, tokens=_estimate_tokens(merged), group_id=msg.group_id)

    def _summarize_all(self, messages: list[Message]) -> Message:
        """Create a single summary message from a list."""
        count = len(messages)
        roles = {m.role.value for m in messages}
        summary = f"[{count} messages compressed: {', '.join(sorted(roles))}]"
        return Message(role=Role.SYSTEM, content=summary, tokens=_estimate_tokens(summary))

    def _merge(self, a: Message, b: Message) -> Message:
        """Merge two messages into one compressed summary."""
        content = f"{a.content} [+1 msg]"
        return Message(role=a.role, content=content, tokens=_estimate_tokens(content))


def compress_with_llm(
    messages: list[Message],
    llm_fn: Callable[[str], str],
) -> str:
    """Semantic compression via an LLM callable.

    Args:
        messages: Messages to compress.
        llm_fn: Callable that takes a prompt string and returns a summary.

    Returns:
        A summary string.
    """
    text = "\n".join(f"{m.role.value}: {m.content}" for m in messages)
    result: str = llm_fn(f"Summarize this conversation concisely:\n{text}")
    return result
