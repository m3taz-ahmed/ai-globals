#!/usr/bin/env python3
"""Information flow control via taint labels (inspired by LLMFirewall).

Provides a lattice-based taint tracking system that prevents untrusted
content (user input, RAG chunks, tool output) from flowing into trusted
contexts (system prompts, tool calls, file writes) without explicit
sanitization.

Taint labels form a lattice with the following ordering (lowest to highest):

    SYSTEM_TRUSTED < TOOL_OUTPUT < RAG_UNTRUSTED < USER_UNTRUSTED < SECRET

The core policy is **no-write-down**: a value with label L may only be
written to a context with label M if L <= M (i.e., the destination is at
least as untrusted as the source). This prevents, for example, RAG-injected
content from authorizing tool calls (RAG_UNTRUSTED cannot flow into
SYSTEM_TRUSTED).

Usage::

    from runtime.taint import TaintError, TaintLabel, TaintTracker

    tracker = TaintTracker()
    tracker.label("system_prompt", TaintLabel.SYSTEM_TRUSTED)
    tracker.label("user_msg", TaintLabel.USER_UNTRUSTED)
    tracker.label("rag_chunk", TaintLabel.RAG_UNTRUSTED)

    # Check if user_msg can flow into system_prompt — should be denied
    if not tracker.can_flow("user_msg", "system_prompt"):
        raise TaintError("USER_UNTRUSTED cannot flow into SYSTEM_TRUSTED")

    # Sanitize before flow
    tracker.sanitize("rag_chunk", target=TaintLabel.SYSTEM_TRUSTED)
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity

# Content-based secret detection patterns. Used by sanitize() to prevent
# downgrading a value that looks like a secret even if it was not initially
# labeled as SECRET (mislabeling protection).
_SECRET_CONTENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)sk-[a-zA-Z0-9]{20,}"),        # OpenAI-style keys
    re.compile(r"(?i)ghp_[a-zA-Z0-9]{36}"),        # GitHub PATs
    re.compile(r"AKIA[A-Z0-9]{16}"),               # AWS access keys
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),  # PEM private keys
    re.compile(r"(?i)(?:password|passwd|pwd)\s*[=:]\s*\S+"),  # password assignments
    re.compile(r"(?i)(?:api[_-]?key|apikey)\s*[=:]\s*['\"]?[a-zA-Z0-9_\-]{20,}"),
)


def _looks_like_secret(value: Any) -> bool:
    """Heuristic check: does the value's content match a known secret pattern?"""
    if not isinstance(value, str):
        return False
    return any(pat.search(value) for pat in _SECRET_CONTENT_PATTERNS)


class TaintLabel(IntEnum):
    """Taint labels ordered from most trusted to most sensitive.

    The integer value encodes the lattice ordering: a value with label L
    may flow to a context with label M iff ``L <= M``.
    """

    SYSTEM_TRUSTED = 0   # System prompt, guardrails — highest trust
    TOOL_OUTPUT = 1      # Output from MCP tools — semi-trusted
    RAG_UNTRUSTED = 2    # Retrieved chunks — untrusted (injection risk)
    USER_UNTRUSTED = 3   # User input — untrusted (prompt injection)
    SECRET = 4           # Secrets/PII — must never leak


class TaintError(AizeeError):
    """Raised when an information-flow policy is violated."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("TAINT_VIOLATION", message, ErrorSeverity.CRITICAL, context)


@dataclass
class TaintEntry:
    """A tracked value with its taint label and optional sanitization history."""

    label: TaintLabel
    original_label: TaintLabel
    sanitized: bool = False
    sanitization_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class TaintTracker:
    """Track taint labels for named values and enforce no-write-down.

    Thread-safe. Each value is identified by a string key. Values can be
    labeled, relabeled (via sanitization), and checked for flow legality.
    """

    def __init__(self, *, allow_sanitization: bool = True) -> None:
        self._entries: dict[str, TaintEntry] = {}
        self._allow_sanitization = allow_sanitization
        self._lock = threading.RLock()
        self._violations: list[dict[str, Any]] = []

    def label(
        self,
        key: str,
        label: TaintLabel,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Assign a taint label to a named value."""
        with self._lock:
            self._entries[key] = TaintEntry(
                label=label,
                original_label=label,
                metadata=metadata or {},
            )

    def label_value(
        self,
        key: str,
        value: Any,
        label: TaintLabel,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Assign a taint label to a named value, scanning content for secrets.

        If the value's content matches a known secret pattern, the label is
        automatically promoted to SECRET and a ``contains_secret`` flag is
        set in metadata. This prevents mislabeled secrets from being
        downgraded via sanitize().
        """
        meta = dict(metadata or {})
        if _looks_like_secret(value):
            label = TaintLabel.SECRET
            meta["contains_secret"] = True
        with self._lock:
            self._entries[key] = TaintEntry(
                label=label,
                original_label=label,
                metadata=meta,
            )

    def get_label(self, key: str) -> TaintLabel | None:
        """Return the current taint label for a key, or None if unknown."""
        with self._lock:
            entry = self._entries.get(key)
            return entry.label if entry else None

    def can_flow(self, source_key: str, dest_key: str) -> bool:
        """Check if source value can flow into destination context.

        Returns True iff ``source.label <= dest.label`` (no-write-down).
        """
        with self._lock:
            src = self._entries.get(source_key)
            dst = self._entries.get(dest_key)
            if src is None or dst is None:
                return False
            return src.label <= dst.label

    def check_flow(self, source_key: str, dest_key: str) -> None:
        """Raise TaintViolation if source cannot flow into destination."""
        if not self.can_flow(source_key, dest_key):
            with self._lock:
                src = self._entries.get(source_key)
                dst = self._entries.get(dest_key)
                src_label = src.label.name if src else "UNKNOWN"
                dst_label = dst.label.name if dst else "UNKNOWN"
                violation = {
                    "source": source_key,
                    "dest": dest_key,
                    "source_label": src_label,
                    "dest_label": dst_label,
                }
                self._violations.append(violation)
            raise TaintError(
                f"{src_label} cannot flow into {dst_label}",
                context=violation,
            )

    def sanitize(
        self,
        key: str,
        target: TaintLabel = TaintLabel.SYSTEM_TRUSTED,
        method: str = "manual",
    ) -> bool:
        """Sanitize a value, downgrading its taint label.

        Returns True if sanitization succeeded, False if not allowed or
        the value is a SECRET (secrets cannot be sanitized — they must
        be redacted, not downgraded).
        """
        if not self._allow_sanitization:
            return False
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return False
            if entry.label is TaintLabel.SECRET:
                return False  # Secrets cannot be downgraded
            # Content-based guard: refuse to downgrade a value flagged as
            # containing a secret (via metadata) even if mislabeled.
            if entry.metadata.get("contains_secret"):
                return False
            entry.label = target
            entry.sanitized = True
            entry.sanitization_count += 1
            entry.metadata["last_sanitization_method"] = method
            return True

    def redact(self, key: str) -> bool:
        """Mark a value as redacted (removes it from tracking)."""
        with self._lock:
            return self._entries.pop(key, None) is not None

    def merge(self, keys: list[str], result_key: str) -> TaintLabel:
        """Merge multiple values — the result gets the highest (most sensitive) label.

        This models the lattice join: combining a SYSTEM_TRUSTED value with
        a USER_UNTRUSTED value produces a USER_UNTRUSTED result.
        """
        with self._lock:
            labels = [self._entries[k].label for k in keys if k in self._entries]
            if not labels:
                raise KeyError("no labeled keys found among merge inputs")
            joined = max(labels)
            self._entries[result_key] = TaintEntry(
                label=joined,
                original_label=joined,
                metadata={"merged_from": list(keys)},
            )
            return joined

    @property
    def violations(self) -> list[dict[str, Any]]:
        """List of recorded taint violations."""
        with self._lock:
            return list(self._violations)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        """Return a snapshot of all tracked labels."""
        with self._lock:
            return {
                k: {
                    "label": v.label.name,
                    "original_label": v.original_label.name,
                    "sanitized": v.sanitized,
                    "sanitization_count": v.sanitization_count,
                }
                for k, v in self._entries.items()
            }

    def clear(self) -> None:
        """Remove all tracked labels and violations."""
        with self._lock:
            self._entries.clear()
            self._violations.clear()


def classify_source(source: str) -> TaintLabel:
    """Heuristically classify a content source into a taint label.

    Args:
        source: A string identifying the source (e.g., "user", "system",
            "rag", "tool:search", "secret:api_key").
    """
    s = source.lower().strip()
    if s.startswith("secret") or s.startswith("api_key") or s.startswith("password"):
        return TaintLabel.SECRET
    if s.startswith("user") or s == "input":
        return TaintLabel.USER_UNTRUSTED
    if s.startswith("rag") or s.startswith("retrieval") or s.startswith("document"):
        return TaintLabel.RAG_UNTRUSTED
    if s.startswith("tool") or s.startswith("mcp") or s.startswith("function"):
        return TaintLabel.TOOL_OUTPUT
    if s.startswith("system") or s.startswith("guardrail") or s.startswith("policy"):
        return TaintLabel.SYSTEM_TRUSTED
    return TaintLabel.USER_UNTRUSTED  # Default to untrusted


_default_tracker: TaintTracker | None = None


def get_default_tracker() -> TaintTracker:
    """Return the process-wide default TaintTracker (lazy singleton)."""
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = TaintTracker()
    return _default_tracker


def _register_taint_guardrail() -> None:
    """Register the taint-flow guardrail into the default registry.

    The guardrail enforces the lattice no-write-down rule: content
    classified as USER_UNTRUSTED/RAG_UNTRUSTED/SECRET may not flow
    into SYSTEM_TRUSTED contexts (tool calls, file writes) without
    explicit sanitization. It runs as an input guardrail before the
    Guardian predicate engine.
    """
    try:
        from runtime.policy import GuardrailResult, input_guardrail

        def _iter_strings(obj: Any, prefix: str = "") -> list[tuple[str, str]]:
            """Recursively collect (key, string_value) pairs from nested dicts/lists."""
            results: list[tuple[str, str]] = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    key = f"{prefix}.{k}" if prefix else str(k)
                    if isinstance(v, str):
                        results.append((key, v))
                    elif isinstance(v, (dict, list, tuple)):
                        results.extend(_iter_strings(v, key))
            elif isinstance(obj, (list, tuple)):
                for i, v in enumerate(obj):
                    key = f"{prefix}[{i}]"
                    if isinstance(v, str):
                        results.append((key, v))
                    elif isinstance(v, (dict, list, tuple)):
                        results.extend(_iter_strings(v, key))
            return results

        @input_guardrail("taint_flow_check")
        def taint_flow_check(context: dict[str, Any]) -> GuardrailResult:
            tool = str(context.get("tool", ""))
            # Also check context.get("action") for nested tool name
            if not tool and isinstance(context.get("action"), dict):
                tool = str(context["action"].get("type", ""))
            # Only enforce on write-like tools where injection risk is highest
            sensitive_tools = {"write", "edit", "exec", "Bash", "apply", "deploy"}
            if tool not in sensitive_tools:
                return GuardrailResult(tripwire_triggered=False)
            # Collect all string values from nested context (handles PolicyManager's {"action":{...},"args":{...}})
            for key, val in _iter_strings(context):
                if not val.strip():
                    continue
                if _looks_like_secret(val):
                    return GuardrailResult(
                        tripwire_triggered=True,
                        output_info={
                            "guardrail": "taint_flow_check",
                            "reason": f"Secret pattern detected in '{key}' for tool '{tool}'",
                        },
                        decision="deny",
                    )
                # Heuristic: if key suggests untrusted source, check for injection
                src_label = classify_source(key.split(".")[-1].split("[")[0])
                if src_label in (TaintLabel.USER_UNTRUSTED, TaintLabel.RAG_UNTRUSTED):
                    injection_keywords = (
                        "ignore previous", "system:", "reveal", "exfiltrate",
                        "rm -rf", "drop table", "delete from",
                    )
                    if any(kw in val.lower() for kw in injection_keywords):
                        return GuardrailResult(
                            tripwire_triggered=True,
                            output_info={
                                "guardrail": "taint_flow_check",
                                "reason": f"Potential injection in '{key}' for tool '{tool}'",
                            },
                            decision="deny",
                        )
            return GuardrailResult(tripwire_triggered=False)

    except Exception:
        # Never break import if policy module not yet ready
        pass


# Auto-register on import so Kernel/Guardian picks it up without explicit wiring
_register_taint_guardrail()

__all__ = [
    "TaintEntry",
    "TaintError",
    "TaintLabel",
    "TaintTracker",
    "classify_source",
    "get_default_tracker",
]
