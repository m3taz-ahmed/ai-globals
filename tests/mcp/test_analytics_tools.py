"""Tests for aizee_mcp/tools/analytics_tools.py MCP tools."""

from __future__ import annotations

import json
from typing import Any

import pytest

from aizee_mcp.tools.analytics_tools import (  # pyright: ignore[reportMissingImports]
    register_analytics_tools,
)

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
    register_analytics_tools(_FakeMCP())
    return _captured_tools[name]


def _parse(result: str) -> dict[str, Any]:
    return json.loads(result)


class TestGa4Fetch:
    def test_happy(self):
        out = _parse(_get_tool("ga4_fetch")(property_id="123", metric="sessions", days=7))
        assert out["ok"] is True
        inst = out["instruction"]
        assert inst["platform"] == "ga4"
        assert inst["date_range"] == "last_7_days"

    def test_days_clamped(self):
        out = _parse(_get_tool("ga4_fetch")(property_id="1", days=999))
        assert out["instruction"]["date_range"] == "last_365_days"

    def test_empty_property(self):
        out = _parse(_get_tool("ga4_fetch")(property_id=""))
        assert out["ok"] is False


class TestGa4Track:
    def test_happy(self):
        out = _parse(_get_tool("ga4_track")(event_name="signup", params='{"plan":"pro"}'))
        assert out["ok"] is True
        assert out["instruction"]["event"] == "signup"
        assert out["instruction"]["params"] == {"plan": "pro"}

    def test_empty_event(self):
        out = _parse(_get_tool("ga4_track")(event_name=""))
        assert out["ok"] is False

    def test_bad_params(self):
        out = _parse(_get_tool("ga4_track")(event_name="e", params="nope"))
        assert out["ok"] is False


class TestMixpanelTrack:
    def test_happy(self):
        out = _parse(_get_tool("mixpanel_track")(event_name="click", distinct_id="u1"))
        assert out["ok"] is True
        assert out["instruction"]["platform"] == "mixpanel"
        assert out["instruction"]["distinct_id"] == "u1"

    def test_empty_event(self):
        out = _parse(_get_tool("mixpanel_track")(event_name=""))
        assert out["ok"] is False

    def test_bad_props(self):
        out = _parse(_get_tool("mixpanel_track")(event_name="e", props="nope"))
        assert out["ok"] is False


class TestAnalyticsDashboard:
    def test_happy(self):
        out = _parse(_get_tool("analytics_dashboard")(sources='["ga4","mixpanel"]'))
        assert out["ok"] is True
        assert out["source_count"] == 2
        assert "traffic" in out["panels"]

    def test_bad_json(self):
        out = _parse(_get_tool("analytics_dashboard")(sources="nope"))
        assert out["ok"] is False

    def test_non_array(self):
        out = _parse(_get_tool("analytics_dashboard")(sources="{}"))
        assert out["ok"] is False


class TestAttributionReport:
    _TPS = '[{"channel":"ads"},{"channel":"email"},{"channel":"direct"}]'

    def test_linear(self):
        out = _parse(_get_tool("attribution_report")(touchpoints=self._TPS, model="linear"))
        assert out["ok"] is True
        assert out["touchpoint_count"] == 3
        assert abs(sum(out["credit"].values()) - 1.0) < 1e-9

    def test_last_click(self):
        out = _parse(_get_tool("attribution_report")(touchpoints=self._TPS, model="last"))
        assert out["credit"] == {"direct": 1.0}

    def test_first_click(self):
        out = _parse(_get_tool("attribution_report")(touchpoints=self._TPS, model="first"))
        assert out["credit"] == {"ads": 1.0}

    def test_position(self):
        out = _parse(_get_tool("attribution_report")(touchpoints=self._TPS, model="position"))
        assert out["credit"]["ads"] == 0.4
        assert out["credit"]["direct"] == 0.4

    def test_bad_model(self):
        out = _parse(_get_tool("attribution_report")(touchpoints=self._TPS, model="weird"))
        assert out["ok"] is False
        assert "model" in out["error"]

    def test_bad_json(self):
        out = _parse(_get_tool("attribution_report")(touchpoints="nope"))
        assert out["ok"] is False

    def test_non_array(self):
        out = _parse(_get_tool("attribution_report")(touchpoints="{}"))
        assert out["ok"] is False

    def test_empty_list(self):
        out = _parse(_get_tool("attribution_report")(touchpoints="[]"))
        assert out["ok"] is False
        assert "non-empty" in out["error"]

    def test_missing_channel_key(self):
        out = _parse(_get_tool("attribution_report")(touchpoints='[{"x":1}]'))
        assert out["ok"] is False


class TestFunnelReport:
    _STEPS = '[{"label":"visit","count":100},{"label":"signup","count":40},{"label":"pay","count":10}]'

    def test_happy(self):
        out = _parse(_get_tool("funnel_report")(steps=self._STEPS))
        assert out["ok"] is True
        assert out["overall_conv"] == 0.1
        assert len(out["stages"]) == 3
        assert out["stages"][1]["conv_from_prev"] == 0.4

    def test_zero_top_count(self):
        out = _parse(_get_tool("funnel_report")(steps='[{"count":0},{"count":0}]'))
        assert out["ok"] is True
        assert out["overall_conv"] == 0.0

    def test_bad_json(self):
        out = _parse(_get_tool("funnel_report")(steps="nope"))
        assert out["ok"] is False

    def test_empty_list(self):
        out = _parse(_get_tool("funnel_report")(steps="[]"))
        assert out["ok"] is False

    def test_missing_count(self):
        out = _parse(_get_tool("funnel_report")(steps='[{"label":"x"}]'))
        assert out["ok"] is False
        assert "count" in out["error"]

    def test_non_int_count(self):
        out = _parse(_get_tool("funnel_report")(steps='[{"count":"many"}]'))
        assert out["ok"] is False
        assert "integer" in out["error"]

    def test_negative_count(self):
        out = _parse(_get_tool("funnel_report")(steps='[{"count":-5}]'))
        assert out["ok"] is False


class TestCacLtvReport:
    def test_happy_healthy(self):
        out = _parse(_get_tool("cac_ltv_report")(spend=1000, new_customers=10,
                                                  arpu=50, gross_margin=0.8,
                                                  avg_lifetime_months=12))
        assert out["ok"] is True
        assert out["cac"] == 100.0
        assert out["ltv"] == 480.0
        assert out["healthy"] is True

    def test_unhealthy(self):
        out = _parse(_get_tool("cac_ltv_report")(spend=1000, new_customers=10,
                                                  arpu=5, gross_margin=1.0,
                                                  avg_lifetime_months=1))
        assert out["healthy"] is False

    def test_zero_spend(self):
        out = _parse(_get_tool("cac_ltv_report")(spend=0, new_customers=10, arpu=50))
        assert out["ok"] is False

    def test_bad_customers(self):
        out = _parse(_get_tool("cac_ltv_report")(spend=100, new_customers="x", arpu=50))
        assert out["ok"] is False

    def test_zero_customers(self):
        out = _parse(_get_tool("cac_ltv_report")(spend=100, new_customers=0, arpu=50))
        assert out["ok"] is False
        assert "positive" in out["error"]

    def test_margin_out_of_range(self):
        out = _parse(_get_tool("cac_ltv_report")(spend=100, new_customers=5, arpu=50,
                                                  gross_margin=2.0))
        assert out["ok"] is False


class TestLeadScore:
    def test_grade_a(self):
        out = _parse(_get_tool("lead_score")(fit=0.9, intent=0.9, behavior=0.9))
        assert out["ok"] is True
        assert out["grade"] == "A"
        assert out["recommendation"] == "prioritize"

    def test_grade_c_nurture(self):
        out = _parse(_get_tool("lead_score")(fit=0.5, intent=0.5, behavior=0.5))
        assert out["grade"] == "C"
        assert out["recommendation"] == "nurture"

    def test_grade_d_disqualify(self):
        out = _parse(_get_tool("lead_score")(fit=0.1, intent=0.1, behavior=0.1))
        assert out["grade"] == "D"
        assert out["recommendation"] == "disqualify"

    def test_out_of_range(self):
        out = _parse(_get_tool("lead_score")(fit=1.5, intent=0.5, behavior=0.5))
        assert out["ok"] is False


class TestComplianceCheck:
    def test_compliant(self):
        out = _parse(_get_tool("compliance_check")(channel="email", has_optin=True,
                                                    has_unsubscribe=True, is_gdpr=True))
        assert out["ok"] is True
        assert out["compliant"] is True
        assert out["violation_count"] == 0

    def test_violations(self):
        out = _parse(_get_tool("compliance_check")(channel="email", has_optin=False,
                                                    has_unsubscribe=False, is_gdpr=True))
        assert out["compliant"] is False
        assert out["violation_count"] >= 2

    def test_unknown_channel(self):
        out = _parse(_get_tool("compliance_check")(channel="fax", has_optin=True,
                                                    has_unsubscribe=True, is_gdpr=False))
        assert out["ok"] is False
        assert "unknown channel" in out["error"]


class TestPipelineWinRate:
    def test_happy(self):
        bids = json.dumps([
            {"platform": "upwork", "niche": "web", "amount": 500, "won": True},
            {"platform": "upwork", "niche": "web", "amount": 300, "won": False},
        ])
        out = _parse(_get_tool("pipeline_win_rate")(platform="upwork", bids=bids))
        assert out["ok"] is True
        assert out["win_rate"] == 0.5
        assert out["bids_recorded"] == 2

    def test_empty_bids(self):
        out = _parse(_get_tool("pipeline_win_rate")())
        assert out["ok"] is True
        assert out["win_rate"] == 0.0

    def test_bad_json(self):
        out = _parse(_get_tool("pipeline_win_rate")(bids="nope"))
        assert out["ok"] is False

    def test_non_array(self):
        out = _parse(_get_tool("pipeline_win_rate")(bids="{}"))
        assert out["ok"] is False

    def test_non_dict_bid(self):
        out = _parse(_get_tool("pipeline_win_rate")(bids="[1]"))
        assert out["ok"] is False
        assert "object" in out["error"]

    def test_bad_amount(self):
        out = _parse(_get_tool("pipeline_win_rate")(bids='[{"amount":"x"}]'))
        assert out["ok"] is False

    def test_bad_won_type(self):
        out = _parse(_get_tool("pipeline_win_rate")(bids='[{"amount":1,"won":"yes"}]'))
        assert out["ok"] is False
        assert "true/false/null" in out["error"]


class TestFunnelDropoff:
    def test_happy(self):
        steps = '[{"label":"visit","count":100},{"label":"buy","count":25}]'
        out = _parse(_get_tool("funnel_dropoff")(steps=steps))
        assert out["ok"] is True
        assert out["step_count"] == 2
        assert out["dropoff"][1]["dropoff_from_prev"] == 0.75

    def test_bad_json(self):
        out = _parse(_get_tool("funnel_dropoff")(steps="nope"))
        assert out["ok"] is False

    def test_empty(self):
        out = _parse(_get_tool("funnel_dropoff")(steps="[]"))
        assert out["ok"] is False

    def test_non_dict_step(self):
        out = _parse(_get_tool("funnel_dropoff")(steps="[1]"))
        assert out["ok"] is False
        assert "object" in out["error"]

    def test_non_int_count(self):
        out = _parse(_get_tool("funnel_dropoff")(steps='[{"count":"x"}]'))
        assert out["ok"] is False

    def test_negative_count(self):
        out = _parse(_get_tool("funnel_dropoff")(steps='[{"count":-1}]'))
        assert out["ok"] is False
