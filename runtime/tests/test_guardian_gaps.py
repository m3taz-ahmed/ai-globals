"""Gap coverage for guardian.py: regex safety, kill-switch, yaml/json loaders."""

from __future__ import annotations

import sys

import pytest

from runtime.guardian import (
    _COMPILED_REGEX_CACHE,
    _MISSING,
    ActionRequest,
    DecisionStatus,
    GuardConfig,
    Guardian,
    KillSwitchRule,
    _safe_regex_search,
    invoke,
)


class TestSafeRegex:
    def test_too_long_pattern(self):
        assert _safe_regex_search("a" * 10_000, "x") is False

    def test_too_long_input(self):
        assert _safe_regex_search("a", "x" * 200_000) is False

    def test_bad_pattern(self):
        assert _safe_regex_search("([", "x") is False

    def test_match_and_cache(self):
        _COMPILED_REGEX_CACHE.clear()
        assert _safe_regex_search(r"\d+", "abc123") is True
        assert _safe_regex_search(r"\d+", "abc") is False
        assert r"\d+" in _COMPILED_REGEX_CACHE

    def test_cache_eviction(self):
        _COMPILED_REGEX_CACHE.clear()
        import runtime.guardian as g

        for i in range(g._MAX_REGEX_CACHE_SIZE + 5):
            _safe_regex_search(f"pat{i}", "x")
        assert len(_COMPILED_REGEX_CACHE) <= g._MAX_REGEX_CACHE_SIZE

    @pytest.mark.skipif(sys.platform == "win32", reason="SIGALRM absent")
    def test_unix_timeout_path(self):
        assert _safe_regex_search("abc", "xabc") is True

    def test_windows_no_alarm(self):
        # On Windows we exercise the else-branch implicitly.
        assert _safe_regex_search("abc", "xabc") is True


class TestMissingSentinel:
    def test_falsy(self):
        assert bool(_MISSING) is False

    def test_repr(self):
        assert repr(_MISSING) == "_MISSING"

    def test_missing_never_eq(self):
        g = Guardian([{"name": "r", "predicate": {"key": "no.such", "op": "eq", "value": 1},
                       "decision": "deny"}])
        d = g.authorize(ActionRequest(tool="T", attributes={}))
        assert d.status == DecisionStatus.ALLOW  # no match -> default


class TestLoaders:
    def test_yaml_missing_file(self, tmp_path):
        with pytest.raises(ValueError):
            Guardian.from_yaml(tmp_path / "none.yaml")

    def test_yaml_bad_rules(self, tmp_path):
        f = tmp_path / "g.yaml"
        f.write_text("rules: {not: a list}")
        with pytest.raises(ValueError):
            Guardian.from_yaml(f)

    def test_json_missing_file(self, tmp_path):
        with pytest.raises(ValueError):
            Guardian.from_json(tmp_path / "none.json")

    def test_json_bad_rules(self, tmp_path):
        f = tmp_path / "g.json"
        f.write_text('{"rules": "nope"}')
        with pytest.raises(ValueError):
            Guardian.from_json(f)


class TestKillSwitch:
    def test_cost_ceiling(self):
        ks = KillSwitchRule("cost_ceiling", limit=10.0, pattern="")
        g = Guardian([], kill_switch_rules=[ks])
        d = g.authorize(ActionRequest(tool="T", attributes={"total_cost": 11.0}))
        assert d.status == DecisionStatus.DENY
        assert "kill_switch" in d.rule_name

    def test_file_touched(self):
        ks = KillSwitchRule("file_touched", limit=0, pattern="*.env")
        g = Guardian([], kill_switch_rules=[ks])
        d = g.authorize(ActionRequest(tool="T", attributes={"files_touched": ["x/.env"]}))
        assert d.status == DecisionStatus.DENY

    def test_tool_call_count(self):
        ks = KillSwitchRule("tool_call_count", limit=5, pattern="")
        g = Guardian([], kill_switch_rules=[ks])
        d = g.authorize(ActionRequest(tool="T", attributes={"tool_call_count": 5}))
        assert d.status == DecisionStatus.DENY

    def test_time_limit(self):
        ks = KillSwitchRule("time_limit", limit=60.0, pattern="")
        g = Guardian([], kill_switch_rules=[ks])
        d = g.authorize(ActionRequest(tool="T", attributes={"elapsed_seconds": 61.0}))
        assert d.status == DecisionStatus.DENY

    def test_not_triggered(self):
        ks = KillSwitchRule("cost_ceiling", limit=10.0, pattern="")
        g = Guardian([], kill_switch_rules=[ks])
        d = g.authorize(ActionRequest(tool="T", attributes={"total_cost": 1.0}))
        assert d.status == DecisionStatus.ALLOW

    def test_bad_context_fails_open(self):
        ks = KillSwitchRule("cost_ceiling", limit=10.0, pattern="")
        triggered, _ = ks.evaluate({"total_cost": "not-a-number"})
        assert triggered is False

    def test_files_not_list(self):
        ks = KillSwitchRule("file_touched", limit=0, pattern="*.env")
        triggered, _ = ks.evaluate({"files_touched": "notalist"})
        assert triggered is False


class TestInvokeArgs:
    def test_positional_args_mapped(self):
        seen = {}

        g = Guardian([{"name": "r", "tool": "fn",
                       "predicate": {"key": "path", "op": "eq", "value": "x"},
                       "decision": "deny"}])

        @invoke(g)
        def fn(path, mode="r"):
            seen["called"] = True
            return path

        import pytest as _pt

        from runtime.schemas import PolicyDeniedError
        with _pt.raises(PolicyDeniedError):
            fn("x")
        assert "called" not in seen
        assert fn("y") == "y"

    def test_async_positional_args(self):
        import asyncio

        g = Guardian([{"name": "r", "tool": "afn",
                       "predicate": {"key": "path", "op": "eq", "value": "x"},
                       "decision": "deny"}])

        @invoke(g)
        async def afn(path):
            return path

        import pytest as _pt

        from runtime.schemas import PolicyDeniedError
        with _pt.raises(PolicyDeniedError):
            asyncio.run(afn("x"))
        assert asyncio.run(afn("y")) == "y"


class TestRequireApproval:
    def test_error_approval(self):
        cfg = GuardConfig(on_evaluation_error=DecisionStatus.REQUIRE_APPROVAL)
        g = Guardian([{"name": "r", "predicate": {"key": "x", "op": "bad", "value": 1}}], cfg)
        d = g.authorize(ActionRequest(tool="T", attributes={}))
        assert d.status == DecisionStatus.REQUIRE_APPROVAL

    def test_error_allow_continues(self):
        cfg = GuardConfig(on_evaluation_error=DecisionStatus.ALLOW)
        g = Guardian([
            {"name": "bad", "predicate": {"key": "x", "op": "bad", "value": 1}},
            {"name": "ok", "decision": "deny"},
        ], cfg)
        d = g.authorize(ActionRequest(tool="T", attributes={}))
        assert d.status == DecisionStatus.DENY and d.rule_name == "ok"

    def test_invalid_decision_string(self):
        g = Guardian([{"name": "r", "decision": "bogus"}],
                     GuardConfig(on_evaluation_error=DecisionStatus.DENY))
        d = g.authorize(ActionRequest(tool="T", attributes={}))
        assert d.status == DecisionStatus.DENY
