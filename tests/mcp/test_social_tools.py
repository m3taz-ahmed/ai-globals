"""Tests for aizee_mcp/tools/social_tools.py MCP tools."""

from __future__ import annotations

import json
from typing import Any

import pytest

from aizee_mcp.tools.social_tools import (  # pyright: ignore[reportMissingImports]
    _resolve_provider,
    normalize_content,
    register_social_tools,
)
from runtime.schemas import ValidationError

pytestmark = pytest.mark.mcp


class _FakeTool:
    def __call__(self, fn: Any | None = None) -> Any:
        if fn is not None:
            _captured_tools[fn.__name__] = fn
            return fn

        def decorator(inner_fn: Any) -> Any:
            _captured_tools[inner_fn.__name__] = inner_fn
            return inner_fn

        return decorator


class _FakeMCP:
    def __init__(self) -> None:
        self.tool = _FakeTool()


_captured_tools: dict[str, Any] = {}


def _get_tool(name: str) -> Any:
    _captured_tools.clear()
    register_social_tools(_FakeMCP())
    return _captured_tools[name]


def _parse(result: str) -> dict[str, Any]:
    return json.loads(result)


class TestNormalizeContent:
    def test_within_limit(self):
        out = normalize_content("x", "short post")
        assert out["truncated"] is False
        assert out["final_length"] == 10

    def test_truncated(self):
        out = normalize_content("x", "y" * 300)
        assert out["truncated"] is True
        assert out["final_length"] == 280

    def test_non_string_content(self):
        out = normalize_content("x", None)
        assert out["content"] == ""

    def test_unknown_network(self):
        with pytest.raises(ValidationError):
            normalize_content("myspace", "hi")

    def test_resolve_provider_bad(self):
        with pytest.raises(ValidationError):
            _resolve_provider("myspace")


class TestSocialSchedule:
    def test_happy(self):
        out = _parse(_get_tool("social_schedule")(network="linkedin", content="hi",
                                                    scheduled_at="2026-10-01T10:00:00Z"))
        assert out["ok"] is True
        assert out["instruction"]["action"] == "schedule"
        assert out["instruction"]["scheduled_at"] == "2026-10-01T10:00:00Z"

    def test_empty_content(self):
        out = _parse(_get_tool("social_schedule")(network="x", content=""))
        assert out["ok"] is False

    def test_bad_datetime(self):
        out = _parse(_get_tool("social_schedule")(network="x", content="hi",
                                                    scheduled_at="tomorrow"))
        assert out["ok"] is False
        assert "ISO-8601" in out["error"]

    def test_oversized_datetime(self):
        out = _parse(_get_tool("social_schedule")(network="x", content="hi",
                                                    scheduled_at="x" * 100))
        assert out["ok"] is False

    def test_bad_network(self):
        out = _parse(_get_tool("social_schedule")(network="myspace", content="hi"))
        assert out["ok"] is False


class TestSocialPublish:
    @pytest.mark.parametrize("net,action", [
        ("x", "tweet"), ("linkedin", "share"), ("instagram", "create_media"),
        ("youtube", "insert_video"), ("tiktok", "post_video"),
    ])
    def test_all_providers(self, net: str, action: str):
        out = _parse(_get_tool("social_publish")(network=net, content="hello"))
        assert out["ok"] is True
        assert out["instruction"]["action"] == action
        assert out["instruction"]["network"] == net

    def test_x_truncates(self):
        out = _parse(_get_tool("social_publish")(network="x", content="y" * 300))
        assert out["instruction"]["truncated"] is True
        assert len(out["instruction"]["content"]) == 280

    def test_youtube_title(self):
        out = _parse(_get_tool("social_publish")(network="youtube", content="vid desc"))
        assert out["instruction"]["title"] == "vid desc"

    def test_empty_content(self):
        out = _parse(_get_tool("social_publish")(network="x", content=""))
        assert out["ok"] is False

    def test_bad_network(self):
        out = _parse(_get_tool("social_publish")(network="myspace", content="hi"))
        assert out["ok"] is False


class TestSocialDraft:
    def test_happy(self):
        out = _parse(_get_tool("social_draft")(network="x", topic="launch",
                                               tone="witty", length_hint="short"))
        assert out["ok"] is True
        assert out["draft"].startswith("[witty] launch:")
        assert out["final_length"] <= 280

    def test_empty_topic(self):
        out = _parse(_get_tool("social_draft")(network="x", topic=""))
        assert out["ok"] is False

    def test_bad_tone(self):
        out = _parse(_get_tool("social_draft")(network="x", topic="t", tone="rude"))
        assert out["ok"] is False

    def test_bad_length(self):
        out = _parse(_get_tool("social_draft")(network="x", topic="t",
                                               length_hint="epic"))
        assert out["ok"] is False

    def test_bad_network(self):
        out = _parse(_get_tool("social_draft")(network="myspace", topic="t"))
        assert out["ok"] is False


class TestSocialAnalytics:
    def test_happy(self):
        out = _parse(_get_tool("social_analytics")(network="tiktok", metric="reach",
                                                    days=14))
        assert out["ok"] is True
        assert out["instruction"]["query"] == {"metric": "reach", "window": "14d"}

    def test_bad_network(self):
        out = _parse(_get_tool("social_analytics")(network="myspace"))
        assert out["ok"] is False

    def test_bad_metric(self):
        out = _parse(_get_tool("social_analytics")(network="x", metric="vibes"))
        assert out["ok"] is False

    def test_bad_days(self):
        out = _parse(_get_tool("social_analytics")(network="x", days="lots"))
        assert out["ok"] is False

    def test_days_clamped(self):
        out = _parse(_get_tool("social_analytics")(network="x", days=9999))
        assert out["days"] == 365


class TestSocialAccountsApprove:
    def test_accounts(self):
        out = _parse(_get_tool("social_accounts")())
        assert out["ok"] is True
        assert len(out["accounts"]) == 5

    def test_approve_happy(self):
        out = _parse(_get_tool("social_approve")(instruction_id="i1", approved=True))
        assert out["ok"] is True
        assert out["decision"] == "approved"
        assert out["authorization"] is False  # decision, not authorization

    def test_approve_rejected(self):
        out = _parse(_get_tool("social_approve")(instruction_id="i1", approved=False))
        assert out["decision"] == "rejected"

    def test_empty_id(self):
        out = _parse(_get_tool("social_approve")(instruction_id=""))
        assert out["ok"] is False

    def test_oversized_id(self):
        out = _parse(_get_tool("social_approve")(instruction_id="x" * 300))
        assert out["ok"] is False

    def test_non_bool_approved(self):
        out = _parse(_get_tool("social_approve")(instruction_id="i", approved="yes"))
        assert out["ok"] is False


class TestSocialEnqueue:
    def test_happy_linkedin(self):
        out = _parse(_get_tool("social_enqueue")(network="linkedin", content="hi"))
        assert out["ok"] is True
        assert out["channel"] == "linkedin"
        assert out["text"] == "hi"

    def test_x_free_gate(self):
        # X is paid-only (free limit 0) -> always rejected
        out = _parse(_get_tool("social_enqueue")(network="x", content="hi"))
        assert out["ok"] is False
        assert "allowance" in out["error"]

    def test_empty_content(self):
        out = _parse(_get_tool("social_enqueue")(network="linkedin", content=""))
        assert out["ok"] is False

    def test_bad_network(self):
        out = _parse(_get_tool("social_enqueue")(network="myspace", content="hi"))
        assert out["ok"] is False
