"""Tests for eval/vibe.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval.vibe import (
    GradeMethod,
    VibeRunner,
    VibeScenario,
    load_scenarios,
)


@pytest.fixture
def runner() -> VibeRunner:
    return VibeRunner()


@pytest.fixture
def refuse_scenario() -> VibeScenario:
    return VibeScenario(
        name="test_refuse",
        description="test",
        prompt="do something bad",
        expected_behavior="refuse",
        grade=GradeMethod.REFUSE,
    )


class TestGrading:
    def test_refuse_pass(self, runner: VibeRunner, refuse_scenario: VibeScenario):
        passed, _ = runner.grade(refuse_scenario, "I can't help with that.")
        assert passed is True

    def test_refuse_fail(self, runner: VibeRunner, refuse_scenario: VibeScenario):
        passed, _ = runner.grade(refuse_scenario, "Sure, here's how to do it.")
        assert passed is False

    def test_regex_pass(self, runner: VibeRunner):
        s = VibeScenario(
            name="r", description="", prompt="", expected_behavior="",
            grade=GradeMethod.REGEX, expected_pattern=r"\berror\b",
        )
        passed, _ = runner.grade(s, "an error occurred")
        assert passed is True

    def test_regex_fail(self, runner: VibeRunner):
        s = VibeScenario(
            name="r", description="", prompt="", expected_behavior="",
            grade=GradeMethod.REGEX, expected_pattern=r"\berror\b",
        )
        passed, _ = runner.grade(s, "all good")
        assert passed is False

    def test_contains_pass(self, runner: VibeRunner):
        s = VibeScenario(
            name="c", description="", prompt="", expected_behavior="",
            grade=GradeMethod.CONTAINS, expected_text="login",
        )
        passed, _ = runner.grade(s, "Here is the login form")
        assert passed is True

    def test_exact_pass(self, runner: VibeRunner):
        s = VibeScenario(
            name="e", description="", prompt="", expected_behavior="",
            grade=GradeMethod.EXACT, expected_text="yes",
        )
        passed, _ = runner.grade(s, "yes")
        assert passed is True

    def test_llm_without_fn_fails(self, runner: VibeRunner):
        s = VibeScenario(
            name="l", description="", prompt="", expected_behavior="",
            grade=GradeMethod.LLM,
        )
        passed, reason = runner.grade(s, "response")
        assert passed is False
        assert "llm_fn" in reason

    def test_llm_with_fn(self, runner: VibeRunner):
        s = VibeScenario(
            name="l", description="", prompt="", expected_behavior="refuse",
            grade=GradeMethod.LLM,
        )
        def fake_llm(prompt: str) -> str:
            return "PASS — correct refusal"
        passed, _ = runner.grade_llm(s, "I refuse", fake_llm)
        assert passed is True


class TestRunScenarios:
    def test_run_refuse_scenario(self, runner: VibeRunner, refuse_scenario: VibeScenario):
        def agent(prompt: str) -> str:
            return "I can't do that."
        result = runner.run(refuse_scenario, agent)
        assert result.passed is True
        assert result.latency_ms >= 0  # mock agent returns instantly; just check field exists

    def test_run_agent_error(self, runner: VibeRunner, refuse_scenario: VibeScenario):
        def agent(prompt: str) -> str:
            raise RuntimeError("boom")
        result = runner.run(refuse_scenario, agent)
        assert result.passed is False
        assert "agent error" in result.reason


class TestLoadScenarios:
    def test_load_from_directory(self, tmp_path: Path):
        (tmp_path / "test.yaml").write_text(
            "scenarios:\n"
            "  - name: t1\n"
            "    prompt: hi\n"
            "    expected_behavior: refuse\n"
            "    grade: refuse\n"
            "  - name: t2\n"
            "    prompt: hi\n"
            "    grade: contains\n"
            "    expected_text: hello\n",
            encoding="utf-8",
        )
        scenarios = load_scenarios(tmp_path)
        assert len(scenarios) == 2
        assert scenarios[0].name == "t1"
        assert scenarios[1].grade is GradeMethod.CONTAINS

    def test_empty_directory(self, tmp_path: Path):
        assert load_scenarios(tmp_path) == []

    def test_missing_directory(self):
        assert load_scenarios(Path("/nonexistent")) == []

    def test_malformed_skipped(self, tmp_path: Path):
        (tmp_path / "bad.yaml").write_text(
            "scenarios:\n"
            "  - name: ok\n"
            "    prompt: hi\n"
            "    grade: refuse\n"
            "  - prompt: missing name\n"  # malformed
            "  - name: bad\n"
            "    grade: explode\n",  # invalid enum
            encoding="utf-8",
        )
        scenarios = load_scenarios(tmp_path)
        assert len(scenarios) == 1
        assert scenarios[0].name == "ok"


class TestRealScenarios:
    """Verify the shipped scenario files load cleanly."""

    def test_security_scenarios_load(self):
        # eval/tests/test_vibe.py -> eval/scenarios/
        root = Path(__file__).resolve().parent.parent
        scenarios = load_scenarios(root / "scenarios")
        assert len(scenarios) >= 5
        names = {s.name for s in scenarios}
        assert "prompt_injection_ignore" in names
