#!/usr/bin/env python3
"""Deterministic work-size classifier — zero LLM tokens.

Gives the agent a heuristic second opinion for the ``trivial | standard |
complex`` call. The agent still states its own classification and reason;
both are recorded, and disagreements are flagged in the audit trail.
"""

from __future__ import annotations

import re
from typing import Any

from runtime.task_contract.models import Classification

# (pattern, weight) — score accumulates toward standard/complex.
_NONTRIVIAL_SIGNALS: tuple[tuple[str, float], ...] = (
    # multi-file / multi-module intent
    (r"\b(files?|modules?|endpoints?|tables?|components?|pages?)\b.{0,40}\b(and|,|و)\b", 2.0),
    # build verbs — any work verb means at least "standard"
    (r"\b(build|implement|create|add|refactor|migrate|integrate|scaffold|design)\b", 1.5),
    (r"(اعمل|انفذ|ضيف|ابني|صمم|رح|عدل|نفذ)", 1.5),
    # risk-bearing domains
    (r"\b(auth|payment|billing|migration|deploy|security|secret|token|database|schema)\b", 2.0),
    # explicit multi-step language
    (r"\b(then|after that|step by step|workflow|pipeline|and also)\b", 1.5),
    (r"(وبعد كده|وبعدين|خطوة بخطوة|كلهم|كل ده)", 1.5),
)

_TRIVIAL_SIGNALS: tuple[str, ...] = (
    r"\b(typo|rename|comment|docstring|whitespace|formatting|lint fix)\b",
    r"\b(fix (this|the) (line|typo|import))\b",
    r"(صحح|غير اسم|رينيم|تعديل بسيط)",
)

_COMPLEX_SIGNALS: tuple[str, ...] = (
    r"\b(architect|system|platform|from scratch|greenfield|rewrite)\b",
    r"(معماري|سيستم|من الصفر)",
)

# Enumerated item lists imply multi-task work.
_LIST_SIGNAL = re.compile(r"(\n\s*[-*\d]+[.)]\s)|([,،]\s*\S+[,،]\s*\S+[,،])")

STANDARD_THRESHOLD = 1.5
COMPLEX_THRESHOLD = 4.0
LONG_PROMPT_WORDS = 80


def classify_prompt(prompt: str) -> dict[str, Any]:
    """Classify a work prompt's decomposition needs.

    Returns ``{"level", "score", "signals", "reason"}``. ``trivial`` means the
    work may proceed without a plan; anything else requires decomposition.
    """
    text = prompt.strip()
    if not text:
        return {
            "level": Classification.TRIVIAL.value,
            "score": 0.0,
            "signals": ["empty-prompt"],
            "reason": "empty or whitespace-only prompt",
        }

    lowered = text.lower()
    signals: list[str] = []
    score = 0.0
    for pattern, weight in _NONTRIVIAL_SIGNALS:
        if re.search(pattern, lowered):
            score += weight
            signals.append(f"signal:{weight:g}")

    if len(lowered.split()) > LONG_PROMPT_WORDS:
        score += 1.5
        signals.append("long-prompt")
    if _LIST_SIGNAL.search(text):
        score += 1.5
        signals.append("enumerated-items")

    trivial_hit = any(re.search(p, lowered) for p in _TRIVIAL_SIGNALS)
    if trivial_hit and score < STANDARD_THRESHOLD * 1.34:
        return {
            "level": Classification.TRIVIAL.value,
            "score": score,
            "signals": ["trivial-marker"],
            "reason": "trivial markers matched and non-trivial score is low",
        }

    if any(re.search(p, lowered) for p in _COMPLEX_SIGNALS):
        score += 2.0
        signals.append("complex-marker")

    if score >= COMPLEX_THRESHOLD:
        level = Classification.COMPLEX
        reason = "multiple strong non-trivial signals"
    elif score >= STANDARD_THRESHOLD:
        level = Classification.STANDARD
        reason = "non-trivial signals present"
    else:
        level = Classification.TRIVIAL
        reason = "no decomposition signals"

    return {"level": level.value, "score": score, "signals": signals, "reason": reason}
