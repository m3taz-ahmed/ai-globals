"""Guardrails package.

Importing this package registers the bundled input/output guardrails into
the default ``GuardrailRegistry`` (auto-registration via decorators).
"""

from __future__ import annotations

from runtime.guardrails.prompt_injection import prompt_injection_guardrail

__all__ = ["prompt_injection_guardrail"]
