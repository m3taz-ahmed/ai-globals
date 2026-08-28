#!/usr/bin/env python3
"""Tool-output sanitizer — prevents indirect prompt injection via tool results.

When an AI agent calls a tool (MCP server, web fetch, file read, shell
command), the output re-enters the LLM's context window. If that output
contains injected instructions (e.g., a malicious web page the agent
fetched, a poisoned file it read), the agent may follow them — this is
**indirect prompt injection**, the dominant attack vector in 2024-2026.

This module sits between tool execution and context re-entry:

    tool.execute() → raw_output → ToolOutputSanitizer.sanitize() → safe_output → context

The sanitizer:
1.  Runs the output through :class:`InjectionDetector` (all 13 techniques).
2.  If injection is detected, applies :class:`DefensiveInjector` to wrap
    the output in a data fence with defensive counter-instructions.
3.  Returns the sanitized output with a verdict for audit logging.

Usage::

    from runtime.tool_output_sanitizer import ToolOutputSanitizer

    sanitizer = ToolOutputSanitizer()
    result = sanitizer.sanitize(raw_tool_output, tool_name="web_fetch")
    if result.was_sanitized:
        logger.warning("Indirect injection blocked in %s: %s", tool_name, result.reason)
    safe_output = result.sanitized_output
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from runtime.defensive_injection import DefenseResult, DefensiveInjector
from runtime.injection_detector import InjectionDetector, InjectionVerdict


@dataclass(frozen=True)
class ToolSanitizeResult:
    """Result of sanitizing a tool output.

    Attributes:
        tool_name: Name of the tool that produced the output.
        original_output: The raw tool output (unmodified).
        sanitized_output: The output to place in the context window.
        was_sanitized: True if the output was modified/defended.
        verdict: The injection-detection verdict.
        defense: The defensive injection result (if applied).
        reason: Human-readable summary.
    """

    tool_name: str
    original_output: str
    sanitized_output: str
    was_sanitized: bool
    verdict: InjectionVerdict
    defense: DefenseResult | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "tool_name": self.tool_name,
            "was_sanitized": self.was_sanitized,
            "reason": self.reason,
            "verdict": self.verdict.to_dict(),
            "defense": self.defense.to_dict() if self.defense else None,
            "original_length": len(self.original_output),
            "sanitized_length": len(self.sanitized_output),
        }


class ToolOutputSanitizer:
    """Sanitizes tool outputs before they re-enter the LLM context window.

    This closes the indirect-prompt-injection attack vector: when an agent
    fetches a web page, reads a file, or receives a tool response, the
    content is scanned for all 13 injection techniques. If found, the
    output is wrapped in a defensive data fence.
    """

    # Tools whose outputs are most likely to carry indirect injection
    HIGH_RISK_TOOLS: ClassVar[frozenset[str]] = frozenset({
        "web_fetch", "fetch_url", "browse", "search", "web_search",
        "read_file", "file_read", "cat",
        "http_get", "http_request", "curl",
        "mcp_call", "tool_call",
        "email_read", "inbox",
        "git_log", "git_diff", "git_show",
        "issue_read", "pr_read", "comment_read",
    })

    MAX_OUTPUT_LENGTH: ClassVar[int] = 200_000

    def __init__(
        self,
        detector: InjectionDetector | None = None,
        injector: DefensiveInjector | None = None,
    ) -> None:
        self._detector = detector or InjectionDetector()
        self._injector = injector or DefensiveInjector()

    def sanitize(
        self,
        output: str,
        *,
        tool_name: str = "unknown",
        force_scan: bool = False,
    ) -> ToolSanitizeResult:
        """Sanitize a tool output before it re-enters the context window.

        Args:
            output: The raw tool output.
            tool_name: Name of the tool (for risk assessment + logging).
            force_scan: If True, always scan even for low-risk tools.

        Returns:
            A :class:`ToolSanitizeResult` with the safe output.
        """
        if not output or not output.strip():
            return ToolSanitizeResult(
                tool_name=tool_name,
                original_output=output or "",
                sanitized_output=output or "",
                was_sanitized=False,
                verdict=InjectionVerdict(text=""),
                reason="empty output",
            )

        bounded = output[: self.MAX_OUTPUT_LENGTH]

        # Skip scanning for low-risk tools unless forced (perf optimization)
        should_scan = force_scan or tool_name.lower() in self.HIGH_RISK_TOOLS
        if not should_scan:
            # Still do a quick check for the most critical patterns
            verdict = self._detector.detect(bounded, scan_encodings=False)
        else:
            verdict = self._detector.detect(bounded, scan_encodings=True)

        if not verdict.is_injection and not verdict.is_suspicious:
            return ToolSanitizeResult(
                tool_name=tool_name,
                original_output=output,
                sanitized_output=output,
                was_sanitized=False,
                verdict=verdict,
                reason="clean",
            )

        # Injection detected — apply defensive injection
        defense = self._injector.inject(bounded, verdict)
        return ToolSanitizeResult(
            tool_name=tool_name,
            original_output=output,
            sanitized_output=defense.hardened_prompt,
            was_sanitized=True,
            verdict=verdict,
            defense=defense,
            reason=f"indirect injection detected in {tool_name}: {verdict.reason}",
        )

    def sanitize_batch(
        self, outputs: list[str], tool_names: list[str] | None = None
    ) -> list[ToolSanitizeResult]:
        """Sanitize multiple tool outputs."""
        if tool_names is None:
            tool_names = ["unknown"] * len(outputs)
        if len(outputs) != len(tool_names):
            raise ValueError("outputs and tool_names must have the same length")
        return [self.sanitize(o, tool_name=tn) for o, tn in zip(outputs, tool_names, strict=True)]
