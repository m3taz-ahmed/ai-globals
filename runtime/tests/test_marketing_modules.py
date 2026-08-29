from __future__ import annotations

from runtime import (
    attribution_model,
    billing_ledger,
    crm_manager,
    drip_engine,
    experiment_tracker,
    feature_flags,
    funnel_tracker,
    lead_scorer,
    marketing_compliance,
    pipeline_analytics,
    post_queue,
    pricing_calculator,
)


def test_pricing_calculator_recommended_rate():
    rate = pricing_calculator.recommended_rate(
        income_goal=120000,
        weeks_per_year=48,
        billable_hours_per_week=30,
        expenses_yearly=20000,
        tax_rate=0.2,
        platform_fee_rate=0.1,
        utilization=0.8,
    )
    assert isinstance(rate, dict)
    assert rate["hourly"] > 0


def test_attribution_model_all_models():
    tps = [
        {"channel": "organic", "ts": 1},
        {"channel": "paid", "ts": 2},
        {"channel": "referral", "ts": 3},
    ]
    for fn in (
        attribution_model.last_click,
        attribution_model.first_click,
        attribution_model.linear,
        attribution_model.position_based,
    ):
        result = fn(tps)
        assert isinstance(result, dict)
        assert abs(sum(result.values()) - 1.0) < 1e-6


def test_experiment_tracker_analyze_ab_test():
    res = experiment_tracker.analyze_ab_test(
        a_conv=120, a_vis=1000, b_conv=140, b_vis=1000, confidence=0.95, method="z_test"
    )
    assert isinstance(res, dict)
    assert 0.0 <= res["p_value"] <= 1.0


def test_lead_scorer():
    s = lead_scorer.score_lead(fit=0.8, intent=0.6, behavior=0.4)
    assert isinstance(s, (int, float))
    assert 0.0 <= s <= 100.0
    assert isinstance(lead_scorer.LeadScorer(), lead_scorer.LeadScorer)


def test_marketing_compliance():
    r = marketing_compliance.check_compliance(
        channel="email", has_optin=True, has_unsubscribe=True, is_gdpr=True
    )
    assert isinstance(r, tuple)
    assert r[0] is True


def test_feature_flags_bucket_is_stable():
    b1 = feature_flags._bucket("launch", "user-1")
    b2 = feature_flags._bucket("launch", "user-1")
    assert b1 == b2
    assert isinstance(b1, int)
    assert 0 <= b1 <= 100


def test_class_instantiation_smoke():
    assert isinstance(drip_engine.DripEngine(), drip_engine.DripEngine)
    assert isinstance(funnel_tracker.Funnel("signup"), funnel_tracker.Funnel)
    assert isinstance(
        post_queue.PostQueue(char_limits={"x": 280}, x_free_monthly_limit=10),
        post_queue.PostQueue,
    )
    assert isinstance(pipeline_analytics.PipelineAnalytics(), pipeline_analytics.PipelineAnalytics)


def test_modules_importable():
    for mod in (
        pricing_calculator,
        billing_ledger,
        drip_engine,
        experiment_tracker,
        feature_flags,
        attribution_model,
        funnel_tracker,
        post_queue,
        lead_scorer,
        pipeline_analytics,
        marketing_compliance,
        crm_manager,
    ):
        assert mod is not None
