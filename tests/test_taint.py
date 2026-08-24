"""Tests for runtime.taint — taint label system (from LLMFirewall)."""

from __future__ import annotations

import contextlib

import pytest

from runtime.taint import TaintError, TaintLabel, TaintTracker, classify_source


def test_taint_label_ordering() -> None:
    assert TaintLabel.SYSTEM_TRUSTED < TaintLabel.TOOL_OUTPUT
    assert TaintLabel.TOOL_OUTPUT < TaintLabel.RAG_UNTRUSTED
    assert TaintLabel.RAG_UNTRUSTED < TaintLabel.USER_UNTRUSTED
    assert TaintLabel.USER_UNTRUSTED < TaintLabel.SECRET


def test_can_flow_trusted_to_untrusted() -> None:
    tracker = TaintTracker()
    tracker.label("sys", TaintLabel.SYSTEM_TRUSTED)
    tracker.label("user", TaintLabel.USER_UNTRUSTED)
    assert tracker.can_flow("sys", "user") is True  # trusted can flow to untrusted


def test_cannot_flow_untrusted_to_trusted() -> None:
    tracker = TaintTracker()
    tracker.label("sys", TaintLabel.SYSTEM_TRUSTED)
    tracker.label("user", TaintLabel.USER_UNTRUSTED)
    assert tracker.can_flow("user", "sys") is False  # no-write-down


def test_check_flow_raises_violation() -> None:
    tracker = TaintTracker()
    tracker.label("sys", TaintLabel.SYSTEM_TRUSTED)
    tracker.label("rag", TaintLabel.RAG_UNTRUSTED)
    with pytest.raises(TaintError):
        tracker.check_flow("rag", "sys")


def test_check_flow_allows_legal_flow() -> None:
    tracker = TaintTracker()
    tracker.label("sys", TaintLabel.SYSTEM_TRUSTED)
    tracker.label("user", TaintLabel.USER_UNTRUSTED)
    tracker.check_flow("sys", "user")  # should not raise


def test_sanitize_downgrades_label() -> None:
    tracker = TaintTracker()
    tracker.label("rag", TaintLabel.RAG_UNTRUSTED)
    assert tracker.sanitize("rag", target=TaintLabel.SYSTEM_TRUSTED) is True
    assert tracker.get_label("rag") is TaintLabel.SYSTEM_TRUSTED


def test_sanitize_secret_fails() -> None:
    tracker = TaintTracker()
    tracker.label("key", TaintLabel.SECRET)
    assert tracker.sanitize("key", target=TaintLabel.SYSTEM_TRUSTED) is False
    assert tracker.get_label("key") is TaintLabel.SECRET


def test_merge_takes_highest_label() -> None:
    tracker = TaintTracker()
    tracker.label("sys", TaintLabel.SYSTEM_TRUSTED)
    tracker.label("user", TaintLabel.USER_UNTRUSTED)
    result = tracker.merge(["sys", "user"], "combined")
    assert result is TaintLabel.USER_UNTRUSTED
    assert tracker.get_label("combined") is TaintLabel.USER_UNTRUSTED


def test_redact_removes_entry() -> None:
    tracker = TaintTracker()
    tracker.label("key", TaintLabel.SECRET)
    assert tracker.redact("key") is True
    assert tracker.get_label("key") is None


def test_violations_recorded() -> None:
    tracker = TaintTracker()
    tracker.label("sys", TaintLabel.SYSTEM_TRUSTED)
    tracker.label("user", TaintLabel.USER_UNTRUSTED)
    with contextlib.suppress(TaintError):
        tracker.check_flow("user", "sys")
    assert len(tracker.violations) == 1
    assert tracker.violations[0]["source_label"] == "USER_UNTRUSTED"


def test_classify_source_user() -> None:
    assert classify_source("user") is TaintLabel.USER_UNTRUSTED
    assert classify_source("user_input") is TaintLabel.USER_UNTRUSTED


def test_classify_source_system() -> None:
    assert classify_source("system") is TaintLabel.SYSTEM_TRUSTED
    assert classify_source("guardrail") is TaintLabel.SYSTEM_TRUSTED


def test_classify_source_rag() -> None:
    assert classify_source("rag") is TaintLabel.RAG_UNTRUSTED
    assert classify_source("retrieval") is TaintLabel.RAG_UNTRUSTED


def test_classify_source_tool() -> None:
    assert classify_source("tool") is TaintLabel.TOOL_OUTPUT
    assert classify_source("mcp:search") is TaintLabel.TOOL_OUTPUT


def test_classify_source_secret() -> None:
    assert classify_source("secret") is TaintLabel.SECRET
    assert classify_source("api_key") is TaintLabel.SECRET


def test_classify_source_default_untrusted() -> None:
    assert classify_source("unknown") is TaintLabel.USER_UNTRUSTED


def test_snapshot() -> None:
    tracker = TaintTracker()
    tracker.label("sys", TaintLabel.SYSTEM_TRUSTED)
    tracker.label("user", TaintLabel.USER_UNTRUSTED)
    snap = tracker.snapshot()
    assert "sys" in snap
    assert snap["sys"]["label"] == "SYSTEM_TRUSTED"
    assert snap["user"]["label"] == "USER_UNTRUSTED"


def test_clear() -> None:
    tracker = TaintTracker()
    tracker.label("sys", TaintLabel.SYSTEM_TRUSTED)
    tracker.clear()
    assert tracker.get_label("sys") is None
    assert len(tracker.violations) == 0
