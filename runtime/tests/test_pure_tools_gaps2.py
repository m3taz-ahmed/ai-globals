"""Gap coverage: pricing_calculator, post_queue, lead_scorer, error_classifier."""
from __future__ import annotations

import pytest

from runtime.error_classifier import (
    _instantiate_error,
    _truncate,
    classify_and_raise,
    classify_error,
    classify_error_with_context,
)
from runtime.lead_scorer import LeadScorer
from runtime.post_queue import PostQueue
from runtime.pricing_calculator import recommended_rate
from runtime.schemas import AizeeError, ValidationError


class TestPricing:
    def test_income_goal(self):
        with pytest.raises(ValidationError):
            recommended_rate(0, billable_hours_per_week=10)

    def test_weeks(self):
        with pytest.raises(ValidationError):
            recommended_rate(50000, weeks_per_year=0, billable_hours_per_week=10)

    def test_hours(self):
        with pytest.raises(ValidationError):
            recommended_rate(50000, billable_hours_per_week=0)

    def test_tax(self):
        with pytest.raises(ValidationError):
            recommended_rate(50000, billable_hours_per_week=10, tax_rate=1.5)

    def test_platform_fee(self):
        with pytest.raises(ValidationError):
            recommended_rate(50000, billable_hours_per_week=10, platform_fee_rate=-0.1)

    def test_utilization(self):
        with pytest.raises(ValidationError):
            recommended_rate(50000, billable_hours_per_week=10, utilization=0)

    def test_ok(self):
        out = recommended_rate(50000, billable_hours_per_week=10)
        assert out["hourly"] > 0


class TestPostQueue:
    def test_unknown_channel(self):
        with pytest.raises(ValidationError):
            PostQueue().enqueue("tiktok", "hi")

    def test_non_str_text(self):
        with pytest.raises(ValidationError):
            PostQueue().enqueue("x", 123)  # type: ignore[arg-type]

    def test_x_under_limit_ok(self):
        q = PostQueue(x_free_monthly_limit=5)
        post = q.enqueue("x", "hello")
        assert post.channel == "x"

    def test_pending_and_pop(self):
        q = PostQueue()
        assert q.pending() == []
        assert q.pop() is None
        q.enqueue("linkedin", "post")
        assert len(q.pending()) == 1
        popped = q.pop()
        assert popped is not None and popped.text == "post"


class TestLeadScorer:
    def test_empty_weights(self):
        with pytest.raises(ValidationError):
            LeadScorer(weights={})

    def test_missing_keys(self):
        with pytest.raises(ValidationError):
            LeadScorer(weights={"fit": 1.0})

    def test_extra_keys(self):
        with pytest.raises(ValidationError):
            LeadScorer(weights={"fit": 0.3, "intent": 0.3, "behavior": 0.4, "x": 0.1})

    def test_nonpositive_total(self):
        with pytest.raises(ValidationError):
            LeadScorer(weights={"fit": 0.0, "intent": 0.0, "behavior": 0.0})

    def test_sum_not_one_no_normalize(self):
        with pytest.raises(ValidationError):
            LeadScorer(weights={"fit": 0.5, "intent": 0.5, "behavior": 0.5})

    def test_sum_not_one_normalized(self):
        s = LeadScorer(weights={"fit": 1.0, "intent": 1.0, "behavior": 2.0}, normalize=True)
        assert s.score_lead(1.0, 1.0, 1.0) == 100


class TestErrorClassifier:
    def test_truncate(self):
        assert _truncate("x" * 600).endswith("...[truncated]")
        assert _truncate("short") == "short"

    def test_instantiate_base(self):
        e = _instantiate_error(AizeeError, "msg")
        assert isinstance(e, AizeeError)

    def test_instantiate_typeerror_fallback(self):
        class WeirdError(AizeeError):
            def __init__(self, only_msg):
                super(AizeeError, self).__init__()

        out = _instantiate_error(WeirdError, "m")  # type: ignore[arg-type]
        assert isinstance(out, WeirdError)

    def test_typeerror_input_caused(self):
        exc = TypeError("invalid input type")
        cls, _ = classify_error(exc)
        assert cls is ValidationError

    def test_typeerror_internal(self):
        exc = TypeError("unsupported operand")
        cls, _ = classify_error(exc)
        assert cls is AizeeError

    def test_classify_and_raise(self):
        with pytest.raises(AizeeError):
            classify_and_raise(RuntimeError("x"))

    def test_context_no_operation(self):
        e = classify_error_with_context(ValueError("bad input value"))
        assert "operation" not in e.context
        assert e.context["original_exception"] == "ValueError"

    def test_context_with_operation(self):
        e = classify_error_with_context(ValueError("bad"), operation="op")
        assert e.context["operation"] == "op"
