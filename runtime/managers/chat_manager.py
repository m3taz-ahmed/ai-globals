#!/usr/bin/env python3
"""Chat session management for the kernel."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from runtime.chat import ChatSession
from runtime.local_responder import LocalResponder
from runtime.prompt_gate import PromptGate, PromptRisk


class ChatManager:
    """Encapsulates chat session lifecycle.

    Replies are produced by an injected :class:`LocalResponder` (or a
    subclass with an LLM backend). The responder is constructed lazily by
    default so tests can inject doubles.
    """

    def __init__(
        self,
        project_root: Path,
        responder: LocalResponder | None = None,
    ) -> None:
        self.project_root = project_root
        self.default_session = ChatSession(project_root)
        self.prompt_gate = PromptGate()
        self.responder = responder or LocalResponder()

    def chat_message(
        self,
        message: str,
        session_id: str | None = None,
        fresh_context: bool = False,
        act_fn: Callable[..., dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Record a chat message and evaluate via policy gates.

        Args:
            message: The user message text.
            session_id: Optional session ID for continuity.
            fresh_context: If True, create a new isolated session.
            act_fn: Callable for action evaluation (typically kernel.act).
        """
        # Pre-inference prompt safety gate — block before any processing.
        verdict = self.prompt_gate.evaluate(message)
        if verdict.risk is PromptRisk.BLOCKED:
            return {
                "ok": False,
                "decision": "deny",
                "reason": verdict.reason,
                "prompt_risk": verdict.risk.value,
                "matched_patterns": verdict.matched_patterns,
                "score": verdict.score,
            }
        if fresh_context:
            session_id = session_id or uuid.uuid4().hex
            session = ChatSession(self.project_root, session_id)
        else:
            session = ChatSession(self.project_root, session_id) if session_id else self.default_session
        session.add("user", message)
        # Chat messages are user-initiated, so we pass approved=True to skip
        # the ASK prompt (the user already chose to send the message).
        # The policy engine still evaluates the action — if a rule DENIES
        # ChatMessage, it will be blocked. The guardian also evaluates
        # write/exec actions triggered by the chat, but ChatMessage itself
        # is treated as read-only (see _READ_ONLY_ACTIONS in PolicyManager).
        if act_fn is None:
            return {
                "ok": False,
                "decision": "deny",
                "reason": "No action function provided (act_fn is None)",
            }
        result: dict[str, Any] = act_fn(
            "ChatMessage",
            content=message,
            approved=True,
            session_id=session_id,
            fresh_context=fresh_context,
        )
        if result["ok"]:
            reply = self.responder.reply(message)
            session.add("assistant", reply, metadata={"decision": result["decision"]})
            result["reply"] = reply
        if session_id is not None:
            result["session_id"] = session_id
        return result
