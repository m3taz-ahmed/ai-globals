"""Persistent chat sessions for AI Global OS."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ChatMessage:
    timestamp: str
    session_id: str
    role: str
    content: str
    metadata: dict[str, Any]


class ChatSession:
    """Append-only chat log per session."""

    def __init__(self, project_root: Path, session_id: str | None = None) -> None:
        self.project_root = project_root
        self.session_id = session_id or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        self.log_path = project_root / "state" / "chat_sessions.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> ChatMessage:
        msg = ChatMessage(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=self.session_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(msg), default=str) + "\n")
        return msg

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        if not self.log_path.exists():
            return messages
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in reversed(f.readlines()):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if data.get("session_id") == self.session_id:
                    messages.append(data)
                    if len(messages) >= limit:
                        break
        return list(reversed(messages))
