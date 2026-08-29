#!/usr/bin/env python3
"""Marketing analytics MCP tools: GA4, Mixpanel, dashboards, attribution, funnels, CAC/LTV.

Implements pure-computation attribution (last/first/linear/position-based),
funnel drop-off, and CAC/LTV math. External fetches/tracks (GA4, Mixpanel)
return JSON proxy instructions — no network libraries imported. Attribution
and funnel computation delegate to ``runtime.attribution_model`` and
``runtime.funnel_tracker``.
"""

from __future__ import annotations

import json
from typing import Any

from aizee_mcp._compat import FastMCP  # pyright: ignore
from runtime import (
    attribution_model,
    funnel_tracker,
    lead_scorer,
    marketing_compliance,
    pipeline_analytics,
)
from runtime.schemas import ValidationError

from .common import truncate, validate_query


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, default=str)


def _err(error: str, **extra: Any) -> str:
    return _json({"ok": False, "error": error, **extra})


def _ok(**data: Any) -> str:
    return _json({"ok": True, **data})


def _parse_touchpoints(touchpoints: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(touchpoints)
    except json.JSONDecodeError as exc:
        raise ValidationError("'touchpoints' must be valid JSON") from exc
    if not isinstance(data, list):
        raise ValidationError("'touchpoints' must be a JSON array")
    return data


_ATTRIBUTION_MODELS = {
    "last": attribution_model.last_click,
    "first": attribution_model.first_click,
    "linear": attribution_model.linear,
    "position": attribution_model.position_based,
}


def register_analytics_tools(mcp: FastMCP) -> None:
    """Register analytics-related MCP tools."""

    @mcp.tool()
    def ga4_fetch(
        property_id: str,
        metric: str = "activeUsers",
        days: int = 30,
    ) -> str:
        """Fetch a GA4 metric. READ/EXTERNAL — returns proxy instruction (no inline call)."""
        if err := validate_query(property_id):
            return err
        days = max(1, min(days, 365))
        return _json({
            "ok": True,
            "instruction": {
                "platform": "ga4",
                "action": "runReport",
                "property_id": property_id,
                "metric": metric,
                "date_range": f"last_{days}_days",
                "requires_credentials_env": "AIZEE_GA4_CREDENTIALS",
            },
            "note": "Proxy instruction; fetch via approved executor with GA4 credentials.",
        })

    @mcp.tool()
    def ga4_track(
        event_name: str,
        params: str = "{}",
    ) -> str:
        """Track a GA4 event (proxy instruction). WRITE/EXTERNAL — gated."""
        if err := validate_query(event_name):
            return err
        try:
            p = json.loads(params)
        except json.JSONDecodeError:
            return _err("'params' must be valid JSON")
        return _json({
            "ok": True,
            "gated": True,
            "approval_required": True,
            "instruction": {
                "platform": "ga4",
                "action": "track",
                "event": event_name,
                "params": p,
                "requires_credentials_env": "AIZEE_GA4_MEASUREMENT_ID",
            },
            "note": "Event tracking requires guardian approval.",
        })

    @mcp.tool()
    def mixpanel_track(
        event_name: str,
        distinct_id: str = "",
        props: str = "{}",
    ) -> str:
        """Track a Mixpanel event (proxy instruction). WRITE/EXTERNAL — gated."""
        if err := validate_query(event_name):
            return err
        try:
            p = json.loads(props)
        except json.JSONDecodeError:
            return _err("'props' must be valid JSON")
        return _json({
            "ok": True,
            "gated": True,
            "approval_required": True,
            "instruction": {
                "platform": "mixpanel",
                "action": "track",
                "event": event_name,
                "distinct_id": distinct_id,
                "props": p,
                "requires_credentials_env": "AIZEE_MIXPANEL_TOKEN",
            },
            "note": "Event tracking requires guardian approval.",
        })

    @mcp.tool()
    def analytics_dashboard(
        sources: str = "[]",
    ) -> str:
        """Aggregate a dashboard summary from a list of source identifiers. Pure computation of counts/status."""
        try:
            src = json.loads(sources)
        except json.JSONDecodeError:
            return _err("'sources' must be valid JSON")
        if not isinstance(src, list):
            return _err("'sources' must be a JSON array")
        return _ok(
            source_count=len(src),
            sources=src,
            panels=["traffic", "conversion", "acquisition", "revenue"],
            note="Wire each panel to ga4_fetch / mixpanel / attribution_report calls.",
        )

    @mcp.tool()
    def attribution_report(
        touchpoints: str,
        model: str = "linear",
    ) -> str:
        """Compute multi-touch attribution credit per channel. Pure computation (last/first/linear/position).

        Touchpoints: JSON array of {"channel": "...", "ts": ...} in chronological order.
        """
        if model not in _ATTRIBUTION_MODELS:
            return _err("'model' must be one of: " + ", ".join(_ATTRIBUTION_MODELS))
        try:
            tps = _parse_touchpoints(touchpoints)
        except ValidationError as exc:
            return _err(exc.message)
        if not tps:
            return _err("'touchpoints' must be non-empty")
        credit = _ATTRIBUTION_MODELS[model](tps)
        return _ok(
            model=model,
            touchpoint_count=len(tps),
            credit=credit,
            note="Attribution computed via runtime.attribution_model.",
        )

    @mcp.tool()
    def funnel_report(
        steps: str,
    ) -> str:
        """Compute funnel drop-off from step counts. Pure computation."""
        try:
            steps_list = json.loads(steps)
        except json.JSONDecodeError:
            return _err("'steps' must be valid JSON")
        if not isinstance(steps_list, list) or not steps_list:
            return _err("'steps' must be a non-empty JSON array")
        counts: list[int] = []
        for s in steps_list:
            if not isinstance(s, dict) or "count" not in s:
                return _err("each step needs a 'count' field")
            counts.append(int(s["count"]))
        top = counts[0] or 1
        stages = []
        prev = counts[0]
        for i, c in enumerate(counts):
            conv_from_prev = (c / prev) if prev else 0.0
            conv_from_top = c / top
            stages.append({
                "step": i + 1,
                "label": steps_list[i].get("label", f"step_{i + 1}"),
                "count": c,
                "conv_from_prev": round(conv_from_prev, 4),
                "conv_from_top": round(conv_from_top, 4),
                "dropoff_from_prev": round(1.0 - conv_from_prev, 4),
            })
            prev = c
        return _ok(
            top_count=counts[0],
            bottom_count=counts[-1],
            overall_conv=round(counts[-1] / top, 4),
            stages=stages,
        )

    @mcp.tool()
    def cac_ltv_report(
        spend: float,
        new_customers: int,
        arpu: float,
        gross_margin: float = 1.0,
        avg_lifetime_months: float = 12.0,
    ) -> str:
        """Compute CAC, LTV, and LTV:CAC ratio. Pure computation."""
        if spend <= 0:
            return _err("'spend' must be positive")
        if new_customers <= 0:
            return _err("'new_customers' must be positive")
        if arpu < 0 or not 0.0 < gross_margin <= 1.0:
            return _err("'arpu' must be >=0 and 'gross_margin' in (0,1]")
        cac = spend / new_customers
        ltv = arpu * gross_margin * avg_lifetime_months
        ratio = ltv / cac if cac else 0.0
        return _ok(
            cac=round(cac, 2),
            ltv=round(ltv, 2),
            ltv_cac_ratio=round(ratio, 2),
            healthy=ratio >= 3.0,
            note=truncate("Healthy LTV:CAC is typically >= 3.0.", 200),
        )

    @mcp.tool()
    def lead_score(
        fit: float,
        intent: float,
        behavior: float,
    ) -> str:
        """Score a lead on a 0-100 scale using runtime.lead_scorer. Pure computation.

        Args:
            fit: How well the lead matches ICP (0.0-1.0).
            intent: Signal strength of buying intent (0.0-1.0).
            behavior: Engagement level (0.0-1.0).
        """
        try:
            score = lead_scorer.score_lead(fit=fit, intent=intent, behavior=behavior)
        except (ValidationError, TypeError, ValueError) as exc:
            return _err(exc.message if hasattr(exc, "message") else str(exc))
        grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D"
        return _ok(
            score=score,
            grade=grade,
            recommendation="prioritize" if score >= 60 else "nurture" if score >= 40 else "disqualify",
            note="Scored via runtime.lead_scorer.",
        )

    @mcp.tool()
    def compliance_check(
        channel: str,
        has_optin: bool,
        has_unsubscribe: bool,
        is_gdpr: bool,
    ) -> str:
        """Check a planned send for GDPR/CAN-SPAM compliance via runtime.marketing_compliance. Pure computation."""
        try:
            compliant, violations = marketing_compliance.check_compliance(
                channel=channel,
                has_optin=has_optin,
                has_unsubscribe=has_unsubscribe,
                is_gdpr=is_gdpr,
            )
        except (ValidationError, TypeError, ValueError) as exc:
            return _err(exc.message if hasattr(exc, "message") else str(exc))
        return _ok(
            compliant=compliant,
            violations=violations,
            violation_count=len(violations),
            note="Checked via runtime.marketing_compliance.",
        )

    @mcp.tool()
    def pipeline_win_rate(
        platform: str = "",
        niche: str = "",
    ) -> str:
        """Compute freelance win rate from recorded bids via runtime.pipeline_analytics.

        Returns 0.0 if no bids recorded. Use pipeline_record_bid first.
        """
        try:
            pa = pipeline_analytics.PipelineAnalytics()
            plat = platform or None
            nich = niche or None
            rate = pa.win_rate(platform=plat, niche=nich)
        except (ValidationError, TypeError, ValueError) as exc:
            return _err(exc.message if hasattr(exc, "message") else str(exc))
        return _ok(
            win_rate=round(rate, 4),
            platform=plat,
            niche=nich,
            note="Computed via runtime.pipeline_analytics. Instantiate PipelineAnalytics and call record_bid to track bids.",
        )

    @mcp.tool()
    def funnel_dropoff(
        steps: str,
    ) -> str:
        """Compute funnel drop-off rates via runtime.funnel_tracker. Pure computation.

        Steps: JSON array of {"label": "...", "count": N} in funnel order.
        """
        try:
            steps_list = json.loads(steps)
        except json.JSONDecodeError:
            return _err("'steps' must be valid JSON")
        if not isinstance(steps_list, list) or not steps_list:
            return _err("'steps' must be a non-empty JSON array")
        try:
            f = funnel_tracker.Funnel(steps_list[0].get("label", "funnel"))
            for s in steps_list:
                if not isinstance(s, dict):
                    return _err("each step must be a JSON object")
                step = f.add_step(s.get("label", "step"))
                step.reached = int(s.get("count", 0))
            dropoff = f.dropoff()
        except (ValidationError, KeyError, TypeError, ValueError, AttributeError) as exc:
            return _err(exc.message if hasattr(exc, "message") else str(exc))
        return _ok(
            step_count=len(steps_list),
            dropoff=dropoff,
            note="Computed via runtime.funnel_tracker.",
        )
