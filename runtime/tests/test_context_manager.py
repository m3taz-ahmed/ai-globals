"""Tests for runtime/context_manager.py."""

from __future__ import annotations

import pytest

from runtime.context_manager import ContextManager, Message, Role


def _msg(role: Role, content: str, group: str | None = None) -> Message:
    return Message(role=role, content=content, group_id=group)


class TestContextManager:
    def test_no_trim_when_under_budget(self):
        cm = ContextManager(max_tokens=10000)
        msgs = [_msg(Role.USER, "hi"), _msg(Role.ASSISTANT, "hello")]
        assert cm.trim(msgs) == msgs

    def test_system_preserved(self):
        cm = ContextManager(max_tokens=100, recent_window=1)
        msgs = [
            _msg(Role.SYSTEM, "you are helpful " * 20),
            _msg(Role.USER, "question " * 20),
            _msg(Role.ASSISTANT, "answer " * 20),
        ]
        trimmed = cm.trim(msgs)
        assert trimmed[0].role is Role.SYSTEM

    def test_recent_window_preserved(self):
        cm = ContextManager(max_tokens=100, recent_window=2)
        msgs = [
            _msg(Role.USER, "old " * 50),
            _msg(Role.ASSISTANT, "old reply " * 50),
            _msg(Role.USER, "recent question"),
            _msg(Role.ASSISTANT, "recent answer"),
        ]
        trimmed = cm.trim(msgs)
        # Last 2 messages should be intact.
        assert trimmed[-1].content == "recent answer"
        assert trimmed[-2].content == "recent question"

    def test_atomic_group_not_split(self):
        cm = ContextManager(max_tokens=120, recent_window=2)
        msgs = [
            _msg(Role.USER, "q1 " * 30),
            _msg(Role.ASSISTANT, "a1 " * 30, group="g1"),
            _msg(Role.TOOL, "tool1 " * 30, group="g1"),
            _msg(Role.USER, "q2 " * 30),
            _msg(Role.ASSISTANT, "a2 " * 30, group="g2"),
            _msg(Role.TOOL, "tool2 " * 30, group="g2"),
        ]
        trimmed = cm.trim(msgs)
        # Verify no group is split: if a tool message is present, its assistant is too.
        group_msgs = [m for m in trimmed if m.group_id is not None]
        groups_present = {m.group_id for m in group_msgs}
        for gid in groups_present:
            roles = {m.role for m in group_msgs if m.group_id == gid}
            assert Role.TOOL not in roles or Role.ASSISTANT in roles

    def test_compresses_middle(self):
        cm = ContextManager(max_tokens=100, recent_window=1)
        msgs = [
            _msg(Role.USER, "long message " * 20),
            _msg(Role.ASSISTANT, "long reply " * 20),
            _msg(Role.USER, "recent"),
        ]
        trimmed = cm.trim(msgs)
        assert cm.estimate_tokens(trimmed) <= cm.max_tokens

    def test_estimate_tokens(self):
        cm = ContextManager()
        assert cm.estimate_tokens([_msg(Role.USER, "x" * 40)]) == 10

    def test_invalid_max_tokens(self):
        with pytest.raises(ValueError):
            ContextManager(max_tokens=10)

    def test_invalid_recent_window(self):
        with pytest.raises(ValueError):
            ContextManager(recent_window=0)

    def test_invalid_compression_ratio(self):
        with pytest.raises(ValueError):
            ContextManager(compression_ratio=0)

    def test_empty_messages(self):
        cm = ContextManager()
        assert cm.trim([]) == []

    def test_compress_with_llm(self):
        from runtime.context_manager import compress_with_llm

        def fake_llm(prompt: str) -> str:
            return "summary"
        result = compress_with_llm([_msg(Role.USER, "hello")], fake_llm)
        assert result == "summary"
