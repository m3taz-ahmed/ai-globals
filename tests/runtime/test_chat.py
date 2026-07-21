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
