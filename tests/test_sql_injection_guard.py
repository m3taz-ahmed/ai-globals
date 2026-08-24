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

    def test_rejects_none(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier(None)  # type: ignore[arg-type]

    def test_rejects_sql_comment_double_dash(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier("name--")

    def test_rejects_sql_block_comment(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier("name/*")

    def test_rejects_quoted_identifier(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier('"my_table"')

    def test_rejects_backtick_quoted_identifier(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier("`my_table`")

    def test_rejects_whitespace(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier("my table")

    def test_rejects_semicolon_drop(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier("users; DROP TABLE users")

    def test_accepts_very_long_valid_identifier(self) -> None:
        long_name = "a" * 500
        assert ensure_safe_identifier(long_name) == long_name

    def test_rejects_unicode_identifier(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier("t\u00e4ble")

    def test_rejects_hyphen(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier("my-table")

    def test_returns_value_on_success(self) -> None:
        # Arrange / Act / Assert
        result = ensure_safe_identifier("col", "column")
        assert result == "col"

    def test_custom_kind_in_error_context(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ensure_safe_identifier("bad!", "table")
        assert exc_info.value.context["kind"] == "table"


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

    def test_rejects_three_parts(self) -> None:
        with pytest.raises(ValidationError):
            validate_order_by("name desc extra")

    def test_rejects_sql_comment_in_order_by(self) -> None:
        with pytest.raises(ValidationError):
            validate_order_by("name--")

    def test_rejects_block_comment_in_order_by(self) -> None:
        with pytest.raises(ValidationError):
            validate_order_by("name/* */")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValidationError):
            validate_order_by("   ")

    def test_rejects_invalid_field_name(self) -> None:
        with pytest.raises(ValidationError):
            validate_order_by("123bad asc")

    def test_normalizes_multiple_fields_case_and_spacing(self) -> None:
        result = validate_order_by("  Name  ASC ,  Created_At  DESC  ")
        assert "name asc" in result
        assert "created_at desc" in result

    def test_single_field_uppercase_normalized(self) -> None:
        assert validate_order_by("NAME") == "name"


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

    def test_rejects_sql_comment_in_column(self) -> None:
        with pytest.raises(ValidationError):
            validate_column_list("name--")

    def test_rejects_block_comment_in_column(self) -> None:
        with pytest.raises(ValidationError):
            validate_column_list("name/*")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValidationError):
            validate_column_list("   ")

    def test_skips_empty_entries_between_commas(self) -> None:
        result = validate_column_list("id, , name, , email")
        assert result == ["id", "name", "email"]

    def test_rejects_all_empty_entries(self) -> None:
        with pytest.raises(ValidationError):
            validate_column_list(", , ,")

    def test_strips_whitespace_around_columns(self) -> None:
        result = validate_column_list("  id  ,  name  ")
        assert result == ["id", "name"]


class TestIsSafeIdentifier:
    def test_true_for_valid(self) -> None:
        assert is_safe_identifier("my_table") is True

    def test_false_for_invalid(self) -> None:
        assert is_safe_identifier("123bad") is False

    def test_false_for_non_string(self) -> None:
        assert is_safe_identifier(123) is False  # type: ignore[arg-type]

    def test_false_for_none(self) -> None:
        assert is_safe_identifier(None) is False  # type: ignore[arg-type]

    def test_false_for_empty(self) -> None:
        assert is_safe_identifier("") is False

    def test_false_for_sql_injection(self) -> None:
        assert is_safe_identifier("name; DROP") is False

    def test_false_for_sql_comment(self) -> None:
        assert is_safe_identifier("name--") is False

    def test_false_for_block_comment(self) -> None:
        assert is_safe_identifier("name/*") is False

    def test_true_for_very_long_valid(self) -> None:
        assert is_safe_identifier("a" * 500) is True

    def test_false_for_unicode(self) -> None:
        assert is_safe_identifier("t\u00e4ble") is False


class TestSanitizeIdentifier:
    def test_strips_special_chars(self) -> None:
        assert sanitize_identifier("my-table!") == "mytable"

    def test_prepends_underscore_for_digit_start(self) -> None:
        assert sanitize_identifier("123table") == "_123table"

    def test_returns_none_for_empty(self) -> None:
        assert sanitize_identifier("") is None

    def test_returns_none_for_all_special(self) -> None:
        assert sanitize_identifier("!!!") is None

    def test_returns_none_for_non_string(self) -> None:
        assert sanitize_identifier(123) is None  # type: ignore[arg-type]

    def test_returns_none_for_none(self) -> None:
        assert sanitize_identifier(None) is None  # type: ignore[arg-type]

    def test_strips_sql_injection_chars(self) -> None:
        assert sanitize_identifier("name; DROP") == "nameDROP"

    def test_strips_sql_comment_chars(self) -> None:
        assert sanitize_identifier("name--") == "name"

    def test_strips_block_comment_chars(self) -> None:
        assert sanitize_identifier("name/* */") == "name"

    def test_preserves_valid_identifier(self) -> None:
        assert sanitize_identifier("my_table") == "my_table"

    def test_strips_whitespace(self) -> None:
        assert sanitize_identifier("  my table  ") == "mytable"

    def test_strips_unicode(self) -> None:
        assert sanitize_identifier("t\u00e4ble") == "tble"


class TestSafeQueryIdentifier:
    def test_default_kind(self) -> None:
        assert safe_query_identifier("users") == "users"

    def test_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            safe_query_identifier("users; DROP")
