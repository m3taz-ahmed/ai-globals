"""Residual gap coverage for aizee_mcp tools: context 500-file cap,
analytics pipeline_win_rate ValidationError, freelance pricing_calc
ValidationError."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

import aizee_mcp.tools.analytics_tools as analytics
import aizee_mcp.tools.context_tools as ctx
import aizee_mcp.tools.freelance_tools as freelance


class _FakeTool:
    def __call__(self, fn: Any | None = None, *a: Any, **k: Any) -> Any:
        if callable(fn):
            _captured[fn.__name__] = fn
            return fn

        def decorator(inner: Any) -> Any:
            _captured[inner.__name__] = inner
            return inner

        return decorator


class _FakeMCP:
    def __init__(self) -> None:
        self.tool = _FakeTool()
        self.resource = _FakeTool()
        self.prompt = _FakeTool()


_captured: dict[str, Any] = {}

analytics.register_analytics_tools(_FakeMCP())
ctx.register_context_tools(_FakeMCP())
freelance.register_freelance_tools(_FakeMCP())

pytestmark = [pytest.mark.mcp]


class TestContext500Cap:
    def test_cap_breaks_at_500(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        skills = tmp_path / "skills"
        skills.mkdir()
        # 501 md files, none matching the query -> `results` never reaches the
        # `limit` early-break, so iteration continues until `scanned >= 500`.
        for i in range(501):
            (skills / f"skill_{i:03d}.md").write_text("x")
        monkeypatch.setattr(ctx, "root", lambda: tmp_path)
        out = json.loads(_captured["search_skills"](query="zzz-no-match"))
        assert out == []


class TestAnalyticsValidation:
    def test_pipeline_win_rate_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from runtime.pipeline_analytics import PipelineAnalytics

        bad = MagicMock(spec=PipelineAnalytics)
        bad.record_bid.return_value = None
        bad.win_rate.side_effect = TypeError("bad args")
        monkeypatch.setattr(
            analytics.pipeline_analytics, "PipelineAnalytics", lambda: bad
        )
        out = json.loads(_captured["pipeline_win_rate"](
            bids='[{"platform": "upwork", "amount": 10, "won": true}]'
        ))
        assert out.get("ok") is False or "error" in out


class TestFreelanceValidation:
    def test_pricing_calc_validation(self) -> None:
        out = json.loads(_captured["pricing_calc"](
            income_goal=1000, billable_hours_per_week=-1,
            tax_rate=0.2, platform_fee_rate=0.1, utilization=0.5,
        ))
        assert out.get("ok") is False or "error" in out
