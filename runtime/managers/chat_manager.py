#!/usr/bin/env python3
"""Chat session management for the kernel."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from runtime.chat import ChatSession


class ChatManager:
    """Encapsulates chat session lifecycle."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.default_session = ChatSession(project_root)

    def chat_message(
        self,
        message: str,
        session_id: str | None = None,
        fresh_context: bool = False,
        act_fn: Any = None,
    ) -> dict[str, Any]:
        """Record a chat message and evaluate via policy gates.

        Args:
            message: The user message text.
            session_id: Optional session ID for continuity.
            fresh_context: If True, create a new isolated session.
            act_fn: Callable for action evaluation (typically kernel.act).
        """
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
        result: dict[str, Any] = act_fn(
            "ChatMessage",
            content=message,
            approved=True,
            session_id=session_id,
            fresh_context=fresh_context,
        )
        if result["ok"]:
            reply = f"Acknowledged: {message[:100]}"
            session.add("assistant", reply, metadata={"decision": result["decision"]})
            result["reply"] = reply
        if session_id is not None:
            result["session_id"] = session_id
        return result
