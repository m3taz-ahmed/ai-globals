"""Agent gateway — runtime interception of LLM/MCP requests and responses.

Sits on the request/response path every prompt and tool call traverses.
Applies pre-LLM guardrails (inspect outbound prompt + tool payloads) and
post-execution guardrails (inspect generated code + tool responses) before
they reach the developer or are acted upon.

Each guardrail produces one of three verdicts:
- ALLOW  — request/response passes unchanged.
- REDACT — sensitive content removed; request still completes.
- BLOCK  — request/response rejected entirely.

Inspired by Fiddler's LLM/MCP gateway pattern: "a policy written in a
document is not enforcement; controls only hold where they sit on the
agent's request and response path."
"""

from __future__ import annotations

import logging
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity, GateVerdict

_logger = logging.getLogger(__name__)


class Verdict(str, Enum):
    """Guardrail verdict on a request or response."""

    ALLOW = "allow"
    REDACT = "redact"
    BLOCK = "block"


class GuardrailPhase(str, Enum):
    """When a guardrail runs relative to the LLM call."""

    PRE_LLM = "pre_llm"
    POST_EXECUTION = "post_execution"


@dataclass
class GuardrailContext:
    """Input to a guardrail check."""

    prompt: str = ""
    tool_name: str = ""
    tool_payload: dict[str, Any] | None = None
    response: str = ""
    generated_code: str = ""
    agent_id: str = ""
    user_id: str = ""
    session_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardrailResult:
    """Output of a guardrail check."""

    verdict: Verdict
    guardrail_name: str
    reason: str = ""
    redacted_fields: list[str] = field(default_factory=list)
    severity: ErrorSeverity = ErrorSeverity.MEDIUM

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "guardrail": self.guardrail_name,
            "reason": self.reason,
            "redacted_fields": list(self.redacted_fields),
            "severity": self.severity.value,
        }

    def to_gate_verdict(self) -> GateVerdict:
        """Convert to unified GateVerdict (EVAL-W0).

        REDACT requires spans; we synthesize placeholder spans from
        redacted_fields since the gateway doesn't track char offsets.
        """
        if self.verdict is Verdict.BLOCK:
            return GateVerdict.block(
                "agent_gateway", self.reason, guardrail=self.guardrail_name, severity=self.severity.value
            )
        if self.verdict is Verdict.REDACT:
            spans = tuple((0, 0, f) for f in self.redacted_fields)
            return GateVerdict.redact(
                "agent_gateway",
                self.reason,
                spans=spans,
                guardrail=self.guardrail_name,
                redacted_fields=list(self.redacted_fields),
            )
        return GateVerdict.allow(
            "agent_gateway", self.reason, guardrail=self.guardrail_name
        )


# A guardrail is a callable: context → result.
GuardrailFn = Callable[[GuardrailContext], GuardrailResult]


class GatewayError(AizeeError):
    """Raised when the gateway encounters an internal error."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("GATEWAY_ERROR", message, ErrorSeverity.HIGH, context)


# -- Built-in guardrails ----------------------------------------------------

_SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(sk-[a-zA-Z0-9]{20,})"),  # OpenAI-style keys
    re.compile(r"(?i)(ghp_[a-zA-Z0-9]{36})"),  # GitHub PATs
    re.compile(r"(?i)(gho_[a-zA-Z0-9]{36})"),  # GitHub OAuth tokens
    re.compile(r"(?i)(ghs_[a-zA-Z0-9]{36})"),  # GitHub app tokens
    re.compile(r"(?i)(AKIA[A-Z0-9]{16})"),  # AWS access keys
    re.compile(r"(?i)(-----BEGIN [A-Z ]*PRIVATE KEY-----)"),  # private keys
    re.compile(r"(?i)(password\s*[=:]\s*\S+)"),  # password assignments
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*['\"]?[a-zA-Z0-9_\-]{20,})"),  # API keys
]
_REDACTED = "[REDACTED]"


def _redact_secrets(text: str) -> tuple[str, list[str]]:
    """Redact known secret patterns. Returns (redacted_text, matched_names)."""
    matched: list[str] = []
    out = text
    for pat in _SENSITIVE_PATTERNS:
        if pat.search(out):
            matched.append(pat.pattern[:40])
            out = pat.sub(_REDACTED, out)
    return out, matched


def secret_leak_guardrail(ctx: GuardrailContext) -> GuardrailResult:
    """Block/redact secrets in prompts and responses."""
    text = "\n".join(t for t in (ctx.prompt, ctx.response, ctx.generated_code) if t)
    _redacted, matched = _redact_secrets(text)
    if not matched:
        return GuardrailResult(Verdict.ALLOW, "secret_leak")
    if ctx.prompt:
        return GuardrailResult(
            Verdict.BLOCK, "secret_leak",
            reason=f"Secret pattern detected in prompt: {matched}",
            severity=ErrorSeverity.CRITICAL,
        )
    return GuardrailResult(
        Verdict.REDACT, "secret_leak",
        reason=f"Secret redacted in response: {matched}",
        redacted_fields=matched,
        severity=ErrorSeverity.HIGH,
    )


def prompt_injection_guardrail(ctx: GuardrailContext) -> GuardrailResult:
    """Detect common prompt-injection patterns in tool responses."""
    if not ctx.response:
        return GuardrailResult(Verdict.ALLOW, "prompt_injection")
    lowered = ctx.response.lower()
    indicators = [
        "ignore previous instructions",
        "ignore all previous",
        "disregard the above",
        "you are now a",
        "new instructions:",
        "system prompt:",
    ]
    hits = [i for i in indicators if i in lowered]
    if hits:
        return GuardrailResult(
            Verdict.BLOCK, "prompt_injection",
            reason=f"Injection indicators: {hits}",
            severity=ErrorSeverity.HIGH,
        )
    return GuardrailResult(Verdict.ALLOW, "prompt_injection")


def destructive_command_guardrail(ctx: GuardrailContext) -> GuardrailResult:
    """Block destructive shell commands in generated code/tool payloads.

    NOTE (substring blocklist limits): matching is plain case-insensitive
    substring search, so it can false-positive on prose/docs (e.g. "sudo "
    in a tutorial) and false-negative on obfuscation (quoting, env vars,
    base64, unicode tricks). Treat BLOCKs as heuristic signals, not a
    sandbox guarantee.
    """
    code = ctx.generated_code or ""
    payload = ctx.tool_payload or {}
    text = code + " " + str(payload.get("command", ""))
    destructive = [
        "rm -rf /", "rm -rf ~", "mkfs", "dd if=/dev/zero",
        ":(){:|:&};:", "drop database", "truncate table",
        "git push --force", "git push -f", "git reset --hard",
        "chmod 777", "chown ", "sudo ", "curl ", "wget ",
    ]
    lowered = text.lower()
    hits = [d for d in destructive if d in lowered]
    if hits:
        return GuardrailResult(
            Verdict.BLOCK, "destructive_command",
            reason=f"Destructive pattern: {hits}",
            severity=ErrorSeverity.CRITICAL,
        )
    return GuardrailResult(Verdict.ALLOW, "destructive_command")


_BUILTIN_GUARDRAILS: dict[str, tuple[GuardrailPhase, GuardrailFn]] = {
    "secret_leak": (GuardrailPhase.PRE_LLM, secret_leak_guardrail),
    "prompt_injection": (GuardrailPhase.POST_EXECUTION, prompt_injection_guardrail),
    "destructive_command": (GuardrailPhase.POST_EXECUTION, destructive_command_guardrail),
}


class AgentGateway:
    """Runtime gateway that intercepts LLM/MCP requests and responses.

    Pre-LLM guardrails inspect the outbound prompt + tool payloads.
    Post-execution guardrails inspect the inbound response + generated code.
    The most severe verdict wins (BLOCK > REDACT > ALLOW).
    """

    def __init__(self) -> None:
        self._guardrails: dict[str, tuple[GuardrailPhase, GuardrailFn]] = dict(
            _BUILTIN_GUARDRAILS
        )
        self._lock = threading.Lock()
        self._verdict_log: list[dict[str, Any]] = []

    def register(
        self, name: str, phase: GuardrailPhase, fn: GuardrailFn
    ) -> None:
        with self._lock:
            self._guardrails[name] = (phase, fn)

    def unregister(self, name: str) -> bool:
        with self._lock:
            return self._guardrails.pop(name, None) is not None

    def list_guardrails(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {"name": n, "phase": p.value}
                for n, (p, _) in self._guardrails.items()
            ]

    def _severity_rank(self, v: Verdict) -> int:
        rank = {Verdict.ALLOW: 0, Verdict.REDACT: 1, Verdict.BLOCK: 2}.get(v)
        if rank is None:
            raise GatewayError(f"Unknown verdict: {v!r}")
        return rank

    def _run_phase(
        self, phase: GuardrailPhase, ctx: GuardrailContext
    ) -> tuple[Verdict, list[GuardrailResult]]:
        results: list[GuardrailResult] = []
        with self._lock:
            items = [(n, fn) for n, (p, fn) in self._guardrails.items() if p == phase]
        for name, fn in items:
            try:
                res = fn(ctx)
                results.append(res)
            except Exception as exc:
                _logger.debug("guardrail %s failed: %s", name, exc, exc_info=True)
                results.append(GuardrailResult(
                    Verdict.BLOCK, name,
                    reason=f"Guardrail error: {exc}",
                    severity=ErrorSeverity.HIGH,
                ))
        if not results:
            return Verdict.ALLOW, results
        worst = max(results, key=lambda r: self._severity_rank(r.verdict))
        return worst.verdict, results

    def check_request(self, ctx: GuardrailContext) -> tuple[Verdict, list[GuardrailResult]]:
        """Run pre-LLM guardrails on an outbound request."""
        verdict, results = self._run_phase(GuardrailPhase.PRE_LLM, ctx)
        self._log("request", verdict, results, ctx)
        return verdict, results

    def check_response(self, ctx: GuardrailContext) -> tuple[Verdict, list[GuardrailResult]]:
        """Run post-execution guardrails on an inbound response."""
        verdict, results = self._run_phase(GuardrailPhase.POST_EXECUTION, ctx)
        self._log("response", verdict, results, ctx)
        return verdict, results

    def _log(
        self, direction: str, verdict: Verdict,
        results: list[GuardrailResult], ctx: GuardrailContext,
    ) -> None:
        sanitized_results = []
        for r in results:
            d = r.to_dict()
            # Redact only actual secret payloads (e.g. key assignments),
            # not every reason that merely mentions "secret"/"pattern".
            reason = d.get("reason", "")
            if isinstance(reason, str) and reason:
                redacted_reason, _ = _redact_secrets(reason)
                d["reason"] = redacted_reason
            sanitized_results.append(d)
        entry: dict[str, Any] = {
            "direction": direction,
            "verdict": verdict.value,
            "agent_id": ctx.agent_id,
            "user_id": ctx.user_id,
            "tool": ctx.tool_name,
            "results": sanitized_results,
        }
        with self._lock:
            self._verdict_log.append(entry)
            if len(self._verdict_log) > 1000:
                self._verdict_log = self._verdict_log[-500:]

    def verdict_log(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._verdict_log[-limit:])

    def clear_log(self) -> None:
        with self._lock:
            self._verdict_log.clear()


__all__ = [
    "AgentGateway",
    "GatewayError",
    "GuardrailContext",
    "GuardrailFn",
    "GuardrailPhase",
    "GuardrailResult",
    "Verdict",
    "destructive_command_guardrail",
    "prompt_injection_guardrail",
    "secret_leak_guardrail",
]
