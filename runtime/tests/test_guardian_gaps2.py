"""Second gap pass for runtime/guardian.py."""
from __future__ import annotations

from runtime.guardian import (
    Guardian,
    KillSwitchError,
    KillSwitchRule,
    _safe_regex_search,
    invoke,
)


class TestRegexSearch:
    def test_search_exception_returns_false(self):
        # bytes text -> TypeError inside search -> logged + False
        assert _safe_regex_search(r"x", b"bytes-not-str") is False  # type: ignore[arg-type]

    def test_oversized_pattern_and_input(self):
        assert _safe_regex_search("x" * 300, "x") is False
        assert _safe_regex_search(r"x", "y" * 20000) is False

    def test_bad_pattern(self):
        assert _safe_regex_search("(", "text") is False

    def test_cache_eviction(self):
        import runtime.guardian as g

        g._COMPILED_REGEX_CACHE.clear()
        for i in range(1100):
            _safe_regex_search(f"p{i}", "x")
        assert len(g._COMPILED_REGEX_CACHE) <= 1024


class TestKillSwitch:
    def test_error_construction(self):
        e = KillSwitchError("cost_ceiling", "over budget", {"k": 1})
        assert e.rule_type == "cost_ceiling"
        assert "KILL_SWITCH" in e.error_code or "cost_ceiling" in e.message
        e2 = KillSwitchError("time_limit", "slow")
        assert e2.context["rule_type"] == "time_limit"

    def test_tool_call_count_below(self):
        r = KillSwitchRule(rule_type="tool_call_count", limit=5)
        hit, msg = r.evaluate({"tool_call_count": 3})
        assert hit is False and msg == ""

    def test_tool_call_count_at_limit(self):
        r = KillSwitchRule(rule_type="tool_call_count", limit=5)
        hit, msg = r.evaluate({"tool_call_count": 5})
        assert hit is True and "exceeded" in msg

    def test_time_limit_below(self):
        r = KillSwitchRule(rule_type="time_limit", limit=60)
        hit, _msg = r.evaluate({"elapsed_seconds": 10})
        assert hit is False

    def test_time_limit_at(self):
        r = KillSwitchRule(rule_type="time_limit", limit=60)
        hit, msg = r.evaluate({"elapsed_seconds": 61.0})
        assert hit is True and "Elapsed" in msg

    def test_bad_context_fails_open(self):
        r = KillSwitchRule(rule_type="cost_ceiling", limit=5)
        hit, _ = r.evaluate({"total_cost": "not-a-float"})
        assert hit is False

    def test_file_touched_non_list(self):
        r = KillSwitchRule(rule_type="file_touched", pattern="x/*")
        hit, _ = r.evaluate({"files_touched": "notalist"})
        assert hit is False

    def test_file_touched_non_str_entry(self):
        r = KillSwitchRule(rule_type="file_touched", pattern="x/*")
        hit, _ = r.evaluate({"files_touched": [123, "safe/f.txt"]})
        assert hit is False


class TestInvokeDecorator:
    def _guardian(self):
        g = Guardian.__new__(Guardian)
        seen: list = []
        g.check = lambda req: seen.append(req.attributes)  # type: ignore[attr-defined]
        g._seen = seen  # type: ignore[attr-defined]
        return g

    def test_sync_kwargs_only(self):
        g = self._guardian()

        @invoke(g, tool="t")
        def fn(a, b):
            return a + b

        assert fn(a=1, b=2) == 3
        assert g._seen[0] == {"a": 1, "b": 2}  # type: ignore[attr-defined]

    def test_sync_positional_mapped(self):
        g = self._guardian()

        @invoke(g)
        def fn(a, b):
            return a + b

        fn(1, b=2)
        assert g._seen[0] == {"a": 1, "b": 2}  # type: ignore[attr-defined]

    def test_sync_extra_args_beyond_params(self):
        g = self._guardian()

        @invoke(g)
        def fn(a, *rest):
            return a

        fn(1, 2, 3)  # extra positional args skipped by i < len(args) bound
        assert g._seen[0]["a"] == 1  # type: ignore[attr-defined]

    def test_async_wrapper(self):
        import asyncio

        g = self._guardian()

        @invoke(g, tool="at")
        async def afn(a, b):
            return a * b

        assert asyncio.run(afn(3, b=4)) == 12
        assert g._seen[0] == {"a": 3, "b": 4}  # type: ignore[attr-defined]

    def test_default_tool_name_is_fn_name(self):
        g = self._guardian()
        captured = []
        g.check = lambda req: captured.append(req.tool)  # type: ignore[attr-defined]

        @invoke(g)
        def my_tool():
            return 1

        my_tool()
        assert captured == ["my_tool"]
