"""Invisible codepoint sanitization for document-borne prompt injection defense.

Ported from book-to-skill (virgiliojr94/book-to-skill) ``sanitize.py``.
Strips zero-width characters, bidi formatting controls (Trojan Source
CVE-2021-42574), invisible letters, and the Unicode tag block — all
used to hide prompt-injection payloads in documents that an AI agent
might ingest.

Usage::

    from runtime.text_sanitize import sanitize_text
    clean, removed = sanitize_text(maybe_dirty)
    if removed:
        logger.warning("Stripped %d invisible codepoints from input", removed)

The sanitizer is pure (no I/O, no logging) so it can run in any
guardian pre-processing step without side effects.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Attack-shape groupings (kept reviewable by grouping by attack vector)
# ---------------------------------------------------------------------------

# 1. Zero-width and invisible spacers. Render as nothing, so text between
#    them is invisible to a human but plain to the model.
_ZERO_WIDTH_CODEPOINTS: frozenset[int] = frozenset({
    0x200B,  # ZERO WIDTH SPACE
    0x200C,  # ZERO WIDTH NON-JOINER
    0x200D,  # ZERO WIDTH JOINER
    0x2060,  # WORD JOINER
    0xFEFF,  # ZERO WIDTH NO-BREAK SPACE / BOM outside position 0
    0x00AD,  # SOFT HYPHEN — invisible except at a line break
    0x034F,  # COMBINING GRAPHEME JOINER — no rendering effect
    0x180E,  # MONGOLIAN VOWEL SEPARATOR
    0x2061,  # FUNCTION APPLICATION
    0x2062,  # INVISIBLE TIMES
    0x2063,  # INVISIBLE SEPARATOR
    0x2064,  # INVISIBLE PLUS
})

# 2. Bidirectional formatting controls — the Trojan Source class
#    (CVE-2021-42574). These change the order a human SEES while the
#    model reads the logical order. Legitimate RTL text (Arabic, Hebrew)
#    is unaffected: the Unicode Bidi Algorithm derives direction from the
#    characters themselves, so only explicit embeddings/overrides/isolates
#    are dropped.
_BIDI_CONTROL_CODEPOINTS: frozenset[int] = frozenset({
    0x200E,  # LEFT-TO-RIGHT MARK
    0x200F,  # RIGHT-TO-LEFT MARK
    0x061C,  # ARABIC LETTER MARK
    0x202A,  # LEFT-TO-RIGHT EMBEDDING
    0x202B,  # RIGHT-TO-LEFT EMBEDDING
    0x202C,  # POP DIRECTIONAL FORMATTING
    0x202D,  # LEFT-TO-RIGHT OVERRIDE
    0x202E,  # RIGHT-TO-LEFT OVERRIDE
    0x2066,  # LEFT-TO-RIGHT ISOLATE
    0x2067,  # RIGHT-TO-LEFT ISOLATE
    0x2068,  # FIRST STRONG ISOLATE
    0x2069,  # POP DIRECTIONAL ISOLATE
})

# 3. Characters that are not format controls (so a category-based filter
#    misses them) but still render as blank width. Unlike a space they are
#    letters, so they survive whitespace normalisation and can pad hidden
#    text.
_INVISIBLE_LETTER_CODEPOINTS: frozenset[int] = frozenset({
    0x115F,  # HANGUL CHOSEONG FILLER
    0x1160,  # HANGUL JUNGSEONG FILLER
    0x3164,  # HANGUL FILLER
    0xFFA0,  # HALFWIDTH HANGUL FILLER
})

_INVISIBLE_CODEPOINTS: frozenset[int] = (
    _ZERO_WIDTH_CODEPOINTS
    | _BIDI_CONTROL_CODEPOINTS
    | _INVISIBLE_LETTER_CODEPOINTS
)

# 4. The Unicode tag block. Originally language tags, now used to smuggle
#    an entire ASCII payload as invisible "tag" characters.
_TAG_BLOCK_START: int = 0xE0000
_TAG_BLOCK_END: int = 0xE007F


def is_invisible_codepoint(codepoint: int) -> bool:
    """Return ``True`` if *codepoint* renders as nothing and should be stripped.

    Exposed so callers (e.g. a generated-skill scanner) can flag exactly
    what extraction strips. When the sanitizer set and this predicate
    drift, the scanner lets a character through that the sanitizer then
    warns about — or worse, neither layer covers it.
    """
    return (
        codepoint in _INVISIBLE_CODEPOINTS
        or _TAG_BLOCK_START <= codepoint <= _TAG_BLOCK_END
    )


def sanitize_text(text: str) -> tuple[str, int]:
    """Remove invisible code points used for document-borne prompt injection.

    Returns a tuple of ``(clean_text, removed_count)``. The clean text
    preserves all visible characters including legitimate RTL prose
    (Arabic, Hebrew) — only explicit bidi embeddings/overrides/isolates
    and zero-width/invisible formatting are stripped.

    Raises ``TypeError`` for non-string input (never silently coerces).
    """
    if not isinstance(text, str):
        raise TypeError(f"sanitize_text expects str, got {type(text).__name__}")

    kept: list[str] = []
    removed = 0
    for char in text:
        if is_invisible_codepoint(ord(char)):
            removed += 1
            continue
        kept.append(char)
    return "".join(kept), removed


def sanitize_text_or_none(text: str | None) -> tuple[str | None, int]:
    """Like :func:`sanitize_text` but accepts ``None`` and passes it through.

    Convenience for optional fields (e.g. MCP tool parameters that may
    be ``None``).
    """
    if text is None:
        return None, 0
    return sanitize_text(text)
