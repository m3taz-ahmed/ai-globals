"""Tests for persistent chat sessions."""

from __future__ import annotations

from pathlib import Path

from runtime.chat import ChatSession
from runtime.kernel import Kernel


def test_chat_session(tmp_path: Path) -> None:
    session = ChatSession(tmp_path, "abc")
    session.add("user", "hello")
    history = session.history()
    assert len(history) == 1
    assert history[0]["role"] == "user"


def test_kernel_chat_message(tmp_path: Path) -> None:
    for sub in ("runtime/policies", "state"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime" / "policies" / "default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-chat\n    condition: \"type == 'ChatMessage'\"\n    action: allow\n"
    )
    k = Kernel(tmp_path, tmp_path)
    result = k.chat_message("hello")
    assert result["ok"] is True
    assert "reply" in result
    assert len(k.chat.history()) == 2


def test_history_empty_when_log_missing(tmp_path: Path) -> None:
    """Cover line 45: history returns empty list when log file doesn't exist."""
    session = ChatSession(tmp_path, "new-session")
    # Don't add any messages — log_path won't exist
    assert session.history() == []


def test_history_skips_blank_lines(tmp_path: Path) -> None:
    """Cover line 50: blank lines in the log are skipped."""
    session = ChatSession(tmp_path, "s1")
    log = tmp_path / "state" / "chat_sessions.jsonl"
    # Write a valid message, then a blank line, then another valid message
    session.add("user", "first")
    with log.open("a", encoding="utf-8") as f:
        f.write("\n")  # blank line
    session.add("user", "second")
    history = session.history()
    assert len(history) == 2
    assert history[0]["content"] == "first"
    assert history[1]["content"] == "second"


def test_history_skips_invalid_json(tmp_path: Path) -> None:
    """Cover lines 53-54: invalid JSON lines are skipped."""
    session = ChatSession(tmp_path, "s1")
    log = tmp_path / "state" / "chat_sessions.jsonl"
    session.add("user", "valid")
    with log.open("a", encoding="utf-8") as f:
        f.write("this is not json\n")
    history = session.history()
    assert len(history) == 1
    assert history[0]["content"] == "valid"


def test_history_respects_limit(tmp_path: Path) -> None:
    """Cover line 58: history stops reading once limit is reached."""
    session = ChatSession(tmp_path, "s1")
    for i in range(10):
        session.add("user", f"msg-{i}")
    history = session.history(limit=3)
    assert len(history) == 3
    # Should be the last 3 messages in order
    assert history[0]["content"] == "msg-7"
    assert history[2]["content"] == "msg-9"
