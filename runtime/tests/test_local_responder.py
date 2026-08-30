"""Tests for the deterministic local chat responder (zero LLM tokens)."""

from __future__ import annotations

from runtime.local_responder import LocalResponder


def _ctx() -> dict:
    return {
        "version": "5.10.0",
        "workflows": ["w1", "w2", "w3"],
        "rules": ["r1", "r2"],
        "guardian_rules": ["g1"],
        "skills": ["s1", "s2", "s3", "s4"],
        "budgets": ["global", "session"],
        "tech_stack": {"python": "3.10", "pytest": "8.0"},
        "personas": ["ARCH", "QA"],
    }


def test_help_intent() -> None:
    r = LocalResponder(_ctx)
    assert "help" in r.reply("help me").lower()


def test_status_intent() -> None:
    r = LocalResponder(_ctx)
    reply = r.reply("what is the status?")
    assert "5.10.0" in reply
    assert "3 workflows" in reply


def test_budget_intent() -> None:
    r = LocalResponder(_ctx)
    reply = r.reply("show me budgets")
    assert "2 active budget scope(s)" in reply


def test_budget_intent_empty() -> None:
    r = LocalResponder(lambda: {"budgets": []})
    assert "unlimited" in r.reply("budgets").lower()


def test_workflow_intent() -> None:
    r = LocalResponder(_ctx)
    reply = r.reply("list workflows")
    assert "3 registered workflow(s)" in reply
    assert "w1" in reply


def test_workflow_intent_truncates() -> None:
    ctx = _ctx()
    ctx["workflows"] = [f"w{i}" for i in range(10)]
    r = LocalResponder(lambda: ctx)
    reply = r.reply("workflows")
    assert "10 registered" in reply
    assert "+5 more" in reply


def test_rules_intent() -> None:
    r = LocalResponder(_ctx)
    reply = r.reply("how many rules?")
    assert "2 policy rule(s)" in reply
    assert "1 guardian rule(s)" in reply


def test_skills_intent() -> None:
    r = LocalResponder(_ctx)
    reply = r.reply("show skills")
    assert "4 skill(s)" in reply


def test_stack_intent() -> None:
    r = LocalResponder(_ctx)
    reply = r.reply("what tech stack?")
    assert "python" in reply
    assert "pytest" in reply


def test_unknown_intent_falls_back() -> None:
    r = LocalResponder(_ctx)
    reply = r.reply("write me a React component")
    assert "No LLM backend" in reply


def test_no_context_provider() -> None:
    r = LocalResponder()
    reply = r.reply("status")
    assert "unavailable" in reply.lower()


def test_context_provider_failure_is_safe() -> None:
    def boom() -> dict:
        raise RuntimeError("boom")
    r = LocalResponder(boom)
    reply = r.reply("status")
    assert "unavailable" in reply.lower()


def test_arabic_help_intent() -> None:
    r = LocalResponder(_ctx)
    reply = r.reply("محتاج مساعدة")
    assert "help" in reply.lower() or "مساعدة" in reply


def test_arabic_status_intent() -> None:
    r = LocalResponder(_ctx)
    reply = r.reply("ايه حالة النظام؟")
    assert "5.10.0" in reply
