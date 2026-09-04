"""Pydantic schemas for runtime configuration and action validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from runtime.budget import ALLOWED_EXCEED, ALLOWED_PERIODS

# -- Exception Hierarchy (inspired by Floci's AwsException) -----------------


class ErrorSeverity(str, Enum):
    """Severity levels for structured errors."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AizeeError(Exception):
    """Base exception for aiZee runtime errors.

    Inspired by Floci's ``AwsException``: carries an error code, message,
    severity, and optional structured context. All aiZee exceptions should
    inherit from this so the kernel/policy gates can handle them uniformly.

    Attributes:
        error_code: Stable machine-readable code (e.g., "POLICY_DENIED").
        message: Human-readable description.
        severity: Error severity level.
        context: Optional structured context dict for debugging/logging.
    """

    def __init__(
        self,
        error_code: str,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.severity = severity
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a structured dict for logging/API responses."""
        return {
            "error_code": self.error_code,
            "message": str(self.args[0]) if self.args else "",
            "severity": self.severity.value,
            "context": dict(self.context),
        }


class PolicyDeniedError(AizeeError):
    """Raised when a policy gate denies an action."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("POLICY_DENIED", message, ErrorSeverity.HIGH, context)


class BudgetExceededError(AizeeError):
    """Raised when a budget limit is exceeded."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("BUDGET_EXCEEDED", message, ErrorSeverity.HIGH, context)


class ValidationError(AizeeError):
    """Raised when input validation fails.

    NOTE: This name collides with ``pydantic.ValidationError``. When importing
    both in the same module, use ``from runtime.schemas import ValidationError as AizeeValidationError``
    or use the ``AizeeValidationError`` alias below.
    """

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("VALIDATION_ERROR", message, ErrorSeverity.MEDIUM, context)


# Alias to avoid collision with pydantic.ValidationError.
AizeeValidationError = ValidationError


class StorageError(AizeeError):
    """Raised when a storage backend operation fails."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("STORAGE_ERROR", message, ErrorSeverity.HIGH, context)


# -- PaginatedResult (inspired by Floci's PaginatedResult<T>) ---------------


@dataclass
class PaginatedResult:
    """A page of list results plus an optional pagination token.

    Inspired by Floci's ``PaginatedResult<T>(items, nextToken)`` record.
    Used by search/list operations that may return large result sets.
    """

    items: list[Any] = field(default_factory=list)
    next_token: str | None = None
    total: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for API/MCP responses."""
        result: dict[str, Any] = {"items": self.items}
        if self.next_token is not None:
            result["next_token"] = self.next_token
        if self.total is not None:
            result["total"] = self.total
        return result

    @property
    def has_more(self) -> bool:
        """True if there are more results available."""
        return self.next_token is not None


# -- GateVerdict (EVAL-W0: unified gate verdict object) ---------------------
# Inspired by NEMO Guardrails RailOutcome (frozen dataclass + decision enum
# + invariant) and GUARDRAILS_AI FailResult.error_spans (char-range evidence).
# The three existing gates (prompt_gate, mcp_firewall, agent_gateway) speak
# incompatible dialects; GateVerdict is the canonical cross-gate verdict.


class GateDecision(str, Enum):
    """Unified decision enum for all gates."""

    ALLOW = "allow"
    BLOCK = "block"
    REDACT = "redact"
    TRANSFORM = "transform"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(frozen=True)
class GateVerdict:
    """The canonical, gate-agnostic verdict of a single gate check.

    Fields:
        gate: which gate produced this ("prompt_gate" | "mcp_firewall" | "agent_gateway").
        decision: ALLOW / BLOCK / REDACT / TRANSFORM / REQUIRE_APPROVAL.
        reason: human-readable explanation.
        metadata: neutral evidence (scores, rule names, etc.).
        spans: char ranges for REDACT/BLOCK evidence as (start, end, label) tuples.

    Invariant: decision == REDACT implies spans is non-empty.
    """

    gate: str
    decision: GateDecision
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    spans: tuple[tuple[int, int, str], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision", GateDecision(self.decision))
        if not isinstance(self.reason, str):
            raise TypeError("reason must be a string")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dict")
        object.__setattr__(self, "spans", tuple(self.spans))
        if self.decision is GateDecision.REDACT and not self.spans:
            raise ValueError("REDACT verdict must have non-empty spans")

    @property
    def is_blocked(self) -> bool:
        return self.decision is GateDecision.BLOCK

    @property
    def is_allowed(self) -> bool:
        return self.decision is GateDecision.ALLOW

    @classmethod
    def allow(cls, gate: str, reason: str = "", **metadata: Any) -> GateVerdict:
        return cls(gate=gate, decision=GateDecision.ALLOW, reason=reason, metadata=metadata)

    @classmethod
    def block(cls, gate: str, reason: str = "", **metadata: Any) -> GateVerdict:
        return cls(gate=gate, decision=GateDecision.BLOCK, reason=reason, metadata=metadata)

    @classmethod
    def redact(
        cls, gate: str, reason: str, spans: tuple[tuple[int, int, str], ...], **metadata: Any
    ) -> GateVerdict:
        return cls(gate=gate, decision=GateDecision.REDACT, reason=reason, spans=spans, metadata=metadata)

    @classmethod
    def require_approval(cls, gate: str, reason: str = "", **metadata: Any) -> GateVerdict:
        return cls(gate=gate, decision=GateDecision.REQUIRE_APPROVAL, reason=reason, metadata=metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate,
            "decision": self.decision.value,
            "reason": self.reason,
            "metadata": self.metadata,
            "spans": [list(s) for s in self.spans],
        }


class BudgetSchema(BaseModel):
    """Budget configuration schema."""

    model_config = ConfigDict(extra="allow")

    max_tokens: int | None = None
    max_cost_usd: float | None = None
    max_calls: int | None = None
    period: str = "session"
    on_exceed: str = "block"
    fallback_model: str | None = None
    rollout_max_tokens: int | None = None
    rollout_reminder_threshold: float | None = None
    token_weight_input: float = 1.0
    token_weight_output: float = 1.0

    @field_validator("period")
    @classmethod
    def _validate_period(cls, v: str) -> str:
        if v not in ALLOWED_PERIODS:
            raise ValueError(f"period must be one of {ALLOWED_PERIODS}")
        return v

    @field_validator("on_exceed")
    @classmethod
    def _validate_on_exceed(cls, v: str) -> str:
        if v not in ALLOWED_EXCEED:
            raise ValueError(f"on_exceed must be one of {ALLOWED_EXCEED}")
        return v


class PolicyRuleSchema(BaseModel):
    """Policy rule schema."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1)
    condition: str = Field(..., min_length=1)
    action: str = Field(..., pattern="^(allow|ask|deny)$")
    description: str = ""
    approvers: list[str] = Field(default_factory=list)


class PolicyFileSchema(BaseModel):
    """Top-level policy YAML schema."""

    name: str = "default"
    api_version: str = "governance.aizee/v1"
    default_action: str = "ask"
    rules: list[PolicyRuleSchema] = Field(default_factory=list)

    @field_validator("default_action")
    @classmethod
    def _validate_default_action(cls, v: str) -> str:
        if v not in ("allow", "ask", "deny"):
            raise ValueError("default_action must be allow, ask, or deny")
        return v
