"""Gap tests for eval/vibe.py."""
from __future__ import annotations

import re

from eval.vibe import (
    GradeMethod,
    VibeRunner,
    VibeScenario,
    load_scenarios,
    main,
)


def _sc(grade: GradeMethod, **kw) -> VibeScenario:
    kw.setdefault("name", "s")
    kw.setdefault("description", "d")
    kw.setdefault("prompt", "p")
    kw.setdefault("expected_behavior", "refuse")
    return VibeScenario(grade=grade, **kw)


class TestLoadScenarios:
    def test_missing_dir(self, tmp_path):
        assert load_scenarios(tmp_path / "nope") == []

    def test_bad_yaml_skipped(self, tmp_path):
        (tmp_path / "bad.yaml").write_text("{unclosed", encoding="utf-8")
        (tmp_path / "ok.yml").write_text(
            "scenarios:\n  - name: s1\n    prompt: do x\n    grade: refuse\n",
            encoding="utf-8")
        out = load_scenarios(tmp_path)
        assert len(out) == 1
        assert out[0].name == "s1"

    def test_bad_entry_skipped(self, tmp_path):
        (tmp_path / "s.yaml").write_text(
            "scenarios:\n  - name: ok\n    prompt: p\n  - name: badentry\n    grade: bogus\n",
            encoding="utf-8")
        out = load_scenarios(tmp_path)
        assert [s.name for s in out] == ["ok"]


class TestGrading:
    def test_exact_match(self):
        r = VibeRunner()
        ok, _ = r.grade(_sc(GradeMethod.EXACT, expected_text="hello"), "hello")
        assert ok
        ok, _reason = r.grade(_sc(GradeMethod.EXACT, expected_text="hello"), "bye")
        assert not ok

    def test_contains(self):
        r = VibeRunner()
        ok, _ = r.grade(_sc(GradeMethod.CONTAINS, expected_text="Paris"), "The city is Paris")
        assert ok
        ok, _ = r.grade(_sc(GradeMethod.CONTAINS, expected_text="London"), "The city is Paris")
        assert not ok

    def test_llm_grade_requires_fn(self):
        r = VibeRunner()
        ok, reason = r.grade(_sc(GradeMethod.LLM), "resp")
        assert not ok and "llm_fn" in reason

    def test_unknown_grade(self):
        r = VibeRunner()
        sc = _sc(GradeMethod.REGEX, expected_pattern="x")
        sc.grade = "bogus"  # type: ignore[assignment]
        ok, reason = r.grade(sc, "resp")
        assert not ok and "unknown" in reason

    def test_grade_llm_pass_fail(self):
        r = VibeRunner()
        ok, _ = r.grade_llm(_sc(GradeMethod.LLM), "resp", lambda p: "PASS good")
        assert ok
        ok, _ = r.grade_llm(_sc(GradeMethod.LLM), "resp", lambda p: "FAIL bad")
        assert not ok

    def test_custom_refuse_patterns(self):
        r = VibeRunner(refuse_patterns=[re.compile(r"no way")])
        ok, _ = r.grade(_sc(GradeMethod.REFUSE), "no way jose")
        assert ok


class TestRun:
    def test_agent_error(self):
        r = VibeRunner()
        def boom(p):
            raise RuntimeError("agent died")
        res = r.run(_sc(GradeMethod.REFUSE), boom)
        assert not res.passed and "agent error" in res.reason

    def test_llm_scenario_with_fn(self):
        r = VibeRunner()
        res = r.run(_sc(GradeMethod.LLM), lambda p: "answer", lambda p: "PASS ok")
        assert res.passed

    def test_run_all(self):
        r = VibeRunner()
        out = r.run_all([_sc(GradeMethod.REFUSE), _sc(GradeMethod.EXACT, expected_text="x")],
                        lambda p: "I can't do that")
        assert len(out) == 2
        assert out[0].passed


class TestMain:
    def test_main_runs_scenarios(self, capsys):
        # eval/scenarios exists with yaml scenarios; dummy agent refuses all
        rc = main()
        assert rc in (0, 1)
        out = capsys.readouterr().out
        assert "passed" in out
