"""Tests for runtime/text_sanitize.py — invisible codepoint sanitization.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

import pytest

from runtime.text_sanitize import (
    is_invisible_codepoint,
    sanitize_text,
    sanitize_text_or_none,
)


class TestIsInvisibleCodepoint:
    def test_zero_width_space(self) -> None:
        assert is_invisible_codepoint(0x200B) is True

    def test_bidi_override(self) -> None:
        assert is_invisible_codepoint(0x202E) is True

    def test_tag_block(self) -> None:
        assert is_invisible_codepoint(0xE0001) is True

    def test_normal_char(self) -> None:
        assert is_invisible_codepoint(ord("A")) is False

    def test_space(self) -> None:
        assert is_invisible_codepoint(ord(" ")) is False

    def test_arabic_letter(self) -> None:
        assert is_invisible_codepoint(ord("ا")) is False  # noqa: RUF001


class TestSanitizeText:
    def test_clean_text_unchanged(self) -> None:
        clean, removed = sanitize_text("Hello World")
        assert clean == "Hello World"
        assert removed == 0

    def test_strips_zero_width_space(self) -> None:
        dirty = "Hello\u200BWorld"
        clean, removed = sanitize_text(dirty)
        assert clean == "HelloWorld"
        assert removed == 1

    def test_strips_multiple(self) -> None:
        dirty = "A\u200BB\u200EC\u202ED"
        clean, removed = sanitize_text(dirty)
        assert clean == "ABCD"
        assert removed == 3

    def test_preserves_rtl_prose(self) -> None:
        arabic = "مرحبا بالعالم"
        clean, removed = sanitize_text(arabic)
        assert clean == arabic
        assert removed == 0

    def test_strips_tag_block(self) -> None:
        dirty = "text\U000E0001more"
        clean, removed = sanitize_text(dirty)
        assert clean == "textmore"
        assert removed == 1

    def test_empty_string(self) -> None:
        clean, removed = sanitize_text("")
        assert clean == ""
        assert removed == 0

    def test_type_error_for_non_string(self) -> None:
        with pytest.raises(TypeError):
            sanitize_text(123)  # type: ignore[arg-type]


class TestSanitizeTextOrNone:
    def test_none_passes_through(self) -> None:
        clean, removed = sanitize_text_or_none(None)
        assert clean is None
        assert removed == 0

    def test_string_sanitized(self) -> None:
        clean, removed = sanitize_text_or_none("Hello\u200BWorld")
        assert clean == "HelloWorld"
        assert removed == 1
