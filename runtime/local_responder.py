#!/usr/bin/env python3
"""Deterministic local chat responder (zero LLM tokens).

aiZee is a control plane, not an LLM. The :class:`LocalResponder` keeps
``aizee chat`` / the dashboard chat tab genuinely useful without an LLM
backend by answering common operational intents directly from live kernel
state, and by being explicit about its offline nature for anything else.

Token efficiency principle (spec.md #6): intent matching is pure regex over
kernel data — no model calls, no network, fully deterministic.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

_PREFIX = "[local] "

_INTENT_HELP = re.compile(r"\b(help|usage|commands?|مساعدة|أوامر)\b", re.IGNORECASE)
_INTENT_STATUS = re.compile(r"\b(status|health|state|حالة|صحة)\b", re.IGNORECASE)
_INTENT_BUDGET = re.compile(r"\bbudgets?\b", re.IGNORECASE)
_INTENT_WORKFLOW = re.compile(r"\bworkflows?\b", re.IGNORECASE)
_INTENT_RULES = re.compile(r"\brules?\b", re.IGNORECASE)
_INTENT_SKILLS = re.compile(r"\bskills?\b", re.IGNORECASE)
_INTENT_STACK = re.compile(r"\b(tech.?stack|stack|lockfiles?)\b", re.IGNORECASE)


class LocalResponder:
    """Answers operational intents from live kernel state.

    Args:
        context_provider: Callable returning a kernel ``status()`` dict.
            Injection keeps this module decoupled from Kernel.
    """

    def __init__(self, context_provider: Callable[[], dict[str, Any]] | None = None) -> None:
        self._context_provider = context_provider

    def _context(self) -> dict[str, Any]:
        if self._context_provider is None:
            return {}
        try:
            return self._context_provider()
        except Exception:
            return {}

    def reply(self, message: str) -> str:
        """Produce a reply for *message* from live state."""
        ctx = self._context()
        if _INTENT_HELP.search(message):
            return (
                _PREFIX + "Available intents: help · status · budgets · workflows · "
                "rules · skills · tech stack. I answer from live kernel state — "
                "I am not an LLM."
            )
        if _INTENT_STATUS.search(message):
            return _PREFIX + self._status_reply(ctx)
        if _INTENT_BUDGET.search(message):
            budgets = ctx.get("budgets") or []
            if not budgets:
                return _PREFIX + "No budget limits are configured (unlimited mode)."
            return _PREFIX + f"{len(budgets)} active budget scope(s): {', '.join(map(str, budgets))}."
        if _INTENT_WORKFLOW.search(message):
            workflows = ctx.get("workflows") or []
            sample = ", ".join(workflows[:5])
            more = f" … +{len(workflows) - 5} more" if len(workflows) > 5 else ""
            return _PREFIX + f"{len(workflows)} registered workflow(s): {sample}{more}."
        if _INTENT_RULES.search(message):
            rules = ctx.get("rules") or []
            guardian = ctx.get("guardian_rules") or []
            return _PREFIX + f"{len(rules)} policy rule(s), {len(guardian)} guardian rule(s) loaded."
        if _INTENT_SKILLS.search(message):
            skills = ctx.get("skills") or []
            return _PREFIX + f"{len(skills)} skill(s) available via 'aizee skill list'."
        if _INTENT_STACK.search(message):
            stack = ctx.get("tech_stack") or {}
            names = ", ".join(sorted(stack)) or "none detected"
            return _PREFIX + f"Detected tech stack: {names}."
        return (
            _PREFIX + "No LLM backend configured — I answer operational intents only "
            "(try 'help'). Use Context7 MCP or your IDE assistant for code questions."
        )

    def _status_reply(self, ctx: dict[str, Any]) -> str:
        if not ctx:
            return "Kernel state unavailable (provider not wired or failed)."
        parts = [
            f"v{ctx.get('version', '?')}",
            f"{len(ctx.get('workflows') or [])} workflows",
            f"{len(ctx.get('rules') or [])} policy rules",
            f"{len(ctx.get('personas') or [])} personas",
            f"{len(ctx.get('skills') or [])} skills",
        ]
        return "Status: " + " · ".join(parts) + "."
