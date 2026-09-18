"""Tests for aizee_mcp/tools/email_tools.py MCP tools."""

from __future__ import annotations

import json
from typing import Any

import pytest

from aizee_mcp.tools.email_tools import (  # pyright: ignore[reportMissingImports]
    BrevoBackend,
    ListmonkBackend,
    MailchimpBackend,
    _clean_header,
    _resolve_backend,
    register_email_tools,
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
    register_email_tools(_FakeMCP())
    return _captured_tools[name]


def _parse(result: str) -> dict[str, Any]:
    return json.loads(result)


# ---------------------------------------------------------------------------
# Helpers / backends
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_clean_header_ok(self):
        assert _clean_header("  hi  ", "subject") == "hi"

    def test_clean_header_empty(self):
        with pytest.raises(ValidationError):
            _clean_header("", "subject")

    def test_clean_header_injection(self):
        with pytest.raises(ValidationError):
            _clean_header("a\nbcc: evil@x.com", "subject")

    def test_clean_header_too_long(self):
        with pytest.raises(ValidationError):
            _clean_header("x" * 999, "subject")

    def test_resolve_backend_all(self):
        assert isinstance(_resolve_backend("brevo"), BrevoBackend)
        assert isinstance(_resolve_backend("listmonk"), ListmonkBackend)
        assert isinstance(_resolve_backend("mailchimp"), MailchimpBackend)
        assert isinstance(_resolve_backend(""), BrevoBackend)  # default

    def test_resolve_backend_unknown(self):
        with pytest.raises(ValidationError):
            _resolve_backend("sendgrid")

    def test_backend_instructions(self):
        payload = {"sender": "a@b.com", "to": [{"email": "c@d.com"}],
                   "subject": "s", "html": "<p>x</p>", "lists": [1], "list_id": "L"}
        b = BrevoBackend().build_send_instruction(payload)
        assert b["provider"] == "brevo" and "brevo.com" in b["endpoint"]
        lm = ListmonkBackend().build_send_instruction(payload)
        assert lm["provider"] == "listmonk" and lm["body"]["lists"] == [1]
        mc = MailchimpBackend().build_send_instruction(payload)
        assert mc["provider"] == "mailchimp"
        assert mc["body"]["recipients"]["list_id"] == "L"


# ---------------------------------------------------------------------------
# email_send
# ---------------------------------------------------------------------------


class TestEmailSend:
    def test_happy_brevo(self):
        out = _parse(_get_tool("email_send")(to="u@x.com", subject="Hi",
                                             html="<p>y</p>"))
        assert out["ok"] is True
        assert out["gated"] is True
        assert out["instruction"]["provider"] == "brevo"
        assert out["instruction"]["body"]["to"] == [{"email": "u@x.com"}]

    def test_text_body(self):
        out = _parse(_get_tool("email_send")(to="u@x.com", subject="Hi",
                                             text="plain"))
        assert out["ok"] is True

    def test_other_providers(self):
        for p in ("listmonk", "mailchimp"):
            out = _parse(_get_tool("email_send")(to="u@x.com", subject="s",
                                                 text="t", provider=p))
            assert out["instruction"]["provider"] == p

    def test_invalid_to(self):
        out = _parse(_get_tool("email_send")(to="not-an-email", subject="s", text="t"))
        assert out["ok"] is False
        assert "valid email" in out["error"]

    def test_header_injection_to(self):
        out = _parse(_get_tool("email_send")(to="u@x.com\nbcc:e@x.com", subject="s",
                                             text="t"))
        assert out["ok"] is False
        assert "line breaks" in out["error"]

    def test_empty_subject(self):
        out = _parse(_get_tool("email_send")(to="u@x.com", subject="", text="t"))
        assert out["ok"] is False

    def test_invalid_sender(self):
        out = _parse(_get_tool("email_send")(to="u@x.com", subject="s", text="t",
                                             sender="bad"))
        assert out["ok"] is False
        assert "'sender'" in out["error"]

    def test_no_body(self):
        out = _parse(_get_tool("email_send")(to="u@x.com", subject="s"))
        assert out["ok"] is False
        assert "body" in out["error"]

    def test_oversized_body(self):
        out = _parse(_get_tool("email_send")(to="u@x.com", subject="s",
                                             html="x" * 200_001))
        assert out["ok"] is False
        assert "exceeds" in out["error"]

    def test_unknown_provider(self):
        out = _parse(_get_tool("email_send")(to="u@x.com", subject="s", text="t",
                                             provider="x"))
        assert out["ok"] is False
        assert "Unknown email provider" in out["error"]


# ---------------------------------------------------------------------------
# email_sequence / email_segment / email_events / email_template
# ---------------------------------------------------------------------------


class TestEmailSequence:
    def test_happy(self):
        steps = '[{"delay_hours": 24, "subject": "Follow up"}]'
        out = _parse(_get_tool("email_sequence")(name="onboard", steps=steps))
        assert out["ok"] is True
        assert out["steps"][0]["step"] == 1
        assert out["steps"][0]["delay_hours"] == 24

    def test_bad_name(self):
        out = _parse(_get_tool("email_sequence")(name=""))
        assert out["ok"] is False

    def test_bad_json(self):
        out = _parse(_get_tool("email_sequence")(name="s", steps="nope"))
        assert out["ok"] is False

    def test_non_array(self):
        out = _parse(_get_tool("email_sequence")(name="s", steps="{}"))
        assert out["ok"] is False

    def test_non_dict_step(self):
        out = _parse(_get_tool("email_sequence")(name="s", steps='[1]'))
        assert out["ok"] is False
        assert "object" in out["error"]

    def test_bad_provider(self):
        out = _parse(_get_tool("email_sequence")(name="s", provider="x"))
        assert out["ok"] is False


class TestEmailSegment:
    def test_happy(self):
        out = _parse(_get_tool("email_segment")(name="eg-users",
                                                criteria='{"country":"EG","opened":true}'))
        assert out["ok"] is True
        assert out["rule_count"] == 2

    def test_bad_name(self):
        out = _parse(_get_tool("email_segment")(name=""))
        assert out["ok"] is False

    def test_bad_json(self):
        out = _parse(_get_tool("email_segment")(name="s", criteria="nope"))
        assert out["ok"] is False

    def test_non_dict(self):
        out = _parse(_get_tool("email_segment")(name="s", criteria="[1]"))
        assert out["ok"] is False


class TestEmailEvents:
    def test_happy(self):
        out = _parse(_get_tool("email_events")())
        assert out["ok"] is True
        assert out["provider"] == "brevo"
        assert "brevo.com" in out["instruction"]["endpoint"]

    def test_since_days_clamped(self):
        out = _parse(_get_tool("email_events")(since_days=365))
        assert out["since_days"] == 90

    def test_since_days_bad_type(self):
        out = _parse(_get_tool("email_events")(since_days="lots"))
        assert out["since_days"] == 7

    def test_bad_provider(self):
        out = _parse(_get_tool("email_events")(provider="x"))
        assert out["ok"] is False


class TestEmailTemplate:
    def test_happy_replaces_vars(self):
        out = _parse(_get_tool("email_template")(name="t", body="Hi {{name}}!",
                                                 variables='["name"]'))
        assert out["ok"] is True
        assert "[name]" in out["preview"]

    def test_bad_name(self):
        out = _parse(_get_tool("email_template")(name=""))
        assert out["ok"] is False

    def test_bad_json(self):
        out = _parse(_get_tool("email_template")(name="t", variables="nope"))
        assert out["ok"] is False

    def test_non_array(self):
        out = _parse(_get_tool("email_template")(name="t", variables="{}"))
        assert out["ok"] is False


# ---------------------------------------------------------------------------
# email_campaign / subscribe / unsubscribe
# ---------------------------------------------------------------------------


class TestEmailCampaign:
    def test_happy(self):
        out = _parse(_get_tool("email_campaign")(name="c", subject="Hi",
                                                 list_id="L1", provider="listmonk"))
        assert out["ok"] is True
        assert out["instruction"]["provider"] == "listmonk"

    def test_bad_name(self):
        out = _parse(_get_tool("email_campaign")(name=""))
        assert out["ok"] is False

    def test_empty_subject(self):
        out = _parse(_get_tool("email_campaign")(name="c", subject=""))
        assert out["ok"] is False

    def test_bad_provider(self):
        out = _parse(_get_tool("email_campaign")(name="c", subject="s", provider="x"))
        assert out["ok"] is False


class TestEmailSubscribe:
    def test_happy(self):
        out = _parse(_get_tool("email_subscribe")(list_id="L1", email="u@x.com"))
        assert out["ok"] is True
        assert out["double_opt_in"] is True
        assert out["instruction"]["action"] == "subscribe"
        assert out["instruction"]["consent_required"] is True

    def test_bad_email(self):
        out = _parse(_get_tool("email_subscribe")(list_id="L1", email="bad"))
        assert out["ok"] is False

    def test_injection_list_id(self):
        out = _parse(_get_tool("email_subscribe")(list_id="L\n1", email="u@x.com"))
        assert out["ok"] is False

    def test_bad_provider(self):
        out = _parse(_get_tool("email_subscribe")(list_id="L", email="u@x.com",
                                                  provider="x"))
        assert out["ok"] is False


class TestEmailUnsubscribe:
    def test_happy(self):
        out = _parse(_get_tool("email_unsubscribe")(list_id="L1", email="u@x.com"))
        assert out["ok"] is True
        assert out["instruction"]["action"] == "unsubscribe"

    def test_bad_email(self):
        out = _parse(_get_tool("email_unsubscribe")(list_id="L1", email="bad"))
        assert out["ok"] is False

    def test_bad_provider(self):
        out = _parse(_get_tool("email_unsubscribe")(list_id="L", email="u@x.com",
                                                    provider="x"))
        assert out["ok"] is False


# ---------------------------------------------------------------------------
# drip_* / crm_opportunity_transition
# ---------------------------------------------------------------------------


class TestDripCreateSequence:
    def test_happy(self):
        out = _parse(_get_tool("drip_create_sequence")(name="seq1"))
        assert out["ok"] is True
        assert out["sequence"] == "seq1"
        assert out["step_count"] == 0

    def test_bad_name(self):
        out = _parse(_get_tool("drip_create_sequence")(name=""))
        assert out["ok"] is False


class TestDripReadySteps:
    def test_happy_ready_step(self):
        steps = json.dumps([{
            "trigger": "on_enter", "action": "send", "delay_hours": 0,
            "entered_hours_ago": 1,
        }])
        out = _parse(_get_tool("drip_ready_steps")(sequence_name="s", steps=steps))
        assert out["ok"] is True
        assert out["ready_count"] == 1
        assert out["ready_steps"][0]["action"] == "send"

    def test_delay_not_elapsed(self):
        steps = json.dumps([{
            "trigger": "on_enter", "action": "send", "delay_hours": 24,
            "entered_hours_ago": 1,
        }])
        out = _parse(_get_tool("drip_ready_steps")(sequence_name="s", steps=steps))
        assert out["ready_count"] == 0

    def test_fired_step_not_ready(self):
        steps = json.dumps([{
            "trigger": "on_enter", "action": "send", "delay_hours": 0,
            "entered_hours_ago": 1, "fired": True,
        }])
        out = _parse(_get_tool("drip_ready_steps")(sequence_name="s", steps=steps))
        assert out["ready_count"] == 0

    def test_not_entered_step(self):
        steps = json.dumps([{
            "trigger": "on_enter", "action": "send", "entered": False,
        }])
        out = _parse(_get_tool("drip_ready_steps")(sequence_name="s", steps=steps))
        assert out["ready_count"] == 0

    def test_bad_sequence_name(self):
        out = _parse(_get_tool("drip_ready_steps")(sequence_name=""))
        assert out["ok"] is False

    def test_bad_context_json(self):
        out = _parse(_get_tool("drip_ready_steps")(sequence_name="s", context="nope"))
        assert out["ok"] is False

    def test_non_dict_context(self):
        out = _parse(_get_tool("drip_ready_steps")(sequence_name="s", context="[1]"))
        assert out["ok"] is False

    def test_bad_steps_json(self):
        out = _parse(_get_tool("drip_ready_steps")(sequence_name="s", steps="nope"))
        assert out["ok"] is False

    def test_non_list_steps(self):
        out = _parse(_get_tool("drip_ready_steps")(sequence_name="s", steps="{}"))
        assert out["ok"] is False

    def test_non_dict_step(self):
        out = _parse(_get_tool("drip_ready_steps")(sequence_name="s", steps="[1]"))
        assert out["ok"] is False
        assert "object" in out["error"]

    def test_invalid_trigger(self):
        steps = '[{"trigger": "bogus", "action": "x"}]'
        out = _parse(_get_tool("drip_ready_steps")(sequence_name="s", steps=steps))
        assert out["ok"] is False
        assert "invalid trigger" in out["error"]

    def test_non_numeric_delay(self):
        steps = '[{"trigger": "on_enter", "action": "x", "delay_hours": "soon"}]'
        out = _parse(_get_tool("drip_ready_steps")(sequence_name="s", steps=steps))
        assert out["ok"] is False
        assert "numbers" in out["error"]

    def test_negative_delay(self):
        steps = '[{"trigger": "on_enter", "action": "x", "delay_hours": -1}]'
        out = _parse(_get_tool("drip_ready_steps")(sequence_name="s", steps=steps))
        assert out["ok"] is False
        assert "non-negative" in out["error"]


class TestCrmOpportunityTransition:
    def test_happy_valid_transition(self):
        out = _parse(_get_tool("crm_opportunity_transition")(
            opportunity_id="o1", company_id="c1",
            from_stage="new", to_stage="qualified", amount=500.0))
        assert out["ok"] is True
        assert out["from_stage"] == "new"
        assert out["to_stage"] == "qualified"

    def test_empty_opportunity_id(self):
        out = _parse(_get_tool("crm_opportunity_transition")(
            opportunity_id="", company_id="c", from_stage="new", to_stage="lost"))
        assert out["ok"] is False

    def test_invalid_stage(self):
        out = _parse(_get_tool("crm_opportunity_transition")(
            opportunity_id="o", company_id="c", from_stage="bogus", to_stage="won"))
        assert out["ok"] is False
        assert "invalid stage" in out["error"]

    def test_non_number_amount(self):
        out = _parse(_get_tool("crm_opportunity_transition")(
            opportunity_id="o", company_id="c", from_stage="new",
            to_stage="qualified", amount="lots"))
        assert out["ok"] is False
        assert "number" in out["error"]

    def test_nan_amount(self):
        out = _parse(_get_tool("crm_opportunity_transition")(
            opportunity_id="o", company_id="c", from_stage="new",
            to_stage="qualified", amount=float("nan")))
        assert out["ok"] is False
        assert "finite" in out["error"]

    def test_invalid_transition(self):
        out = _parse(_get_tool("crm_opportunity_transition")(
            opportunity_id="o", company_id="c", from_stage="new", to_stage="won"))
        assert out["ok"] is False
        assert "invalid opportunity transition" in out["error"]
