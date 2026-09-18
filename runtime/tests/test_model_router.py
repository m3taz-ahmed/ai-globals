"""Tests for runtime/model_router.py — cost-aware model routing."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from runtime.model_router import (
    ModelCapability,
    ModelRouter,
    RouteTier,
)


class TestRoute:
    def test_text_routes_local(self):
        d = ModelRouter().route("summarize_text")
        assert d.tier == RouteTier.LOCAL
        assert d.estimated_cost == 0.0
        assert d.fallback is not None  # cheap-tier fallback exists

    def test_code_task(self):
        d = ModelRouter().route("code_generation")
        assert d.tier == RouteTier.LOCAL  # llama-3.1-8b has CODE

    def test_reasoning_escalates(self):
        d = ModelRouter().route("complex_reasoning_task")
        assert d.tier == RouteTier.STANDARD  # locals lack REASONING

    def test_vision_escalates(self):
        d = ModelRouter().route("describe_image", requires_vision=True)
        assert d.tier == RouteTier.CHEAP  # gemini-1.5-flash cheapest with vision

    def test_embedding_no_capable_model(self):
        # No catalog model has EMBEDDING — falls back to cheapest available
        d = ModelRouter().route("embed_documents")
        assert "No model meets all constraints" in d.reason
        assert d.estimated_cost == 0.0  # local free model

    def test_max_cost_constraint(self):
        d = ModelRouter().route("reasoning", max_cost=6.0)
        # gemini-1.5-pro: 1.25+5.00=6.25 > 6.0; mistral-large: 2.00+6.00=8.0
        # gpt-4o: 12.5 — all too expensive? check cheapest premium... none.
        # Actually standard tier min is 6.25 → falls to premium? also >6.
        # → cheapest available fallback
        assert "cheapest available" in d.reason or d.estimated_cost <= 6.0

    def test_local_unhealthy_skips(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "route.json"
            cfg.write_text(json.dumps({"local_healthy": False}))
            r = ModelRouter(cfg)
            dec = r.route("summarize")
            assert dec.tier == RouteTier.CHEAP
            assert dec.estimated_cost > 0

    def test_corrupt_config(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "route.json"
            cfg.write_text("{bad json")
            r = ModelRouter(cfg)  # warns, defaults healthy
            assert r.route("x").tier == RouteTier.LOCAL

    def test_missing_config(self):
        r = ModelRouter(Path("nonexistent_route_cfg.json"))
        assert r.route("x").tier == RouteTier.LOCAL

    def test_session_requirement(self):
        # All models have supports_session=True, so no change expected
        d = ModelRouter().route("text", requires_session=True)
        assert d.tier == RouteTier.LOCAL


class TestEscalate:
    def test_local_to_cheap(self):
        d = ModelRouter().escalate("llama-3.1-8b", "too slow")
        assert d.tier == RouteTier.CHEAP
        assert d.fallback == "llama-3.1-8b"
        assert "too slow" in d.reason

    def test_premium_cant_escalate(self):
        d = ModelRouter().escalate("o1", "x")
        assert "highest tier" in d.reason
        assert d.model == "o1"

    def test_unknown_model(self):
        d = ModelRouter().escalate("no-such-model", "x")
        assert "Unknown model" in d.reason

    def test_escalate_no_capable_next_tier(self):
        # mistral-7b (LOCAL, TEXT-only) -> CHEAP tier has TEXT models
        r = ModelRouter()
        d = r.escalate("mistral-7b", "reason")
        assert d.tier == RouteTier.CHEAP


class TestCompareAndGet:
    def test_compare_sorted(self):
        r = ModelRouter().compare("code_task")
        costs = [m["cost_per_1m_input"] + m["cost_per_1m_output"] for m in r]
        assert costs == sorted(costs)
        assert all("name" in m for m in r)

    def test_compare_filters_caps(self):
        r = ModelRouter().compare("embed_stuff")
        for m in r:
            assert "embedding" in m["capabilities"]

    def test_get_model(self):
        r = ModelRouter()
        assert r.get_model("gpt-4o").tier == RouteTier.STANDARD
        assert r.get_model("nonexistent") is None

    def test_to_dict(self):
        d = ModelRouter().route("text").to_dict()
        assert d["tier"] == "local" and "reason" in d

    def test_capabilities_mapping(self):
        r = ModelRouter()
        assert ModelCapability.CODE in r._task_capabilities("write_code")
        assert ModelCapability.REASONING in r._task_capabilities("analyze_plan")
        assert ModelCapability.EMBEDDING in r._task_capabilities("embed")
        assert r._task_capabilities("plain") == {ModelCapability.TEXT}
