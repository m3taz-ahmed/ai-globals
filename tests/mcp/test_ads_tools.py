"""Tests for aizee_mcp/tools/ads_tools.py MCP tools."""

from __future__ import annotations

import json
from typing import Any

import pytest

from aizee_mcp.tools.ads_tools import register_ads_tools  # pyright: ignore[reportMissingImports]

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
    register_ads_tools(_FakeMCP())
    return _captured_tools[name]


def _parse(result: str) -> dict[str, Any]:
    return json.loads(result)


class TestAdsCreateCampaign:
    def test_happy(self):
        out = _parse(_get_tool("ads_create_campaign")(
            platform="google", name="Launch", budget_daily=50.0,
            target_locations='["EG","SA"]'))
        assert out["ok"] is True
        assert out["gated"] is True
        inst = out["instruction"]
        assert inst["platform"] == "google"
        assert inst["budget_daily"] == 50.0
        assert inst["locations"] == ["EG", "SA"]

    def test_empty_name(self):
        out = _parse(_get_tool("ads_create_campaign")(platform="meta", name=""))
        assert out["ok"] is False

    def test_bad_budget_type(self):
        out = _parse(_get_tool("ads_create_campaign")(platform="meta", name="x",
                                                      budget_daily="abc"))
        assert out["ok"] is False
        assert "number" in out["error"]

    def test_zero_budget(self):
        out = _parse(_get_tool("ads_create_campaign")(platform="meta", name="x",
                                                      budget_daily=0))
        assert out["ok"] is False
        assert "finite" in out["error"]

    def test_nan_budget(self):
        out = _parse(_get_tool("ads_create_campaign")(platform="meta", name="x",
                                                      budget_daily=float("nan")))
        assert out["ok"] is False

    def test_bad_platform(self):
        out = _parse(_get_tool("ads_create_campaign")(platform="snap", name="x",
                                                      budget_daily=10))
        assert out["ok"] is False
        assert "Unknown ads platform" in out["error"]

    def test_bad_locations_json(self):
        out = _parse(_get_tool("ads_create_campaign")(platform="meta", name="x",
                                                      budget_daily=10, target_locations="nope"))
        assert out["ok"] is False
        assert "valid JSON" in out["error"]

    def test_non_array_locations(self):
        out = _parse(_get_tool("ads_create_campaign")(platform="meta", name="x",
                                                      budget_daily=10, target_locations="{}"))
        assert out["ok"] is False
        assert "JSON array" in out["error"]


class TestAdsOptimize:
    def test_healthy_metrics(self):
        out = _parse(_get_tool("ads_optimize")(campaign_id="c1", ctr=0.05, cpc=1.0,
                                               conversion_rate=0.05))
        assert out["ok"] is True
        assert "healthy" in out["recommendations"][0]

    def test_low_ctr(self):
        out = _parse(_get_tool("ads_optimize")(campaign_id="c1", ctr=0.005))
        assert any("Low CTR" in r for r in out["recommendations"])

    def test_high_cpc(self):
        out = _parse(_get_tool("ads_optimize")(campaign_id="c1", ctr=0.05, cpc=3.0))
        assert any("High CPC" in r for r in out["recommendations"])

    def test_low_conversion(self):
        out = _parse(_get_tool("ads_optimize")(campaign_id="c1", ctr=0.05,
                                               conversion_rate=0.01))
        assert any("Low conversion" in r for r in out["recommendations"])

    def test_empty_campaign_id(self):
        out = _parse(_get_tool("ads_optimize")(campaign_id=""))
        assert out["ok"] is False

    def test_non_number_metric(self):
        out = _parse(_get_tool("ads_optimize")(campaign_id="c1", ctr="high"))
        assert out["ok"] is False


class TestAdsFetchRoas:
    def test_happy(self):
        out = _parse(_get_tool("ads_fetch_roas")(platform="tiktok", spend=100.0,
                                                 revenue=350.0))
        assert out["ok"] is True
        assert out["roas"] == 3.5
        assert out["roas_multiple"] == "3.5x"
        assert out["profitable"] is True

    def test_unprofitable(self):
        out = _parse(_get_tool("ads_fetch_roas")(platform="meta", spend=100.0,
                                                 revenue=50.0))
        assert out["profitable"] is False

    def test_bad_platform(self):
        out = _parse(_get_tool("ads_fetch_roas")(platform="x"))
        assert out["ok"] is False

    def test_zero_spend(self):
        out = _parse(_get_tool("ads_fetch_roas")(platform="meta", spend=0))
        assert out["ok"] is False

    def test_non_number_revenue(self):
        out = _parse(_get_tool("ads_fetch_roas")(platform="meta", spend=10, revenue="x"))
        assert out["ok"] is False


class TestAdsKeyword:
    def test_broad(self):
        out = _parse(_get_tool("ads_keyword")(seed="plumber"))
        assert out["ok"] is True
        assert out["count"] == 10
        assert out["keywords"][0] == "plumber"
        assert '"plumber"' not in out["keywords"]

    def test_exact_match_wraps(self):
        out = _parse(_get_tool("ads_keyword")(seed="plumber", match_type="exact",
                                              max_suggestions=3))
        assert out["keywords"][0] == "[plumber]"
        assert out["count"] == 3

    def test_phrase_match_quotes(self):
        out = _parse(_get_tool("ads_keyword")(seed="plumber", match_type="phrase"))
        assert out["keywords"][0] == '"plumber"'

    def test_max_suggestions_clamped(self):
        out = _parse(_get_tool("ads_keyword")(seed="plumber", max_suggestions=500))
        assert out["count"] == 10  # only 10 templates exist

    def test_bad_match_type(self):
        out = _parse(_get_tool("ads_keyword")(seed="x", match_type="regex"))
        assert out["ok"] is False

    def test_non_int_max(self):
        out = _parse(_get_tool("ads_keyword")(seed="x", max_suggestions="lots"))
        assert out["ok"] is False

    def test_empty_seed(self):
        out = _parse(_get_tool("ads_keyword")(seed=""))
        assert out["ok"] is False


class TestAdsAudience:
    def test_happy(self):
        out = _parse(_get_tool("ads_audience")(platform="linkedin", age_min=25,
                                               age_max=45, interests='["tech","saas"]'))
        assert out["ok"] is True
        assert out["age_span"] == 20
        assert out["interest_count"] == 2

    def test_bad_platform(self):
        out = _parse(_get_tool("ads_audience")(platform="x"))
        assert out["ok"] is False

    def test_non_int_ages(self):
        out = _parse(_get_tool("ads_audience")(platform="meta", age_min="x"))
        assert out["ok"] is False
        assert "integers" in out["error"]

    def test_invalid_age_range(self):
        out = _parse(_get_tool("ads_audience")(platform="meta", age_min=50, age_max=20))
        assert out["ok"] is False
        assert "age range" in out["error"].lower()

    def test_age_below_minimum(self):
        out = _parse(_get_tool("ads_audience")(platform="meta", age_min=10))
        assert out["ok"] is False

    def test_bad_interests_json(self):
        out = _parse(_get_tool("ads_audience")(platform="meta", interests="nope"))
        assert out["ok"] is False

    def test_non_list_interests(self):
        out = _parse(_get_tool("ads_audience")(platform="meta", interests="{}"))
        assert out["ok"] is False


class TestAdsBudget:
    def test_happy_weighted(self):
        out = _parse(_get_tool("ads_budget")(total_budget=1000.0,
                                             splits='{"google": 3, "meta": 1}'))
        assert out["ok"] is True
        assert out["allocations"]["google"] == 750.0
        assert out["allocations"]["meta"] == 250.0

    def test_default_splits(self):
        out = _parse(_get_tool("ads_budget")(total_budget=400.0, splits="{}"))
        assert out["ok"] is True
        assert len(out["allocations"]) == 4  # all platforms, equal weight
        assert out["allocations"]["google"] == 100.0

    def test_bad_budget(self):
        out = _parse(_get_tool("ads_budget")(total_budget=0))
        assert out["ok"] is False

    def test_bad_splits_json(self):
        out = _parse(_get_tool("ads_budget")(total_budget=100, splits="nope"))
        assert out["ok"] is False

    def test_non_dict_splits_uses_default(self):
        out = _parse(_get_tool("ads_budget")(total_budget=400.0, splits="[1,2]"))
        assert out["ok"] is True
        assert len(out["allocations"]) == 4

    def test_bad_weight_value(self):
        out = _parse(_get_tool("ads_budget")(total_budget=100, splits='{"g": "x"}'))
        assert out["ok"] is False

    def test_zero_total_weight(self):
        out = _parse(_get_tool("ads_budget")(total_budget=100, splits='{"g": 0}'))
        assert out["ok"] is False
        assert "positive" in out["error"]
