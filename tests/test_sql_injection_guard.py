"""Tests for runtime/sql_injection_guard.py — SQL injection prevention.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

import pytest

from runtime.schemas import ValidationError
from runtime.sql_injection_guard import (
    ensure_safe_identifier,
    is_safe_identifier,
    safe_query_identifier,
    sanitize_identifier,
    validate_column_list,
    validate_order_by,
)


class TestEnsureSafeIdentifier:
    def test_valid_identifier(self) -> None:
        assert ensure_safe_identifier("my_table") == "my_table"

    def test_valid_with_underscore(self) -> None:
        assert ensure_safe_identifier("_private") == "_private"

    def test_valid_alphanumeric(self) -> None:
        assert ensure_safe_identifier("table123") == "table123"

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier("")

    def test_rejects_starts_with_digit(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier("123table")

    def test_rejects_special_chars(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier("table; DROP")

    def test_rejects_traversal(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier("../etc/passwd")

    def test_rejects_non_string(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier(123)  # type: ignore[arg-type]


class TestValidateOrderBy:
    def test_simple_field(self) -> None:
        assert validate_order_by("name") == "name"

    def test_field_with_direction(self) -> None:
        assert validate_order_by("name desc") == "name desc"

    def test_multiple_fields(self) -> None:
        result = validate_order_by("name asc, created_at desc")
        assert "name asc" in result
        assert "created_at desc" in result

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError):
            validate_order_by("")

    def test_rejects_invalid_direction(self) -> None:
        with pytest.raises(ValidationError):
            validate_order_by("name sideways")

    def test_rejects_sql_injection(self) -> None:
        with pytest.raises(ValidationError):
            validate_order_by("name; DROP TABLE users")

    def test_normalizes_case(self) -> None:
        assert validate_order_by("NAME DESC") == "name desc"


class TestValidateColumnList:
    def test_single_column(self) -> None:
        result = validate_column_list("name")
        assert result == ["name"]

    def test_multiple_columns(self) -> None:
        result = validate_column_list("id, name, email")
        assert result == ["id", "name", "email"]

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError):
            validate_column_list("")

    def test_rejects_invalid_column(self) -> None:
        with pytest.raises(ValidationError):
            validate_column_list("name; DROP")


class TestIsSafeIdentifier:
    def test_true_for_valid(self) -> None:
        assert is_safe_identifier("my_table") is True

    def test_false_for_invalid(self) -> None:
        assert is_safe_identifier("123bad") is False

    def test_false_for_non_string(self) -> None:
        assert is_safe_identifier(123) is False  # type: ignore[arg-type]


class TestSanitizeIdentifier:
    def test_strips_special_chars(self) -> None:
        assert sanitize_identifier("my-table!") == "mytable"

    def test_prepends_underscore_for_digit_start(self) -> None:
        assert sanitize_identifier("123table") == "_123table"

    def test_returns_none_for_empty(self) -> None:
        assert sanitize_identifier("") is None

    def test_returns_none_for_all_special(self) -> None:
        assert sanitize_identifier("!!!") is None


class TestSafeQueryIdentifier:
    def test_default_kind(self) -> None:
        assert safe_query_identifier("users") == "users"

    def test_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            safe_query_identifier("users; DROP")
