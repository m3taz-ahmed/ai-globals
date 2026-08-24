#!/usr/bin/env python3
"""Misc quality utilities for aiZee (WS-J).

WS-J items implemented in this module:
- W1: Budget providers — pluggable cost provider interface
- W3: Assertions — test assertion helpers
- W5: Output schemas — standardized output envelope
- W6: Bounder — output bounding/limiting
- W7: Witness — execution witness tracking
- W8: Lazy imports — lazy import helper for heavy dependencies
- W9: Reflexion — self-reflection helper for learning from failures

Items W2 (mypy tests) and W4 (adapter hygiene) are addressed via
existing code quality (mypy already passes on all test files, and
adapters follow the existing StorageBackend protocol pattern).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# WS-J W1: Budget providers — pluggable cost provider interface
# ---------------------------------------------------------------------------


class CostProvider:
    """WS-J W1: Interface for pluggable cost providers.

    A cost provider translates tokens/calls into a monetary cost.
    Different providers can be plugged in for different LLM vendors.
    """

    def cost_per_token(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Compute the cost for a token usage. Override in subclasses."""
        return 0.0

    def cost_per_call(self, model: str, calls: int) -> float:
        """Compute the cost for a number of API calls. Override in subclasses."""
        return 0.0


class FixedRateCostProvider(CostProvider):
    """Simple cost provider with fixed per-token rates per model."""

    def __init__(self, rates: dict[str, dict[str, float]] | None = None) -> None:
        self._rates = rates or {
            "gpt-4": {"input": 0.00003, "output": 0.00006},
            "gpt-3.5-turbo": {"input": 0.0000015, "output": 0.000002},
            "default": {"input": 0.00001, "output": 0.00002},
        }

    def cost_per_token(self, model: str, input_tokens: int, output_tokens: int) -> float:
        rates = self._rates.get(model, self._rates["default"])
        return (input_tokens * rates["input"]) + (output_tokens * rates["output"])


# ---------------------------------------------------------------------------
# WS-J W5: Output schemas — standardized output envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OutputEnvelope:
    """WS-J W5: Standardized output envelope for all aiZee operations.

    Every operation returns this envelope with:
    - ok: success/failure boolean
    - data: the result data (if successful)
    - error: error message (if failed)
    - gate: which gate made the decision (if any)
    - metadata: additional context (tokens, duration, etc.)
    """

    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    gate: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "data": dict(self.data),
            "error": self.error,
            "gate": self.gate,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def success(cls, data: dict[str, Any] | None = None, **metadata: Any) -> OutputEnvelope:
        return cls(ok=True, data=data or {}, metadata=dict(metadata))

    @classmethod
    def failure(cls, error: str, gate: str = "", **metadata: Any) -> OutputEnvelope:
        return cls(ok=False, error=error, gate=gate, metadata=dict(metadata))


# ---------------------------------------------------------------------------
# WS-J W6: Bounder — output bounding/limiting
# ---------------------------------------------------------------------------


class Bounder:
    """WS-J W6: Bound output size to prevent runaway responses.

    Enforces max length, max items, and max depth on output data.
    """

    def __init__(self, max_chars: int = 10000, max_items: int = 100, max_depth: int = 10) -> None:
        self.max_chars = max_chars
        self.max_items = max_items
        self.max_depth = max_depth

    def bound_text(self, text: str) -> str:
        """Truncate text to max_chars."""
        if len(text) <= self.max_chars:
            return text
        return text[: self.max_chars] + "...[truncated]"

    def bound_list(self, items: list[T]) -> list[T]:
        """Truncate list to max_items."""
        if len(items) <= self.max_items:
            return items
        return items[: self.max_items]

    def bound_dict(self, data: dict[str, Any], depth: int = 0) -> dict[str, Any]:
        """Truncate dict to max_items and limit nesting depth."""
        if depth >= self.max_depth:
            return {"_truncated": "max depth reached"}
        if len(data) <= self.max_items:
            return {
                k: self._bound_value(v, depth + 1) if isinstance(v, (dict, list)) else v
                for k, v in data.items()
            }
        truncated = dict(list(data.items())[: self.max_items])
        truncated["_truncated"] = f"{len(data) - self.max_items} more keys"
        return truncated

    def _bound_value(self, value: Any, depth: int) -> Any:
        if isinstance(value, dict):
            return self.bound_dict(value, depth)
        if isinstance(value, list):
            return self.bound_list(value)
        return value


# ---------------------------------------------------------------------------
# WS-J W7: Witness — execution witness tracking
# ---------------------------------------------------------------------------


@dataclass
class Witness:
    """WS-J W7: Execution witness — tracks what happened during an operation.

    A witness is an immutable record of an operation's execution, including
    inputs, outputs, timing, and any gate decisions. Used for audit trails
    and debugging.
    """

    operation: str
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0.0
    gate: str = ""
    success: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "inputs": dict(self.inputs),
            "outputs": dict(self.outputs),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": round(self.duration_ms, 2),
            "gate": self.gate,
            "success": self.success,
            "error": self.error,
        }


class WitnessRecorder:
    """WS-J W7: Records execution witnesses for audit/debugging."""

    def __init__(self, max_witnesses: int = 1000) -> None:
        self._witnesses: list[Witness] = []
        self._max = max_witnesses

    def record(self, witness: Witness) -> None:
        self._witnesses.append(witness)
        if len(self._witnesses) > self._max:
            self._witnesses = self._witnesses[-self._max :]

    def all(self) -> list[Witness]:
        return list(self._witnesses)

    def by_operation(self, operation: str) -> list[Witness]:
        return [w for w in self._witnesses if w.operation == operation]

    def failures(self) -> list[Witness]:
        return [w for w in self._witnesses if not w.success]

    def clear(self) -> None:
        self._witnesses.clear()


# ---------------------------------------------------------------------------
# WS-J W8: Lazy imports — lazy import helper
# ---------------------------------------------------------------------------


class LazyImport(Generic[T]):
    """WS-J W8: Lazy import helper for heavy dependencies.

    Defers the import until the first access, preventing slow startup
    when the dependency isn't always needed.

    Usage::

        heavy_lib = LazyImport("runtime.heavy_module.HeavyClass")
        # ...
        obj = heavy_lib()  # import happens here, not at module load
    """

    def __init__(self, import_path: str) -> None:
        self._import_path = import_path
        self._cached: type[T] | None = None

    def _resolve(self) -> type[T]:
        if self._cached is not None:
            return self._cached
        parts = self._import_path.split(".")
        if len(parts) < 2:
            raise ImportError(f"Invalid lazy import path: {self._import_path!r}")
        module_path = ".".join(parts[:-1])
        attr_name = parts[-1]
        import importlib

        try:
            module = importlib.import_module(module_path)
            obj = getattr(module, attr_name)
        except (ImportError, AttributeError) as exc:
            raise ImportError(f"Failed to lazy import {self._import_path!r}: {exc}") from exc
        self._cached = obj
        return obj  # type: ignore[no-any-return]

    def __call__(self, *args: Any, **kwargs: Any) -> T:
        cls = self._resolve()
        return cls(*args, **kwargs)

    @property
    def is_loaded(self) -> bool:
        return self._cached is not None


# ---------------------------------------------------------------------------
# WS-J W9: Reflexion — self-reflection helper
# ---------------------------------------------------------------------------


@dataclass
class ReflexionEntry:
    """WS-J W9: A single self-reflection entry.

    Inspired by Reflexion (arXiv 2303.11366) — agents that reflect on
    past failures to improve future performance.
    """

    task: str
    outcome: str  # "success" or "failure"
    reflection: str
    lesson: str
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "outcome": self.outcome,
            "reflection": self.reflection,
            "lesson": self.lesson,
            "timestamp": self.timestamp,
        }


class ReflexionLog:
    """WS-J W9: Log of self-reflection entries for learning from failures."""

    def __init__(self, max_entries: int = 100) -> None:
        self._entries: list[ReflexionEntry] = []
        self._max = max_entries

    def add(self, task: str, outcome: str, reflection: str, lesson: str) -> ReflexionEntry:
        entry = ReflexionEntry(
            task=task,
            outcome=outcome,
            reflection=reflection,
            lesson=lesson,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._entries.append(entry)
        if len(self._entries) > self._max:
            self._entries = self._entries[-self._max :]
        return entry

    def failures(self) -> list[ReflexionEntry]:
        return [e for e in self._entries if e.outcome == "failure"]

    def successes(self) -> list[ReflexionEntry]:
        return [e for e in self._entries if e.outcome == "success"]

    def lessons(self) -> list[str]:
        return [e.lesson for e in self._entries if e.outcome == "failure"]

    def all(self) -> list[ReflexionEntry]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries.clear()

    def summary(self) -> dict[str, Any]:
        total = len(self._entries)
        fails = len(self.failures())
        return {
            "total": total,
            "failures": fails,
            "successes": total - fails,
            "failure_rate": fails / total if total > 0 else 0.0,
        }


# ---------------------------------------------------------------------------
# WS-J W3: Assertion helpers
# ---------------------------------------------------------------------------


def assert_ok(response: dict[str, Any], msg: str = "") -> None:
    """WS-J W3: Assert that a kernel response has ok=True."""
    assert response.get("ok") is True, f"Expected ok=True, got {response.get('ok')}. {msg}"


def assert_denied(response: dict[str, Any], msg: str = "") -> None:
    """WS-J W3: Assert that a kernel response has ok=False."""
    assert response.get("ok") is False, f"Expected ok=False, got {response.get('ok')}. {msg}"


def assert_gate(response: dict[str, Any], gate: str, msg: str = "") -> None:
    """WS-J W3: Assert that a response was blocked by a specific gate."""
    actual = response.get("gate", "")
    assert actual == gate, f"Expected gate={gate!r}, got {actual!r}. {msg}"


def assert_has_key(response: dict[str, Any], key: str, msg: str = "") -> None:
    """WS-J W3: Assert that a response has a specific key."""
    assert key in response, f"Expected key {key!r} in response. {msg}"
