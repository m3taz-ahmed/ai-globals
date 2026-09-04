"""Error classification to typed AizeeError subclasses.

Ported from open-notebook (lfnovo/open-notebook) ``classify_error``
pattern. Inspects a raw exception and returns the correct typed
:class:`~runtime.schemas.AizeeError` subclass. Ensures consistent
error mapping across MCP tool handlers and runtime modules.

Usage::

    from runtime.error_classifier import classify_error
    try:
        risky_operation()
    except Exception as exc:
        error_class, message = classify_error(exc)
        raise error_class(message) from exc
"""

from __future__ import annotations

import re
from typing import Any

from runtime.schemas import (
    AizeeError,
    BudgetExceededError,
    ErrorSeverity,
    PolicyDeniedError,
    ValidationError,
)

# Type alias for AizeeError subclasses.
ErrorClass = type[AizeeError]


def _truncate(detail: str, limit: int = 500) -> str:
    """Truncate raw exception text before interpolating into new messages."""
    if len(detail) > limit:
        return detail[:limit] + "...[truncated]"
    return detail


def _instantiate_error(
    error_class: ErrorClass,
    message: str,
    *,
    context: dict[str, Any] | None = None,
    severity: ErrorSeverity | None = None,
) -> AizeeError:
    """Instantiate an AizeeError subclass with the correct constructor signature.

    Subclasses (BudgetExceededError, PolicyDeniedError, ValidationError)
    take ``(message, context=None)``, but the base ``AizeeError`` takes
    ``(error_code, message, severity, context)``. This helper handles
    both cases so callers don't need to know which they got.
    Preserves caller-provided context/severity where supported.
    """
    if error_class is AizeeError:
        return AizeeError(
            "UNEXPECTED_ERROR", message, severity or ErrorSeverity.MEDIUM, context,
        )
    try:
        return error_class(message, context)  # type: ignore[arg-type]
    except TypeError:
        return error_class(message)  # type: ignore[call-arg]


# Pattern → (ErrorClass, message_template) mappings.
# Checked in order; first match wins. Specific quota/budget patterns come
# first so they win over generic validation matches.
_CLASSIFICATION_RULES: list[tuple[re.Pattern[str], ErrorClass, str]] = [
    # Budget / rate limit (specific first)
    (
        re.compile(r"budget.?exceeded|quota.?exceeded|usage.?limit", re.IGNORECASE),
        BudgetExceededError,
        "Budget/quota exceeded: {detail}",
    ),
    (
        re.compile(r"rate.?limit|too many requests|429", re.IGNORECASE),
        BudgetExceededError,
        "Rate limit exceeded: {detail}",
    ),
    (
        re.compile(r"\bquota\b", re.IGNORECASE),
        BudgetExceededError,
        "Budget/quota exceeded: {detail}",
    ),
    # Policy / permission
    (
        re.compile(r"permission.?denied|forbidden|403|not.?authorized", re.IGNORECASE),
        PolicyDeniedError,
        "Permission denied: {detail}",
    ),
    (
        re.compile(r"policy.?denied|blocked.?by.?policy|guardian.?deny", re.IGNORECASE),
        PolicyDeniedError,
        "Blocked by policy: {detail}",
    ),
    # Validation (generic input errors)
    (
        re.compile(r"validation|invalid|malformed|bad.?request|400", re.IGNORECASE),
        ValidationError,
        "Validation error: {detail}",
    ),
]


def classify_error(exc: Exception) -> tuple[ErrorClass, str]:
    """Inspect *exc* and return ``(error_class, message)``.

    If the exception is already an :class:`AizeeError`, its class and
    message are returned directly. Otherwise, the exception's string
    representation is matched against classification rules to determine
    the appropriate subclass.
    """
    # If already an AizeeError, pass through via its structured message field.
    if isinstance(exc, AizeeError):
        return type(exc), exc.message

    detail = _truncate(str(exc))
    exc_type_name = type(exc).__name__

    # Type/Key/Attribute/Index errors are internal bugs, not input validation,
    # unless the message clearly shows input-caused failure. Map to generic
    # internal error but keep the original traceback note.
    if isinstance(exc, (TypeError, KeyError, AttributeError, IndexError)):
        tb_note = f"{exc_type_name}: {detail}"
        # Clearly input-caused phrasing still maps to ValidationError.
        if re.search(r"validation|invalid|malformed|bad.?request", detail, re.IGNORECASE):
            return ValidationError, f"Validation error: {detail} (orig {tb_note})"
        return AizeeError, f"Unexpected error ({tb_note})"

    # Check classification rules
    for pattern, error_class, template in _CLASSIFICATION_RULES:
        if pattern.search(detail) or pattern.search(exc_type_name):
            return error_class, template.format(detail=detail)

    # Default: generic AizeeError
    return AizeeError, f"Unexpected error ({exc_type_name}): {detail}"


def classify_and_raise(exc: Exception) -> None:
    """Classify *exc* and raise the appropriate AizeeError subclass.

    Convenience for ``except`` blocks that want to convert any
    exception to a typed AizeeError.
    """
    error_class, message = classify_error(exc)
    raise _instantiate_error(error_class, message) from exc


def classify_error_with_context(
    exc: Exception,
    operation: str = "",
    context: dict[str, Any] | None = None,
) -> AizeeError:
    """Classify *exc* and return an AizeeError instance with context.

    The returned exception includes the operation name and additional
    context dict for debugging/logging.
    """
    error_class, message = classify_error(exc)
    ctx = dict(context or {})
    if operation:
        ctx["operation"] = operation
    ctx["original_exception"] = type(exc).__name__
    # Preserve context/severity via helper (base needs error_code+severity).
    severity = exc.severity if isinstance(exc, AizeeError) else ErrorSeverity.MEDIUM
    orig_ctx = dict(exc.context) if isinstance(exc, AizeeError) else {}
    merged = {**orig_ctx, **ctx}
    return _instantiate_error(error_class, message, context=merged, severity=severity)
