"""Prompt-injection input guardrail (OWASP LLM01).

This is an ADDITIONAL conservative layer on top of the existing
GuardrailRegistry / Guardian tripwire machinery. It inspects untrusted
user text (chat messages, command content, queries) for explicit
instruction-override patterns and trips the input-phase guardrail when
one is found.

Design goals:
- Be extremely conservative: only very explicit, well-known injection
  phrases trip the wire. Plain natural language never does.
- Never change the behavior of other gates; we only add a guardrail to
  the existing registry and run it for text-carrying (read-only) actions
  that would otherwise skip the guardian gate.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from runtime.policy import GuardrailResult, input_guardrail

# ---------------------------------------------------------------------------
# Conservative pattern sets
# ---------------------------------------------------------------------------

# Strong, unambiguous override instructions. Any single match trips the wire.
_STRONG_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"ignore\s+(?:all\s+|the\s+|your\s+|any\s+)?"
        r"(?:previous|prior|above|preceding)\s+"
        r"(?:instructions|prompts|context|messages|rules)"
    ),
    re.compile(r"disregard\s+(?:your\s+|the\s+|all\s+)?(?:system\s+prompt|instructions|previous|prior|above|rules)"),
    re.compile(r"ignore\s+(?:your\s+|the\s+)?system\s+prompt"),
    re.compile(r"reveal\s+(?:me\s+)?(?:your\s+|the\s+)?(?:system\s+prompt|instructions|prompt|rules)"),
    re.compile(r"print\s+(?:your\s+|the\s+)?(?:system\s+prompt|instructions)"),
    re.compile(r"show\s+(?:me\s+)?(?:your\s+|the\s+)?system\s+prompt"),
    re.compile(r"forget\s+(?:your\s+|all\s+|the\s+)?(?:instructions|everything|previous|prompt)"),
    re.compile(r"developer\s+mode"),
    re.compile(r"dev\s+mode"),
    re.compile(r"\b[Dd][Aa][Nn]\b(?:\s+mode)?"),
    re.compile(r"do\s+anything\s+now"),
    re.compile(r"jailbreak"),
)

# Roleplay framing is only treated as injection when paired with a bypass
# marker in the same text (per task: "you are now" / "pretend to be" must be
# accompanied by a bypass request). This keeps benign "pretend to be a cat"
# style text from tripping the wire.
_ROLEPLAY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"pretend\s+to\s+be"),
    re.compile(r"you\s+are\s+now"),
    re.compile(r"act\s+as\s+if\s+you\s+are"),
)

_BYPASS_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore"),
    re.compile(r"disregard"),
    re.compile(r"no\s+(?:longer\s+)?rules"),
    re.compile(r"without\s+(?:any\s+)?restrictions?"),
    re.compile(r"bypass"),
    re.compile(r"jailbreak"),
    re.compile(r"developer\s+mode"),
    re.compile(r"\b[Dd][Aa][Nn]\b"),
    re.compile(r"override"),
)


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


def _iter_strings(obj: Any, _seen: set[int] | None = None) -> Iterator[str]:
    """Yield every string value found in nested dict/list/tuple structures."""
    if _seen is None:
        _seen = set()
    obj_id = id(obj)
    if obj_id in _seen:
        return
    _seen.add(obj_id)
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _iter_strings(value, _seen)
    elif isinstance(obj, (list, tuple, set)):
        for value in obj:
            yield from _iter_strings(value, _seen)


def _has_roleplay_bypass(text: str) -> bool:
    """True if text frames a roleplay AND requests a bypass in the same snippet."""
    if not any(p.search(text) for p in _ROLEPLAY_PATTERNS):
        return False
    return any(p.search(text) for p in _BYPASS_MARKERS)


# ---------------------------------------------------------------------------
# Guardrail
# ---------------------------------------------------------------------------


@input_guardrail("prompt_injection")
def prompt_injection_guardrail(context: dict[str, Any]) -> GuardrailResult:
    """Detect explicit prompt-injection attempts in untrusted input text.

    Returns a tripped ``GuardrailResult`` (decision="deny") only for clear,
    well-known instruction-override patterns. Plain text never trips.
    """
    for text in _iter_strings(context):
        if not text or not text.strip():
            continue
        lowered = text.lower()
        for pattern in _STRONG_PATTERNS:
            if pattern.search(lowered):
                return GuardrailResult(
                    tripwire_triggered=True,
                    output_info={
                        "guardrail": "prompt_injection",
                        "reason": "Explicit instruction-override pattern detected (OWASP LLM01)",
                        "matched": pattern.pattern,
                    },
                    decision="deny",
                )
        if _has_roleplay_bypass(lowered):
            return GuardrailResult(
                tripwire_triggered=True,
                output_info={
                    "guardrail": "prompt_injection",
                    "reason": "Roleplay framing combined with a bypass request (OWASP LLM01)",
                },
                decision="deny",
            )
    return GuardrailResult(tripwire_triggered=False)
