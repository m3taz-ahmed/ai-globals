"""Gap coverage: runtime/sql_injection_guard.py — all public functions."""

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
    def test_valid(self) -> None:
        assert ensure_safe_identifier("users") == "users"
        assert ensure_safe_identifier("_x9", "column") == "_x9"

    def test_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ensure_safe_identifier("users; DROP TABLE")
        with pytest.raises(ValidationError):
            ensure_safe_identifier("9abc")
        with pytest.raises(ValidationError):
            ensure_safe_identifier(123)  # type: ignore[arg-type]


class TestValidateOrderBy:
    def test_empty(self) -> None:
        with pytest.raises(ValidationError):
            validate_order_by("")
        with pytest.raises(ValidationError):
            validate_order_by("   ")

    def test_single_field(self) -> None:
        assert validate_order_by("Name") == "name"

    def test_field_direction(self) -> None:
        assert validate_order_by("name DESC") == "name desc"
        assert validate_order_by("a asc, b desc") == "a asc, b desc"

    def test_bad_field(self) -> None:
        with pytest.raises(ValidationError):
            validate_order_by("name;drop")
        with pytest.raises(ValidationError):
            validate_order_by("bad-field desc")

    def test_bad_direction(self) -> None:
        with pytest.raises(ValidationError, match="direction"):
            validate_order_by("name sideways")

    def test_too_many_parts(self) -> None:
        with pytest.raises(ValidationError):
            validate_order_by("a b c")


class TestValidateColumnList:
    def test_valid(self) -> None:
        assert validate_column_list("a, b ,c") == ["a", "b", "c"]

    def test_empty(self) -> None:
        with pytest.raises(ValidationError):
            validate_column_list("")
        with pytest.raises(ValidationError):
            validate_column_list(" , , ")  # all entries empty

    def test_bad_column(self) -> None:
        with pytest.raises(ValidationError):
            validate_column_list("a, x;y")


class TestHelpers:
    def test_safe_query_identifier(self) -> None:
        assert safe_query_identifier("t") == "t"
        with pytest.raises(ValidationError):
            safe_query_identifier("a b")

    def test_is_safe_identifier(self) -> None:
        assert is_safe_identifier("ok_1")
        assert not is_safe_identifier("1bad")
        assert not is_safe_identifier(5)  # type: ignore[arg-type]

    def test_sanitize_identifier(self) -> None:
        assert sanitize_identifier("  name! ") == "name"
        assert sanitize_identifier("9lives") == "_9lives"
        assert sanitize_identifier("!!!") is None
        assert sanitize_identifier(None) is None  # type: ignore[arg-type]
