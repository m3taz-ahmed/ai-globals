#!/usr/bin/env python3
"""CRO (conversion rate optimization) MCP tools: audit, experiments, flags, heatmaps, replay, surveys.

Implements pure-computation experiment significance (two-proportion z-test),
flag configuration, and audit checklists. External observability tools
(heatmap / session replay / surveys) return JSON proxy instructions — no
network libraries imported. Experiment analysis delegates to
``runtime.experiment_tracker`` and flag evaluation to ``runtime.feature_flags``.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any

from aizee_mcp._compat import FastMCP  # pyright: ignore
from runtime import experiment_tracker, feature_flags
from runtime.schemas import ValidationError

from .common import truncate, validate_query


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, default=str)


def _err(error: str, **extra: Any) -> str:
    return _json({"ok": False, "error": error, **extra})


def _ok(**data: Any) -> str:
    return _json({"ok": True, **data})


class CroAuditArea(str, Enum):
    COPY = "copy"
    DESIGN = "design"
    SPEED = "speed"
    FORM = "form"
    TRUST = "trust"


_AUDIT_CHECKLIST: dict[str, list[str]] = {
    CroAuditArea.COPY.value: [
        "Clear value proposition above the fold",
        "Single focused CTA",
        "Benefit-driven headlines",
    ],
    CroAuditArea.DESIGN.value: [
        "Mobile-responsive layout",
        "Visual hierarchy directs to CTA",
        "Contrasting CTA button",
    ],
    CroAuditArea.SPEED.value: [
        "LCP < 2.5s",
        "No render-blocking resources",
        "Image optimization",
    ],
    CroAuditArea.FORM.value: [
        "Minimal fields",
        "Inline validation",
        "Autofill support",
    ],
    CroAuditArea.TRUST.value: [
        "Social proof / testimonials",
        "Security badges",
        "Clear privacy policy link",
    ],
}


def register_cro_tools(mcp: FastMCP) -> None:
    """Register CRO-related MCP tools."""

    @mcp.tool()
    def cro_audit(
        url: str = "",
        areas: str = '["copy","design","speed","form","trust"]',
    ) -> str:
        """Return a CRO audit checklist for the given areas (proxy — no live fetch).

        ``url`` labels the checklist; use seo_audit_page for a live fetch.
        """
        try:
            area_list = json.loads(areas)
        except json.JSONDecodeError:
            return _err("'areas' must be valid JSON")
        if not isinstance(area_list, list):
            return _err("'areas' must be a JSON array")
        checks: list[dict[str, Any]] = []
        for area in area_list:
            if area not in _AUDIT_CHECKLIST:
                return _err(f"unknown audit area '{area}'")
            for item in _AUDIT_CHECKLIST[area]:
                checks.append({"area": area, "check": item, "status": "todo"})
        return _ok(
            url=url or None,
            area_count=len(area_list),
            check_count=len(checks),
            checks=checks,
            note="Static checklist (no live page fetch). Complete each check; then cro_run_experiment to validate impact.",
        )

    @mcp.tool()
    def cro_run_experiment(
        name: str,
        variant_a_conv: int,
        variant_a_samples: int,
        variant_b_conv: int,
        variant_b_samples: int,
    ) -> str:
        """Run an A/B experiment and compute statistical significance via runtime.experiment_tracker. Pure computation."""
        if err := validate_query(name):
            return err
        try:
            counts = {
                "a_conv": int(variant_a_conv), "a_vis": int(variant_a_samples),
                "b_conv": int(variant_b_conv), "b_vis": int(variant_b_samples),
            }
        except (TypeError, ValueError):
            return _err("conversion/sample counts must be integers")
        if any(v < 0 or v > 10**12 for v in counts.values()):
            return _err("conversion/sample counts must be within [0, 1e12]")
        if counts["a_conv"] > counts["a_vis"] or counts["b_conv"] > counts["b_vis"]:
            return _err("conversions cannot exceed samples")
        try:
            result = experiment_tracker.analyze_ab_test(
                a_conv=counts["a_conv"],
                a_vis=counts["a_vis"],
                b_conv=counts["b_conv"],
                b_vis=counts["b_vis"],
                confidence=0.95,
                method="z_test",
            )
        except (ValidationError, TypeError, ValueError, ZeroDivisionError) as exc:
            return _err(getattr(exc, "message", str(exc)))
        for required in ("p_a", "p_b", "z", "p_value", "srm_ok", "significant", "winner"):
            if not hasattr(result, required):
                return _err(f"experiment backend returned unexpected shape (missing {required!r})")
        return _ok(
            experiment=name,
            variant_a_rate=round(result["p_a"], 4),
            variant_b_rate=round(result["p_b"], 4),
            z_score=round(result["z"], 4),
            p_value=round(result["p_value"], 4),
            srm_ok=result["srm_ok"],
            significant=result["significant"],
            winner=result["winner"] or "inconclusive",
            note="Analyzed via runtime.experiment_tracker.",
        )

    @mcp.tool()
    def cro_create_flag(
        name: str,
        rollout_percent: int = 0,
        description: str = "",
    ) -> str:
        """Create a feature flag config via runtime.feature_flags. WRITE — gated."""
        if err := validate_query(name):
            return err
        try:
            rollout_percent = int(rollout_percent)
        except (TypeError, ValueError):
            return _err("'rollout_percent' must be an integer")
        if not 0 <= rollout_percent <= 100:
            return _err("'rollout_percent' must be 0-100")
        # Sanitize the flag key: interpolated into an evaluate_command string,
        # so quotes/slashes would break it (or worse, inject).
        key = re.sub(r"[^a-z0-9_]", "_", name.strip().lower().replace(" ", "_"))[:64].strip("_")
        if not key:
            return _err("flag name must contain alphanumeric characters")
        return _json({
            "ok": True,
            "gated": True,
            "approval_required": True,
            "flag": {
                "key": key,
                "description": description,
                "rollout_percent": rollout_percent,
                "enabled": rollout_percent > 0,
            },
            "evaluate_command": f"FeatureFlagger().evaluate(flag_name='{key}', identity='<user_id>', segments={{}}, rollout_pct={rollout_percent}) via runtime.feature_flags",
            "note": "Flag definition for runtime.feature_flags; evaluate with cro_evaluate_flag tool.",
        })

    @mcp.tool()
    def cro_evaluate_flag(
        key: str,
        identifier: str = "anonymous",
        rollout_percent: int = 0,
        segments: str = "{}",
    ) -> str:
        """Evaluate a feature flag for an identifier via runtime.feature_flags. Pure computation.

        Args:
            key: Flag name.
            identifier: Stable per-user/entity identifier.
            rollout_percent: Global rollout percentage (0-100).
            segments: JSON object of segment configs (each may have "ids" and/or "pct").
        """
        if err := validate_query(key):
            return err
        if err := validate_query(identifier):
            return err
        try:
            rollout_percent = int(rollout_percent)
        except (TypeError, ValueError):
            return _err("'rollout_percent' must be an integer")
        if not 0 <= rollout_percent <= 100:
            return _err("'rollout_percent' must be 0-100")
        try:
            segs = json.loads(segments)
        except json.JSONDecodeError:
            return _err("'segments' must be valid JSON")
        if not isinstance(segs, dict):
            return _err("'segments' must be a JSON object")
        try:
            flagger = feature_flags.FeatureFlagger()
            enabled = flagger.evaluate(
                flag_name=key,
                identity=identifier,
                segments=segs,
                rollout_pct=rollout_percent,
            )
        except (ValidationError, TypeError, ValueError, AttributeError) as exc:
            return _err(getattr(exc, "message", str(exc)))
        return _ok(
            key=key,
            identifier=identifier,
            enabled=enabled,
            rollout_percent=rollout_percent,
            note="Evaluated via runtime.feature_flags.",
        )

    @mcp.tool()
    def cro_heatmap(
        page: str,
    ) -> str:
        """Fetch/define a heatmap for a page (proxy instruction). READ/EXTERNAL."""
        if err := validate_query(page):
            return err
        return _json({
            "ok": True,
            "instruction": {
                "tool": "heatmap",
                "page": page,
                "requires_provider_env": "AIZEE_POSTHOG_TOKEN",
                "note": "Use PostHog/OpenReplay heatmap API via approved executor.",
            },
        })

    @mcp.tool()
    def cro_replay(
        session_id: str = "",
    ) -> str:
        """Fetch a session replay (proxy instruction). READ/EXTERNAL — privacy-gated."""
        return _json({
            "ok": True,
            "instruction": {
                "tool": "session_replay",
                "session_id": session_id or None,
                "requires_provider_env": "AIZEE_OPENREPLAY_TOKEN",
                "privacy_note": "Mask PII before storing replays (GDPR).",
            },
        })

    @mcp.tool()
    def cro_survey(
        question: str,
        kind: str = "multiple_choice",
        options: str = "[]",
    ) -> str:
        """Create a survey (proxy). WRITE/EXTERNAL — gated; returns survey definition."""
        if err := validate_query(question):
            return err
        if kind not in ("multiple_choice", "open_text", "rating"):
            return _err("'kind' must be multiple_choice/open_text/rating")
        try:
            opts = json.loads(options)
        except json.JSONDecodeError:
            return _err("'options' must be valid JSON")
        return _json({
            "ok": True,
            "gated": True,
            "approval_required": True,
            "survey": {
                "question": truncate(question, 300),
                "kind": kind,
                "options": opts if isinstance(opts, list) else [],
            },
            "requires_provider_env": "AIZEE_FORMBRICKS_TOKEN",
            "note": "Survey creation requires guardian approval.",
        })
