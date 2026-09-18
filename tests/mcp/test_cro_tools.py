"""Tests for aizee_mcp/tools/cro_tools.py MCP tools."""

from __future__ import annotations

import json
from typing import Any

import pytest

from aizee_mcp.tools.cro_tools import register_cro_tools  # pyright: ignore[reportMissingImports]
from runtime import experiment_tracker

pytestmark = pytest.mark.mcp


# --- Helper to capture tool functions from a fake MCP ----------------------


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
    """Register tools on a fresh fake MCP and return the named tool function."""
    _captured_tools.clear()
    fake = _FakeMCP()
    register_cro_tools(fake)
    return _captured_tools[name]


def _parse(result: str) -> dict[str, Any]:
    return json.loads(result)


# ---------------------------------------------------------------------------
# cro_audit
# ---------------------------------------------------------------------------


class TestCroAudit:
    def test_default_areas(self):
        out = _parse(_get_tool("cro_audit")())
        assert out["ok"] is True
        assert out["area_count"] == 5
        assert out["check_count"] == 15
        assert len(out["checks"]) == 15
        assert out["url"] is None

    def test_single_area(self):
        out = _parse(_get_tool("cro_audit")(areas='["copy"]'))
        assert out["ok"] is True
        assert out["area_count"] == 1
        assert out["check_count"] == 3
        assert all(c["area"] == "copy" for c in out["checks"])

    def test_url_label(self):
        out = _parse(_get_tool("cro_audit")(url="https://x.test"))
        assert out["url"] == "https://x.test"

    def test_invalid_json(self):
        out = _parse(_get_tool("cro_audit")(areas="not-json"))
        assert out["ok"] is False
        assert "valid JSON" in out["error"]

    def test_non_array(self):
        out = _parse(_get_tool("cro_audit")(areas='{"a":1}'))
        assert out["ok"] is False
        assert "JSON array" in out["error"]

    def test_unknown_area(self):
        out = _parse(_get_tool("cro_audit")(areas='["nope"]'))
        assert out["ok"] is False
        assert "unknown audit area" in out["error"]


# ---------------------------------------------------------------------------
# cro_run_experiment
# ---------------------------------------------------------------------------


class TestCroRunExperiment:
    def test_happy_significant(self):
        out = _parse(
            _get_tool("cro_run_experiment")(
                name="cta", variant_a_conv=50, variant_a_samples=1000,
                variant_b_conv=90, variant_b_samples=1000,
            )
        )
        assert out["ok"] is True
        assert out["experiment"] == "cta"
        assert out["winner"] == "B"
        assert out["significant"] is True
        assert "p_value" in out and "z_score" in out

    def test_happy_inconclusive(self):
        out = _parse(
            _get_tool("cro_run_experiment")(
                name="tie", variant_a_conv=50, variant_a_samples=1000,
                variant_b_conv=52, variant_b_samples=1000,
            )
        )
        assert out["ok"] is True
        assert out["winner"] == "inconclusive"
        assert out["significant"] is False

    def test_empty_name(self):
        out = _parse(_get_tool("cro_run_experiment")(name="", variant_a_conv=1,
                                                     variant_a_samples=10, variant_b_conv=1,
                                                     variant_b_samples=10))
        assert out["ok"] is False

    def test_non_integer_counts(self):
        out = _parse(_get_tool("cro_run_experiment")(name="x", variant_a_conv="a",
                                                     variant_a_samples=10, variant_b_conv=1,
                                                     variant_b_samples=10))
        assert out["ok"] is False
        assert "integers" in out["error"]

    def test_negative_counts(self):
        out = _parse(_get_tool("cro_run_experiment")(name="x", variant_a_conv=-1,
                                                     variant_a_samples=10, variant_b_conv=1,
                                                     variant_b_samples=10))
        assert out["ok"] is False
        assert "[0, 1e12]" in out["error"]

    def test_conv_exceeds_samples(self):
        out = _parse(_get_tool("cro_run_experiment")(name="x", variant_a_conv=20,
                                                     variant_a_samples=10, variant_b_conv=1,
                                                     variant_b_samples=10))
        assert out["ok"] is False
        assert "exceed" in out["error"]

    def test_zero_visitors_backend_error(self):
        out = _parse(_get_tool("cro_run_experiment")(name="x", variant_a_conv=0,
                                                     variant_a_samples=0, variant_b_conv=1,
                                                     variant_b_samples=10))
        assert out["ok"] is False
        assert "positive" in out["error"]

    def test_backend_bad_shape(self, monkeypatch: pytest.MonkeyPatch):
        class _Bad:
            pass

        monkeypatch.setattr(experiment_tracker, "analyze_ab_test", lambda **kw: _Bad())
        out = _parse(_get_tool("cro_run_experiment")(name="x", variant_a_conv=1,
                                                     variant_a_samples=10, variant_b_conv=1,
                                                     variant_b_samples=10))
        assert out["ok"] is False
        assert "unexpected shape" in out["error"]


# ---------------------------------------------------------------------------
# cro_create_flag
# ---------------------------------------------------------------------------


class TestCroCreateFlag:
    def test_happy(self):
        out = _parse(_get_tool("cro_create_flag")(name="New Checkout", rollout_percent=25,
                                                  description="test flag"))
        assert out["ok"] is True
        assert out["gated"] is True
        flag = out["flag"]
        assert flag["key"] == "new_checkout"
        assert flag["rollout_percent"] == 25
        assert flag["enabled"] is True
        assert "new_checkout" in out["evaluate_command"]

    def test_zero_rollout_disabled(self):
        out = _parse(_get_tool("cro_create_flag")(name="flag", rollout_percent=0))
        assert out["flag"]["enabled"] is False

    def test_empty_name(self):
        out = _parse(_get_tool("cro_create_flag")(name=""))
        assert out["ok"] is False

    def test_non_int_rollout(self):
        out = _parse(_get_tool("cro_create_flag")(name="flag", rollout_percent="x"))
        assert out["ok"] is False
        assert "integer" in out["error"]

    def test_rollout_out_of_range(self):
        out = _parse(_get_tool("cro_create_flag")(name="flag", rollout_percent=150))
        assert out["ok"] is False
        assert "0-100" in out["error"]

    def test_unsanitizable_name(self):
        out = _parse(_get_tool("cro_create_flag")(name="!!!"))
        assert out["ok"] is False
        assert "alphanumeric" in out["error"]


# ---------------------------------------------------------------------------
# cro_evaluate_flag
# ---------------------------------------------------------------------------


class TestCroEvaluateFlag:
    def test_full_rollout_enabled(self):
        out = _parse(_get_tool("cro_evaluate_flag")(key="flag", rollout_percent=100))
        assert out["ok"] is True
        assert out["enabled"] is True

    def test_zero_rollout_disabled(self):
        out = _parse(_get_tool("cro_evaluate_flag")(key="flag", rollout_percent=0))
        assert out["enabled"] is False

    def test_segment_ids_match(self):
        out = _parse(_get_tool("cro_evaluate_flag")(
            key="flag", identifier="u1", rollout_percent=0,
            segments='{"beta": {"ids": ["u1"]}}'))
        assert out["enabled"] is True

    def test_empty_key(self):
        out = _parse(_get_tool("cro_evaluate_flag")(key=""))
        assert out["ok"] is False

    def test_non_int_rollout(self):
        out = _parse(_get_tool("cro_evaluate_flag")(key="f", rollout_percent="x"))
        assert out["ok"] is False

    def test_rollout_out_of_range(self):
        out = _parse(_get_tool("cro_evaluate_flag")(key="f", rollout_percent=-5))
        assert out["ok"] is False

    def test_bad_segments_json(self):
        out = _parse(_get_tool("cro_evaluate_flag")(key="f", segments="nope"))
        assert out["ok"] is False
        assert "valid JSON" in out["error"]

    def test_non_dict_segments(self):
        out = _parse(_get_tool("cro_evaluate_flag")(key="f", segments="[1]"))
        assert out["ok"] is False
        assert "JSON object" in out["error"]


# ---------------------------------------------------------------------------
# cro_heatmap / cro_replay / cro_survey
# ---------------------------------------------------------------------------


class TestCroProxies:
    def test_heatmap_happy(self):
        out = _parse(_get_tool("cro_heatmap")(page="/pricing"))
        assert out["ok"] is True
        assert out["instruction"]["tool"] == "heatmap"
        assert out["instruction"]["page"] == "/pricing"

    def test_heatmap_empty_page(self):
        out = _parse(_get_tool("cro_heatmap")(page=""))
        assert out["ok"] is False

    def test_replay_happy(self):
        out = _parse(_get_tool("cro_replay")(session_id="s1"))
        assert out["ok"] is True
        assert out["instruction"]["tool"] == "session_replay"
        assert out["instruction"]["session_id"] == "s1"

    def test_replay_empty_id(self):
        out = _parse(_get_tool("cro_replay")())
        assert out["instruction"]["session_id"] is None


class TestCroSurvey:
    def test_happy(self):
        out = _parse(_get_tool("cro_survey")(question="Rate us", kind="rating",
                                             options='["1","2"]'))
        assert out["ok"] is True
        assert out["gated"] is True
        assert out["survey"]["kind"] == "rating"
        assert out["survey"]["options"] == ["1", "2"]

    def test_empty_question(self):
        out = _parse(_get_tool("cro_survey")(question=""))
        assert out["ok"] is False

    def test_bad_kind(self):
        out = _parse(_get_tool("cro_survey")(question="q", kind="weird"))
        assert out["ok"] is False
        assert "multiple_choice" in out["error"]

    def test_bad_options_json(self):
        out = _parse(_get_tool("cro_survey")(question="q", options="nope"))
        assert out["ok"] is False
        assert "valid JSON" in out["error"]

    def test_non_list_options_becomes_empty(self):
        out = _parse(_get_tool("cro_survey")(question="q", options='{"a":1}'))
        assert out["ok"] is True
        assert out["survey"]["options"] == []
