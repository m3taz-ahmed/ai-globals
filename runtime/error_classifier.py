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


def _instantiate_error(error_class: ErrorClass, message: str) -> AizeeError:
    """Instantiate an AizeeError subclass with the correct constructor signature.

    Subclasses (BudgetExceededError, PolicyDeniedError, ValidationError)
    take ``(message, context=None)``, but the base ``AizeeError`` takes
    ``(error_code, message, severity, context)``. This helper handles
    both cases so callers don't need to know which they got.
    """
    if error_class is AizeeError:
        return AizeeError(
            "UNEXPECTED_ERROR", message, ErrorSeverity.MEDIUM,
        )
    return error_class(message)  # type: ignore[call-arg]


# Pattern → (ErrorClass, message_template) mappings.
# Checked in order; first match wins.
_CLASSIFICATION_RULES: list[tuple[re.Pattern[str], ErrorClass, str]] = [
    # Budget / rate limit
    (
        re.compile(r"rate.?limit|too many requests|429", re.IGNORECASE),
        BudgetExceededError,
        "Rate limit exceeded: {detail}",
    ),
    (
        re.compile(r"quota|usage.?limit|budget.?exceeded", re.IGNORECASE),
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
    # Validation
    (
        re.compile(r"validation|invalid|malformed|bad.?request|400", re.IGNORECASE),
        ValidationError,
        "Validation error: {detail}",
    ),
    (
        re.compile(r"type.?error|attribute.?error|key.?error|index.?error", re.IGNORECASE),
        ValidationError,
        "Type/attribute error: {detail}",
    ),
]


def classify_error(exc: Exception) -> tuple[ErrorClass, str]:
    """Inspect *exc* and return ``(error_class, message)``.

    If the exception is already an :class:`AizeeError`, its class and
    message are returned directly. Otherwise, the exception's string
    representation is matched against classification rules to determine
    the appropriate subclass.
    """
    # If already an AizeeError, pass through
    if isinstance(exc, AizeeError):
        return type(exc), str(exc.args[0]) if exc.args else str(exc)

    detail = str(exc)
    exc_type_name = type(exc).__name__

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
    # Construct with context — subclasses accept (message, context),
    # but AizeeError base requires (error_code, message, severity, context).
    if error_class is AizeeError:
        return AizeeError("UNEXPECTED_ERROR", message, ErrorSeverity.MEDIUM, ctx)
    return error_class(message, ctx)  # type: ignore[arg-type]
