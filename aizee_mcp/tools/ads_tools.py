#!/usr/bin/env python3
"""Paid advertising MCP tools: campaign creation, optimization, ROAS, keywords, audience, budget.

All tools use pure computation or return JSON proxy instructions for external
ad platforms (Google / Meta / TikTok / LinkedIn Ads). No network libraries are
imported; write tools (create_campaign) are gated by the guardian and return
an approval-required instruction object.
"""

from __future__ import annotations

import json
import math
from enum import Enum
from typing import Any

from aizee_mcp._compat import FastMCP  # pyright: ignore
from runtime.schemas import ValidationError

from .common import truncate, validate_query


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, default=str)


def _finite(value: Any, name: str, minimum: float = 0.0, maximum: float = 1e15) -> float:
    """Coerce to a finite float in [minimum, maximum]; raises ValidationError."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"'{name}' must be a number", context={"name": name}) from exc
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValidationError(
            f"'{name}' must be finite and within [{minimum}, {maximum}]",
            context={"name": name},
        )
    return number


def _err(error: str, **extra: Any) -> str:
    return _json({"ok": False, "error": error, **extra})


def _ok(**data: Any) -> str:
    return _json({"ok": True, **data})


class AdsPlatform(str, Enum):
    GOOGLE = "google"
    META = "meta"
    TIKTOK = "tiktok"
    LINKEDIN = "linkedin"


_ALLOWED_PLATFORMS = [p.value for p in AdsPlatform]


def _resolve_platform(platform: str) -> AdsPlatform:
    key = (platform or "").lower()
    try:
        return AdsPlatform(key)
    except ValueError as exc:
        raise ValidationError(
            f"Unknown ads platform '{platform}'",
            context={"allowed": _ALLOWED_PLATFORMS},
        ) from exc


def register_ads_tools(mcp: FastMCP) -> None:
    """Register paid-advertising MCP tools."""

    @mcp.tool()
    def ads_create_campaign(
        platform: str,
        name: str,
        objective: str = "conversions",
        budget_daily: float = 0.0,
        target_locations: str = "[]",
    ) -> str:
        """Create a paid campaign. WRITE/EXTERNAL — gated; returns proxy instruction (no inline API call)."""
        if err := validate_query(name):
            return err
        try:
            budget_daily = _finite(budget_daily, "budget_daily", minimum=0.01)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        try:
            plat = _resolve_platform(platform)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        try:
            locations = json.loads(target_locations)
        except json.JSONDecodeError:
            return _err("'target_locations' must be valid JSON")
        if not isinstance(locations, list):
            return _err("'target_locations' must be a JSON array")
        return _json({
            "ok": True,
            "gated": True,
            "approval_required": True,
            "campaign": name,
            "instruction": {
                "platform": plat.value,
                "action": "create_campaign",
                "objective": objective,
                "budget_daily": budget_daily,
                "locations": locations,
                "requires_api_key_env": f"AIZEE_{plat.value.upper()}_ADS_KEY",
            },
            "note": "Campaign creation requires guardian approval before execution.",
        })

    @mcp.tool()
    def ads_optimize(
        campaign_id: str,
        ctr: float = 0.0,
        cpc: float = 0.0,
        conversion_rate: float = 0.0,
    ) -> str:
        """Compute optimization recommendations from campaign metrics (pure logic)."""
        if err := validate_query(campaign_id):
            return err
        try:
            ctr = _finite(ctr, "ctr", maximum=100.0)
            cpc = _finite(cpc, "cpc", maximum=1e6)
            conversion_rate = _finite(conversion_rate, "conversion_rate", maximum=100.0)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        recommendations: list[str] = []
        if ctr < 0.01:
            recommendations.append("Low CTR (<1%): refine ad copy / creative and tighten targeting.")
        if cpc > 0 and cpc > 2.0:
            recommendations.append("High CPC (>2.0): add negative keywords and improve Quality Score.")
        if conversion_rate > 0 and conversion_rate < 0.02:
            recommendations.append("Low conversion (<2%): optimize landing page and CTA.")
        if not recommendations:
            recommendations.append("Metrics within healthy ranges; maintain and A/B test creatives.")
        return _ok(
            campaign_id=campaign_id,
            ctr=ctr,
            cpc=cpc,
            conversion_rate=conversion_rate,
            recommendations=recommendations,
        )

    @mcp.tool()
    def ads_fetch_roas(
        platform: str,
        spend: float = 0.0,
        revenue: float = 0.0,
    ) -> str:
        """Compute ROAS (return on ad spend) from spend and revenue. READ — pure computation."""
        try:
            plat = _resolve_platform(platform)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        try:
            spend = _finite(spend, "spend", minimum=0.01)
            revenue = _finite(revenue, "revenue")
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        roas = revenue / spend
        return _ok(
            platform=plat.value,
            spend=spend,
            revenue=revenue,
            roas=round(roas, 3),
            roas_multiple=f"{round(roas, 2)}x",
            profitable=roas >= 1.0,
        )

    @mcp.tool()
    def ads_keyword(
        seed: str,
        match_type: str = "broad",
        max_suggestions: int = 10,
    ) -> str:
        """Generate keyword variants from a seed (pure expansion). match_type: broad/phrase/exact."""
        if err := validate_query(seed):
            return err
        if match_type not in ("broad", "phrase", "exact"):
            return _err("'match_type' must be broad/phrase/exact")
        try:
            max_suggestions = max(1, min(int(max_suggestions), 50))
        except (TypeError, ValueError):
            return _err("'max_suggestions' must be an integer")
        templates = [
            "{kw}",
            "best {kw}",
            "{kw} service",
            "{kw} near me",
            "buy {kw}",
            "cheap {kw}",
            "{kw} reviews",
            "top {kw} 2026",
            "{kw} pricing",
            "{kw} for business",
        ]
        suggestions = []
        for t in templates:
            kw = t.format(kw=seed)
            if match_type == "exact":
                disp = f"[{kw}]"
            elif match_type == "phrase":
                disp = f'"{kw}"'
            else:
                disp = kw
            suggestions.append(disp)
            if len(suggestions) >= max_suggestions:
                break
        return _ok(
            seed=seed,
            match_type=match_type,
            count=len(suggestions),
            keywords=suggestions,
        )

    @mcp.tool()
    def ads_audience(
        platform: str,
        age_min: int = 18,
        age_max: int = 65,
        interests: str = "[]",
    ) -> str:
        """Estimate audience reach parameters (pure computation of age span + interest count)."""
        try:
            plat = _resolve_platform(platform)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        try:
            age_min = int(age_min)
            age_max = int(age_max)
        except (TypeError, ValueError):
            return _err("Age bounds must be integers")
        if age_min < 13 or age_max > 100 or age_min > age_max:
            return _err("Invalid age range (13-100, min<=max)")
        try:
            intr = json.loads(interests)
        except json.JSONDecodeError:
            return _err("'interests' must be valid JSON")
        if not isinstance(intr, list):
            return _err("'interests' must be a JSON array")
        return _ok(
            platform=plat.value,
            age_range=[age_min, age_max],
            age_span=age_max - age_min,
            interest_count=len(intr),
            interests=intr,
            note="Actual reach requires the platform's audience-estimate API (proxy).",
        )

    @mcp.tool()
    def ads_budget(
        total_budget: float,
        splits: str = "{}",
    ) -> str:
        """Distribute a total budget across channels by weight (pure computation)."""
        try:
            total_budget = _finite(total_budget, "total_budget", minimum=0.01)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        try:
            split_map = json.loads(splits)
        except json.JSONDecodeError:
            return _err("'splits' must be valid JSON")
        if not isinstance(split_map, dict) or not split_map:
            split_map = dict.fromkeys(_ALLOWED_PLATFORMS, 1.0)
        try:
            weights = {str(ch): _finite(w, f"splits[{ch}]") for ch, w in split_map.items()}
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        total_weight = sum(weights.values())
        if total_weight <= 0:
            return _err("sum of weights must be positive")
        allocations = {
            ch: round(total_budget * w / total_weight, 2)
            for ch, w in weights.items()
        }
        return _ok(
            total_budget=total_budget,
            total_weight=round(total_weight, 3),
            allocations=allocations,
            note=truncate("Allocate per-channel budgets; adjust weights to shift spend.", 200),
        )
