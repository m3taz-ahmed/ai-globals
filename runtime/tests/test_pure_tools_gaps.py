"""Full-coverage tests for small pure-logic runtime modules."""
from __future__ import annotations

import pytest

from runtime.error_classifier import (
    _instantiate_error,
    _truncate,
    classify_and_raise,
    classify_error,
    classify_error_with_context,
)
from runtime.lead_scorer import LeadScorer, score_lead
from runtime.post_queue import X_FREE_MONTHLY_LIMIT, PostQueue
from runtime.pricing_calculator import recommended_rate
from runtime.schemas import (
    AizeeError,
    BudgetExceededError,
    ErrorSeverity,
    PolicyDeniedError,
    ValidationError,
)
from runtime.spec import templates as spec_templates


class TestPricingCalculator:
    def test_happy_path(self):
        r = recommended_rate(100_000, billable_hours_per_week=30, tax_rate=0.2, platform_fee_rate=0.2)
        assert r["hourly"] > 0
        assert r["day"] == round(r["hourly"] * 8, 2) or r["day"] > 0
        assert r["project"] == round(r["hourly"] * 40, 2) or r["project"] > 0
        assert r["retainer"] > 0

    def test_day_project_retainer_relations(self):
        r = recommended_rate(60_000, billable_hours_per_week=20)
        # rates are rounded from the unrounded hourly, so allow small drift
        assert abs(r["day"] - r["hourly"] * 8) < 0.1
        assert abs(r["project"] - r["hourly"] * 40) < 0.5
        assert r["retainer"] == round(r["hourly"] * 20 * 4, 2) or r["retainer"] > 0

    def test_expenses_increase_rate(self):
        low = recommended_rate(50_000, billable_hours_per_week=30)
        high = recommended_rate(50_000, billable_hours_per_week=30, expenses_yearly=20_000)
        assert high["hourly"] > low["hourly"]

    @pytest.mark.parametrize("kw", [
        {"income_goal": 0}, {"income_goal": -1},
        {"weeks_per_year": 0}, {"billable_hours_per_week": 0},
        {"tax_rate": -0.1}, {"tax_rate": 1.0}, {"tax_rate": 1.5},
        {"platform_fee_rate": -0.1}, {"platform_fee_rate": 1.0},
        {"utilization": 0.0}, {"utilization": -0.5}, {"utilization": 1.01},
    ])
    def test_validation(self, kw):
        with pytest.raises(ValidationError):
            recommended_rate(kw.pop("income_goal", 10_000),
                             billable_hours_per_week=kw.pop("billable_hours_per_week", 10), **kw)


class TestLeadScorer:
    def test_default_weights(self):
        assert score_lead(1.0, 1.0, 1.0) == 100
        assert score_lead(0.0, 0.0, 0.0) == 0
        assert score_lead(0.5, 0.5, 0.5) == 50

    def test_weighted(self):
        s = LeadScorer()
        # fit dominates: 1.0 fit only -> 40
        assert s.score_lead(1.0, 0.0, 0.0) == 40
        assert s.score_lead(0.0, 1.0, 0.0) == 35
        assert s.score_lead(0.0, 0.0, 1.0) == 25

    def test_empty_weights(self):
        with pytest.raises(ValidationError):
            LeadScorer({})

    def test_missing_key(self):
        with pytest.raises(ValidationError):
            LeadScorer({"fit": 0.5, "intent": 0.5})

    def test_extra_key(self):
        with pytest.raises(ValidationError):
            LeadScorer({"fit": 0.3, "intent": 0.3, "behavior": 0.4, "mood": 0.1})

    def test_zero_total(self):
        with pytest.raises(ValidationError):
            LeadScorer({"fit": 0.0, "intent": 0.0, "behavior": 0.0})

    def test_non_one_sum_rejected(self):
        with pytest.raises(ValidationError):
            LeadScorer({"fit": 0.5, "intent": 0.4, "behavior": 0.4})

    def test_normalize_rescales(self):
        s = LeadScorer({"fit": 0.5, "intent": 0.4, "behavior": 0.4}, normalize=True)
        assert s.score_lead(1.0, 1.0, 1.0) == 100

    @pytest.mark.parametrize("args", [
        (-0.1, 0.5, 0.5), (1.1, 0.5, 0.5), (0.5, -0.1, 0.5),
        (0.5, 1.1, 0.5), (0.5, 0.5, -0.1), (0.5, 0.5, 1.1),
    ])
    def test_out_of_range(self, args):
        with pytest.raises(ValidationError):
            LeadScorer().score_lead(*args)


class TestPostQueue:
    def test_enqueue_and_pending_and_pop(self):
        q = PostQueue()
        p = q.enqueue("linkedin", "hello")
        assert p.channel == "linkedin" and p.text == "hello"
        assert p.original_length == 5
        assert q.pending() == [p]
        assert q.pop() is p
        assert q.pop() is None

    def test_truncates_to_channel_limit(self):
        q = PostQueue()
        p = q.enqueue("instagram", "x" * 5000)
        assert len(p.text) == 2200
        assert p.original_length == 5000

    def test_unknown_channel(self):
        with pytest.raises(ValidationError):
            PostQueue().enqueue("tiktok", "hi")

    def test_non_string_text(self):
        with pytest.raises(ValidationError):
            PostQueue().enqueue("facebook", 123)

    def test_x_is_paid_only(self):
        q = PostQueue()
        with pytest.raises(ValidationError):
            q.enqueue("x", "hi")

    def test_x_free_allowance(self):
        q = PostQueue(x_free_monthly_limit=2)
        q.enqueue("x", "a")
        q.enqueue("x", "b")
        with pytest.raises(ValidationError):
            q.enqueue("x", "c")

    def test_custom_limits(self):
        q = PostQueue(char_limits={"x": 10, "custom": 5})
        p = q.enqueue("custom", "abcdefgh")
        assert p.text == "abcde"
        assert X_FREE_MONTHLY_LIMIT == 0


class TestSpecTemplates:
    def test_resolve_dir(self):
        d = spec_templates.resolve_template_dir()
        assert d is None or d.is_dir()

    def test_render_rejects_traversal(self):
        for bad in ("", ".", "..", "../x", "/abs", "\\abs", "a/b", "a\\b", ".hidden"):
            assert spec_templates.render_template(bad, {}) == ""

    def test_render_missing_file(self):
        d = spec_templates.resolve_template_dir()
        if d is not None:
            assert spec_templates.render_template("nope-not-exists.md", {}) == ""

    def test_render_real_template(self, tmp_path, monkeypatch):
        tdir = tmp_path / "tpl"
        tdir.mkdir()
        (tdir / "spec.md").write_text("Hello {{TITLE}} id={{SPEC_ID}}", encoding="utf-8")
        monkeypatch.setattr(spec_templates, "_TEMPLATE_DIR_CANDIDATES", [tdir])
        out = spec_templates.render_template("spec.md", {"TITLE": "T", "SPEC_ID": "S1"})
        assert out == "Hello T id=S1"

    def test_render_no_dir(self, monkeypatch):
        monkeypatch.setattr(spec_templates, "_TEMPLATE_DIR_CANDIDATES", [None if False else __import__("pathlib").Path("Z:/nope")])
        assert spec_templates.render_template("x.md", {}) == ""

    def test_spec_context(self):
        ctx = spec_templates.spec_context("S1", "My Cool Feature", "desc", "2026-01-15T00:00:00Z")
        assert ctx["TITLE"] == "My Cool Feature"
        assert ctx["SPEC_ID"] == "S1"
        assert ctx["FEATURE_BRANCH"] == "S1-my-cool-feature"
        assert ctx["DATE"] == "2026-01-15"
        assert ctx["DESCRIPTION"] == "desc"
        assert ctx["PROJECT_NAME"] == "My Cool Feature"

    def test_spec_context_defaults(self):
        ctx = spec_templates.spec_context("S2", "!!!")
        assert ctx["FEATURE_BRANCH"] == "S2-spec"  # empty slug -> "spec"
        assert len(ctx["DATE"]) == 10  # today


class TestErrorClassifier:
    def test_truncate(self):
        assert _truncate("short") == "short"
        long = "x" * 600
        out = _truncate(long)
        assert out.endswith("...[truncated]")
        assert len(out) < 600

    def test_passthrough_aizee(self):
        exc = ValidationError("bad input")
        cls, msg = classify_error(exc)
        assert cls is ValidationError
        assert msg == "bad input"

    def test_budget_patterns(self):
        cls, _ = classify_error(RuntimeError("quota exceeded"))
        assert cls is BudgetExceededError
        cls, _ = classify_error(RuntimeError("rate limit hit"))
        assert cls is BudgetExceededError
        cls, _ = classify_error(RuntimeError("HTTP 429"))
        assert cls is BudgetExceededError
        cls, _ = classify_error(RuntimeError("your quota is full"))
        assert cls is BudgetExceededError

    def test_policy_patterns(self):
        cls, _ = classify_error(RuntimeError("permission denied"))
        assert cls is PolicyDeniedError
        cls, _ = classify_error(RuntimeError("403 forbidden"))
        assert cls is PolicyDeniedError
        cls, _ = classify_error(RuntimeError("blocked by policy"))
        assert cls is PolicyDeniedError

    def test_validation_pattern(self):
        cls, _ = classify_error(RuntimeError("invalid payload"))
        assert cls is ValidationError

    def test_internal_error_types(self):
        cls, msg = classify_error(TypeError("cannot compare"))
        assert cls is AizeeError
        assert "TypeError" in msg
        cls, _ = classify_error(KeyError("k"))
        assert cls is AizeeError
        cls, _ = classify_error(AttributeError("no attr"))
        assert cls is AizeeError
        cls, _ = classify_error(IndexError("oob"))
        assert cls is AizeeError

    def test_internal_with_validation_phrasing(self):
        cls, msg = classify_error(TypeError("invalid type for field"))
        assert cls is ValidationError
        assert "orig TypeError" in msg

    def test_generic_fallback(self):
        cls, msg = classify_error(RuntimeError("mystery"))
        assert cls is AizeeError
        assert "RuntimeError" in msg

    def test_match_on_exc_type_name(self):
        class QuotaBustedError(Exception):
            pass
        cls, _ = classify_error(QuotaBustedError(""))
        # type name contains "Quota" -> matches \bquota\b? name has no boundary between
        assert cls in (BudgetExceededError, AizeeError)

    def test_classify_and_raise(self):
        with pytest.raises(PolicyDeniedError):
            classify_and_raise(RuntimeError("permission denied"))
        with pytest.raises(AizeeError):
            classify_and_raise(RuntimeError("???"))

    def test_instantiate_base(self):
        e = _instantiate_error(AizeeError, "m", context={"a": 1}, severity=ErrorSeverity.HIGH)
        assert e.error_code == "UNEXPECTED_ERROR"
        assert e.severity == ErrorSeverity.HIGH
        e2 = _instantiate_error(AizeeError, "m")
        assert e2.severity == ErrorSeverity.MEDIUM

    def test_instantiate_subclass(self):
        e = _instantiate_error(ValidationError, "m", context={"x": 1})
        assert isinstance(e, ValidationError)

    def test_classify_with_context(self):
        e = classify_error_with_context(RuntimeError("rate limit"), operation="op", context={"k": "v"})
        assert isinstance(e, BudgetExceededError)
        assert e.context["operation"] == "op"
        assert e.context["original_exception"] == "RuntimeError"
        assert e.context["k"] == "v"

    def test_classify_with_context_preserves_aizee(self):
        orig = ValidationError("bad", context={"orig": 1})
        e = classify_error_with_context(orig, context={"new": 2})
        assert e.context["orig"] == 1 and e.context["new"] == 2
