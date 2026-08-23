"""Tests for runtime/error_classifier.py — error classification.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

import pytest

from runtime.error_classifier import classify_and_raise, classify_error, classify_error_with_context
from runtime.schemas import AizeeError, BudgetExceededError, PolicyDeniedError, ValidationError


class TestClassifyError:
    def test_passes_through_aizee_error(self) -> None:
        original = BudgetExceededError("Budget hit")
        error_class, message = classify_error(original)
        assert error_class is BudgetExceededError
        assert "Budget hit" in message

    def test_rate_limit_to_budget(self) -> None:
        exc = Exception("Rate limit exceeded: 429 Too Many Requests")
        error_class, _message = classify_error(exc)
        assert error_class is BudgetExceededError

    def test_permission_denied_to_policy(self) -> None:
        exc = Exception("Permission denied: 403 Forbidden")
        error_class, _message = classify_error(exc)
        assert error_class is PolicyDeniedError

    def test_validation_error(self) -> None:
        exc = ValueError("Invalid input: bad request 400")
        error_class, _message = classify_error(exc)
        assert error_class is ValidationError

    def test_unknown_error_to_aizee(self) -> None:
        exc = RuntimeError("Something unexpected happened")
        error_class, message = classify_error(exc)
        assert error_class is AizeeError
        assert "RuntimeError" in message


class TestClassifyAndRaise:
    def test_raises_typed_error(self) -> None:
        with pytest.raises(BudgetExceededError):
            try:
                raise Exception("Rate limit exceeded")
            except Exception as exc:
                classify_and_raise(exc)

    def test_preserves_chain(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            try:
                raise ValueError("Invalid input")
            except Exception as exc:
                classify_and_raise(exc)
        assert exc_info.value.__cause__ is not None


class TestClassifyErrorWithContext:
    def test_includes_context(self) -> None:
        exc = Exception("Rate limit exceeded")
        result = classify_error_with_context(exc, operation="test_op", context={"user": "test"})
        assert isinstance(result, BudgetExceededError)
        # Context should be set via the AizeeError constructor
