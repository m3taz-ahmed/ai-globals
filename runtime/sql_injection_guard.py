"""SQL injection prevention guards for query identifiers.

Ported from open-notebook (lfnovo/open-notebook)
``open_notebook/database/repository.py`` and
``open_notebook/domain/base.py``.
Validates table names, column names, ORDER BY clauses, and other
SQL identifiers before they are interpolated into queries.

SurrealQL/SQLite only allows binding *values* as query parameters,
not identifiers (table/column names in certain positions). This
module validates those identifiers against an allowlist pattern
before interpolation, preventing SQL injection via user-controlled
sort/identifier input.
"""

from __future__ import annotations

import re

from runtime.schemas import ValidationError

# Bare identifier: no ':', whitespace, or query syntax.
# Allows letters, digits, underscores; must start with letter or underscore.
_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Allowed ORDER BY directions.
_ALLOWED_DIRECTIONS: set[str] = {"asc", "desc"}


def ensure_safe_identifier(value: str, kind: str = "identifier") -> str:
    """Validate a table/column/relationship name before interpolation.

    Raises :class:`ValidationError` if *value* is not a safe identifier.
    """
    if not isinstance(value, str) or not _IDENTIFIER_RE.match(value):
        raise ValidationError(
            f"Invalid {kind} name: {value!r}",
            context={"value": value, "kind": kind},
        )
    return value


def validate_order_by(order_by: str) -> str:
    """Validate and normalize an ORDER BY clause.

    Supports:
    - ``"field"``
    - ``"field direction"``
    - ``"field1 direction, field2 direction"``

    Raises :class:`ValidationError` for invalid field names or directions.
    Returns the normalized clause string.
    """
    if not order_by or not order_by.strip():
        raise ValidationError("ORDER BY clause cannot be empty")

    clauses = [c.strip() for c in order_by.split(",")]
    validated_clauses: list[str] = []

    for clause in clauses:
        parts = clause.strip().split()
        if len(parts) == 1:
            # Just a field name
            field = parts[0].lower()
            if not _IDENTIFIER_RE.match(field):
                raise ValidationError(
                    f"Invalid ORDER BY field: {parts[0]!r}",
                    context={"clause": clause},
                )
            validated_clauses.append(field)
        elif len(parts) == 2:
            # field + direction
            field = parts[0].lower()
            direction = parts[1].lower()
            if not _IDENTIFIER_RE.match(field):
                raise ValidationError(
                    f"Invalid ORDER BY field: {parts[0]!r}",
                    context={"clause": clause},
                )
            if direction not in _ALLOWED_DIRECTIONS:
                raise ValidationError(
                    f"Invalid ORDER BY direction: {parts[1]!r}. "
                    f"Allowed: {', '.join(sorted(_ALLOWED_DIRECTIONS))}",
                    context={"clause": clause, "direction": parts[1]},
                )
            validated_clauses.append(f"{field} {direction}")
        else:
            raise ValidationError(
                f"Invalid ORDER BY clause: {clause!r}",
                context={"clause": clause},
            )

    return ", ".join(validated_clauses)


def validate_column_list(columns: str) -> list[str]:
    """Validate a comma-separated column list. Returns validated column names.

    Each column must match the identifier pattern.
    """
    if not columns or not columns.strip():
        raise ValidationError("Column list cannot be empty")

    result: list[str] = []
    for col in columns.split(","):
        col = col.strip()
        if not col:
            continue
        ensure_safe_identifier(col, "column")
        result.append(col)

    if not result:
        raise ValidationError("Column list has no valid columns")
    return result


def safe_query_identifier(value: str, kind: str = "table") -> str:
    """Alias for :func:`ensure_safe_identifier` with a default kind.

    Convenience for the most common case: validating a table name.
    """
    return ensure_safe_identifier(value, kind)


def is_safe_identifier(value: str) -> bool:
    """Return True if *value* is a safe SQL identifier (no raise)."""
    return isinstance(value, str) and bool(_IDENTIFIER_RE.match(value))


def sanitize_identifier(value: str) -> str | None:
    """Return a sanitized version of *value* if it can be made safe, else None.

    Strips non-identifier characters and checks the result. Useful for
    user input that may have trailing/leading whitespace or mixed case.
    """
    if not isinstance(value, str):
        return None
    # Strip non-alphanumeric-underscore characters
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", value)
    if not cleaned:
        return None
    # Ensure it starts with a letter or underscore
    if cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    if _IDENTIFIER_RE.match(cleaned):
        return cleaned
    return None
