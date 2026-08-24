"""Tests for runtime/managers/chat_manager.py — ChatManager lifecycle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runtime.chat import ChatSession
from runtime.managers.chat_manager import ChatManager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_root(tmp_path: Path) -> Path:
    """Minimal aiZee root with a state/ dir for chat session logs."""
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _ok_act_fn(
    action: str,
    *,
    content: str = "",
    approved: bool = False,
    session_id: str | None = None,
    fresh_context: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """A stand-in for Kernel.act that always succeeds."""
    return {
        "ok": True,
        "decision": {"decision": "allow", "reason": "test"},
        "action": action,
        "args": {"content": content},
    }


def _deny_act_fn(
    action: str,
    *,
    content: str = "",
    approved: bool = False,
    session_id: str | None = None,
    fresh_context: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """A stand-in for Kernel.act that always denies."""
    return {
        "ok": False,
        "decision": {"decision": "deny", "reason": "blocked"},
        "action": action,
        "args": {"content": content},
        "error": "blocked by policy",
    }


# ---------------------------------------------------------------------------
# Chat session creation
# ---------------------------------------------------------------------------


class TestChatSessionCreation:
    """ChatManager initialises and creates sessions correctly."""

    def test_default_session_created_on_init(self, tmp_root: Path) -> None:
        """ChatManager.__init__ creates a default ChatSession."""
        cm = ChatManager(tmp_root)
        assert cm.default_session is not None
        assert isinstance(cm.default_session, ChatSession)
        assert cm.default_session.project_root == tmp_root

    def test_project_root_stored(self, tmp_root: Path) -> None:
        """ChatManager stores the project root."""
        cm = ChatManager(tmp_root)
        assert cm.project_root == tmp_root

    def test_fresh_context_generates_session_id(self, tmp_root: Path) -> None:
        """fresh_context=True without session_id generates a new UUID."""
        cm = ChatManager(tmp_root)
        result = cm.chat_message("hello", fresh_context=True, act_fn=_ok_act_fn)
        assert result["ok"]
        assert "session_id" in result
        assert result["session_id"] is not None
        # Generated session_id should differ from the default session
        assert result["session_id"] != cm.default_session.session_id

    def test_fresh_context_with_explicit_session_id(self, tmp_root: Path) -> None:
        """fresh_context=True with an explicit session_id uses that ID."""
        cm = ChatManager(tmp_root)
        result = cm.chat_message(
            "hello", session_id="custom-123", fresh_context=True, act_fn=_ok_act_fn
        )
        assert result["ok"]
        assert result["session_id"] == "custom-123"


# ---------------------------------------------------------------------------
# Message sending / receiving
# ---------------------------------------------------------------------------


class TestMessageSending:
    """chat_message records user + assistant turns and returns a reply."""

    def test_successful_message_returns_reply(self, tmp_root: Path) -> None:
        """When act_fn succeeds, a reply is generated and returned."""
        cm = ChatManager(tmp_root)
        result = cm.chat_message("hello world", act_fn=_ok_act_fn)
        assert result["ok"]
        assert "reply" in result
        assert result["reply"].startswith("[local] ")

    def test_offline_fallback_is_explicit(self, tmp_root: Path) -> None:
        """Arbitrary (non-intent) messages get an honest offline reply."""
        cm = ChatManager(tmp_root)
        long_msg = "x" * 250
        result = cm.chat_message(long_msg, act_fn=_ok_act_fn)
        assert result["ok"]
        assert "No LLM backend configured" in result["reply"]

    def test_status_intent_answers_from_context(self, tmp_root: Path) -> None:
        """The 'status' intent answers from the injected context provider."""
        from runtime.local_responder import LocalResponder

        responder = LocalResponder(context_provider=lambda: {
            "version": "9.9.9", "workflows": ["a"], "rules": [], "personas": [], "skills": [],
        })
        cm = ChatManager(tmp_root, responder=responder)
        result = cm.chat_message("what is the status?", act_fn=_ok_act_fn)
        assert result["ok"]
        assert "v9.9.9" in result["reply"]
        assert "1 workflows" in result["reply"]

    def test_help_intent_lists_supported_intents(self, tmp_root: Path) -> None:
        cm = ChatManager(tmp_root)
        result = cm.chat_message("help", act_fn=_ok_act_fn)
        assert result["ok"]
        assert "status" in result["reply"]
        assert "budgets" in result["reply"]

    def test_user_message_recorded_in_session(self, tmp_root: Path) -> None:
        """The user message is added to the session history."""
        cm = ChatManager(tmp_root)
        cm.chat_message("test user msg", act_fn=_ok_act_fn)
        history = cm.default_session.history()
        assert len(history) >= 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "test user msg"

    def test_assistant_reply_recorded_in_session(self, tmp_root: Path) -> None:
        """The assistant reply is added to the session history with metadata."""
        cm = ChatManager(tmp_root)
        cm.chat_message("test msg", act_fn=_ok_act_fn)
        history = cm.default_session.history()
        assistant_msgs = [m for m in history if m["role"] == "assistant"]
        assert len(assistant_msgs) == 1
        assert "decision" in assistant_msgs[0]["metadata"]

    def test_denied_message_does_not_add_reply(self, tmp_root: Path) -> None:
        """When act_fn denies, no reply is generated or recorded."""
        cm = ChatManager(tmp_root)
        result = cm.chat_message("blocked msg", act_fn=_deny_act_fn)
        assert not result["ok"]
        assert "reply" not in result
        # Only the user message should be in history, no assistant reply
        history = cm.default_session.history()
        roles = [m["role"] for m in history]
        assert "user" in roles
        assert "assistant" not in roles

    def test_act_fn_receives_correct_arguments(self, tmp_root: Path) -> None:
        """act_fn is called with ChatMessage action and approved=True."""
        received: dict[str, Any] = {}

        def capturing_act(action: str, **kwargs: Any) -> dict[str, Any]:
            received["action"] = action
            received.update(kwargs)
            return {"ok": True, "decision": {"decision": "allow"}}

        cm = ChatManager(tmp_root)
        cm.chat_message("capture me", act_fn=capturing_act)
        assert received["action"] == "ChatMessage"
        assert received["content"] == "capture me"
        assert received["approved"] is True


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------


class TestSessionPersistence:
    """Messages are persisted to the JSONL log file on disk."""

    def test_log_file_created_on_message(self, tmp_root: Path) -> None:
        """Sending a message creates the chat_sessions.jsonl log file."""
        cm = ChatManager(tmp_root)
        log_path = tmp_root / "state" / "chat_sessions.jsonl"
        assert not log_path.exists()
        cm.chat_message("persist me", act_fn=_ok_act_fn)
        assert log_path.exists()

    def test_messages_appended_to_log(self, tmp_root: Path) -> None:
        """Multiple messages are appended as separate JSONL lines."""
        cm = ChatManager(tmp_root)
        cm.chat_message("first", act_fn=_ok_act_fn)
        cm.chat_message("second", act_fn=_ok_act_fn)
        log_path = tmp_root / "state" / "chat_sessions.jsonl"
        lines = [line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        # 2 user + 2 assistant = 4 lines
        assert len(lines) == 4

    def test_persisted_messages_are_valid_json(self, tmp_root: Path) -> None:
        """Each line in the log file is valid JSON with expected fields."""
        cm = ChatManager(tmp_root)
        cm.chat_message("json check", act_fn=_ok_act_fn)
        log_path = tmp_root / "state" / "chat_sessions.jsonl"
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            assert "timestamp" in data
            assert "session_id" in data
            assert "role" in data
            assert "content" in data
            assert "metadata" in data

    def test_fresh_context_session_persisted_separately(self, tmp_root: Path) -> None:
        """A fresh-context session writes to the same log with its own session_id."""
        cm = ChatManager(tmp_root)
        result = cm.chat_message("fresh msg", fresh_context=True, act_fn=_ok_act_fn)
        session = ChatSession(tmp_root, result["session_id"])
        history = session.history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "fresh msg"


# ---------------------------------------------------------------------------
# Session retrieval
# ---------------------------------------------------------------------------


class TestSessionRetrieval:
    """Session history can be retrieved by session_id."""

    def test_history_returns_only_session_messages(self, tmp_root: Path) -> None:
        """history() filters messages by session_id."""
        cm = ChatManager(tmp_root)
        # Send to default session
        cm.chat_message("default msg", act_fn=_ok_act_fn)
        # Send to a fresh session
        result = cm.chat_message("fresh msg", fresh_context=True, act_fn=_ok_act_fn)

        default_history = cm.default_session.history()
        fresh_session = ChatSession(tmp_root, result["session_id"])
        fresh_history = fresh_session.history()

        # Default session should not contain fresh session messages
        default_contents = [m["content"] for m in default_history]
        assert "default msg" in default_contents
        assert "fresh msg" not in default_contents

        # Fresh session should not contain default session messages
        fresh_contents = [m["content"] for m in fresh_history]
        assert "fresh msg" in fresh_contents
        assert "default msg" not in fresh_contents

    def test_history_respects_limit(self, tmp_root: Path) -> None:
        """history(limit=N) returns at most N messages."""
        cm = ChatManager(tmp_root)
        for i in range(5):
            cm.chat_message(f"msg-{i}", act_fn=_ok_act_fn)
        # 5 user + 5 assistant = 10 messages; limit to 3
        history = cm.default_session.history(limit=3)
        assert len(history) == 3

    def test_history_empty_for_nonexistent_session(self, tmp_root: Path) -> None:
        """A session_id with no messages returns an empty history."""
        cm = ChatManager(tmp_root)
        cm.chat_message("real msg", act_fn=_ok_act_fn)
        other = ChatSession(tmp_root, "nonexistent-session-id")
        assert other.history() == []

    def test_continuity_with_existing_session_id(self, tmp_root: Path) -> None:
        """Providing session_id continues an existing session's log."""
        cm = ChatManager(tmp_root)
        # First message creates the session
        r1 = cm.chat_message(
            "first", session_id="cont-1", fresh_context=True, act_fn=_ok_act_fn
        )
        # Second message continues the same session
        r2 = cm.chat_message("second", session_id="cont-1", act_fn=_ok_act_fn)
        assert r1["session_id"] == "cont-1"
        assert r2["session_id"] == "cont-1"

        session = ChatSession(tmp_root, "cont-1")
        history = session.history()
        # 2 user + 2 assistant = 4
        assert len(history) == 4
        contents = [m["content"] for m in history if m["role"] == "user"]
        assert "first" in contents
        assert "second" in contents


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """ChatManager handles error conditions gracefully."""

    def test_act_fn_none_returns_deny(self, tmp_root: Path) -> None:
        """Calling chat_message without act_fn returns a graceful deny result."""
        cm = ChatManager(tmp_root)
        result = cm.chat_message("no act fn")
        assert not result["ok"]
        assert result["decision"] == "deny"
        assert "act_fn" in result["reason"]

    def test_denied_result_propagates_error(self, tmp_root: Path) -> None:
        """A denied result includes the error from act_fn."""
        cm = ChatManager(tmp_root)
        result = cm.chat_message("denied", act_fn=_deny_act_fn)
        assert not result["ok"]
        assert result["error"] == "blocked by policy"

    def test_session_id_returned_even_on_deny(self, tmp_root: Path) -> None:
        """session_id is returned in the result even when the action is denied."""
        cm = ChatManager(tmp_root)
        result = cm.chat_message(
            "denied", session_id="err-1", fresh_context=True, act_fn=_deny_act_fn
        )
        assert not result["ok"]
        assert result["session_id"] == "err-1"

    def test_empty_message_handled(self, tmp_root: Path) -> None:
        """An empty message string is processed without error."""
        cm = ChatManager(tmp_root)
        result = cm.chat_message("", act_fn=_ok_act_fn)
        assert result["ok"]
        assert result["reply"].startswith("[local] ")

    def test_act_fn_raising_exception_propagates(self, tmp_root: Path) -> None:
        """If act_fn raises, the exception propagates to the caller."""
        cm = ChatManager(tmp_root)

        def exploding_act(action: str, **kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("act_fn exploded")

        with pytest.raises(RuntimeError, match="exploded"):
            cm.chat_message("boom", act_fn=exploding_act)


class TestLocalResponderAllIntents:
    """Cover every LocalResponder intent branch from live context."""

    def _responder(self):
        from runtime.local_responder import LocalResponder

        ctx = {
            "version": "1.0",
            "budgets": ["global", "session"],
            "workflows": [f"wf-{i}" for i in range(7)],
            "rules": ["r1", "r2"],
            "guardian_rules": ["g1"],
            "skills": ["s1", "s2", "s3"],
            "tech_stack": {"laravel": {}, "react": {}},
        }
        return LocalResponder(context_provider=lambda: ctx)

    def test_budget_intent_with_limits(self):
        reply = self._responder().reply("what about budgets?")
        assert "[local]" in reply
        assert "2 active budget scope(s)" in reply
        assert "global" in reply

    def test_budget_intent_without_limits(self):
        from runtime.local_responder import LocalResponder

        r = LocalResponder(context_provider=lambda: {})
        assert "No budget limits" in r.reply("budgets?")

    def test_workflow_intent_truncates_long_lists(self):
        reply = self._responder().reply("run a workflow")
        assert "7 registered workflow(s)" in reply
        assert "+2 more" in reply

    def test_rules_intent_counts_guardian_too(self):
        reply = self._responder().reply("show me the rules")
        assert "2 policy rule(s)" in reply
        assert "1 guardian rule(s)" in reply

    def test_skills_intent(self):
        assert "3 skill(s)" in self._responder().reply("list skills")

    def test_stack_intent_sorted_names(self):
        reply = self._responder().reply("what tech stack?")
        assert "laravel" in reply and "react" in reply

    def test_status_reply_when_provider_fails(self):
        from runtime.local_responder import LocalResponder

        def broken():
            raise RuntimeError("boom")

        r = LocalResponder(context_provider=broken)
        assert "unavailable" in r.reply("status?")

    def test_status_reply_when_no_provider(self):
        from runtime.local_responder import LocalResponder

        assert "Kernel state unavailable" in LocalResponder().reply("status?")
