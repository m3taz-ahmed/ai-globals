"""Tests for eval.prompt_injection_suite — defense effectiveness measurement."""

from __future__ import annotations

import pytest

from eval.prompt_injection_suite import (
    EvalReport,
    PromptInjectionEvalSuite,
)
from runtime.injection_detector import InjectionTechnique


@pytest.fixture
def suite() -> PromptInjectionEvalSuite:
    return PromptInjectionEvalSuite()


def test_suite_runs(suite: PromptInjectionEvalSuite) -> None:
    report = suite.run()
    assert isinstance(report, EvalReport)
    assert report.total_attacks > 0
    assert report.total_benign > 0


def test_detection_rate_above_threshold(suite: PromptInjectionEvalSuite) -> None:
    report = suite.run()
    # We expect at least 65% detection rate for the deterministic detector
    assert report.detection_rate >= 0.65, (
        f"Detection rate too low: {report.detection_rate:.1%}. "
        f"Missed: {report.missed_attacks[:5]}"
    )


def test_false_positive_rate_below_threshold(suite: PromptInjectionEvalSuite) -> None:
    report = suite.run()
    # We expect less than 20% false positive rate
    assert report.false_positive_rate <= 0.20, (
        f"False positive rate too high: {report.false_positive_rate:.1%}. "
        f"FPs: {report.false_positive_cases[:5]}"
    )


def test_containment_rate_above_threshold(suite: PromptInjectionEvalSuite) -> None:
    report = suite.run()
    # Containment = defensive injector produced safe output for detected attacks
    assert report.containment_rate >= 0.90, (
        f"Containment rate too low: {report.containment_rate:.1%}"
    )


def test_all_13_techniques_tested(suite: PromptInjectionEvalSuite) -> None:
    techniques_in_corpus = {c.technique for c in suite.ATTACK_CORPUS}
    expected = {
        InjectionTechnique.DIRECT_OVERRIDE,
        InjectionTechnique.SYSTEM_PROMPT_EXTRACTION,
        InjectionTechnique.ROLEPLAY_JAILBREAK,
        InjectionTechnique.MULTI_TURN_MANIPULATION,
        InjectionTechnique.ENCODING_OBFUSCATION,
        InjectionTechnique.TYPOGLYCEMIA,
        InjectionTechnique.BEST_OF_N,
        InjectionTechnique.HTML_MARKDOWN_INJECTION,
        InjectionTechnique.MULTIMODAL_INJECTION,
        InjectionTechnique.RAG_POISONING,
        InjectionTechnique.TOOL_ABUSE,
        InjectionTechnique.THOUGHT_INJECTION,
        InjectionTechnique.MEMORY_POISONING,
    }
    assert expected.issubset(techniques_in_corpus), (
        f"Missing techniques in corpus: {expected - techniques_in_corpus}"
    )


def test_per_technique_stats(suite: PromptInjectionEvalSuite) -> None:
    report = suite.run()
    assert len(report.per_technique) >= 13
    for _tech_name, stats in report.per_technique.items():
        assert "total" in stats
        assert "detected" in stats
        assert stats["total"] > 0
        assert stats["detected"] <= stats["total"]


def test_report_summary(suite: PromptInjectionEvalSuite) -> None:
    report = suite.run()
    summary = report.summary()
    assert "Detection rate" in summary
    assert "False positive rate" in summary
    assert "Containment rate" in summary


def test_report_to_dict(suite: PromptInjectionEvalSuite) -> None:
    report = suite.run()
    d = report.to_dict()
    assert "detection_rate" in d
    assert "false_positive_rate" in d
    assert "containment_rate" in d
    assert "per_technique" in d


def test_benign_corpus_has_hard_negatives() -> None:
    # Hard negatives: benign inputs that contain injection-like words
    hard_negatives = [
        c for c in PromptInjectionEvalSuite.BENIGN_CORPUS
        if any(w in c.text.lower() for w in ["ignore", "system", "rules", "act as", "override", "bypass"])
    ]
    assert len(hard_negatives) >= 5, "Need more hard-negative benign cases"
