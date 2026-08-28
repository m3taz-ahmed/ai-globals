"""Tests for persona reset trigger commands — /reset, #انتحل, etc."""

from __future__ import annotations

from runtime.persona import (
    RESET_TRIGGERS,
    PersonaDetector,
    inject_persona_context,
    is_persona_reset_command,
)

# --- is_persona_reset_command ---

def test_reset_slash_command() -> None:
    assert is_persona_reset_command("/reset")


def test_reset_hashtag_command() -> None:
    assert is_persona_reset_command("#reset")


def test_reset_arabic_slash() -> None:
    assert is_persona_reset_command("/انتحل")


def test_reset_arabic_hashtag() -> None:
    assert is_persona_reset_command("#شخصيات")


def test_reset_with_extra_text() -> None:
    assert is_persona_reset_command("/reset to backend mode")


def test_reset_arabic_with_extra_text() -> None:
    assert is_persona_reset_command("/بدّل لـ backend")


def test_normal_text_not_reset() -> None:
    assert not is_persona_reset_command("اكتب backend API")


def test_empty_text_not_reset() -> None:
    assert not is_persona_reset_command("")


def test_reset_not_substring() -> None:
    """Reset command must be at start, not embedded in text."""
    assert not is_persona_reset_command("please /reset now")


def test_all_triggers_are_valid_reset_commands() -> None:
    """Every trigger in RESET_TRIGGERS should be detected as a reset command."""
    for trigger in RESET_TRIGGERS:
        assert is_persona_reset_command(trigger), f"Trigger {trigger!r} not detected"


# --- inject_persona_context with reset ---

def test_reset_clears_existing_persona_and_redetects() -> None:
    """When /reset is sent, existing persona fields are cleared and re-detected."""
    detector = PersonaDetector()
    context: dict[str, object] = {
        "message": "صمملي landing page",
        "persona": "UX",
        "skill": "frontend-ui-expert",
        "personas": ["UX"],
        "skills": ["frontend-ui-expert"],
        "lords": ["design-taste"],
    }
    inject_persona_context(detector, context)
    # Without reset, persona stays UX
    assert context["persona"] == "UX"

    # Now send /reset with a backend hint
    context["message"] = "/reset اكتب backend API مع idempotency"
    inject_persona_context(detector, context)
    # Persona should be re-detected based on the new text
    assert context["persona"] != "UX" or "backend" in str(context.get("lords", []))
    # Old lords should be gone, new ones based on backend text
    assert "design-taste" not in context.get("lords", [])


def test_reset_without_hint_redetects_on_full_text() -> None:
    """Bare /reset still works — re-detects on the command itself."""
    detector = PersonaDetector()
    context: dict[str, object] = {
        "message": "/reset",
        "persona": "DEV",
        "personas": ["DEV"],
    }
    inject_persona_context(detector, context)
    # Persona fields should be present (re-detected)
    assert "persona" in context
    assert "personas" in context


def test_non_reset_message_preserves_existing_persona() -> None:
    """Normal messages don't trigger re-detection when persona is already set."""
    detector = PersonaDetector()
    context: dict[str, object] = {
        "message": "اكتب backend API",
        "persona": "UX",
        "personas": ["UX"],
        "skills": ["frontend-ui-expert"],
    }
    inject_persona_context(detector, context)
    # Persona stays UX — not re-detected
    assert context["persona"] == "UX"
    assert context["skills"] == ["frontend-ui-expert"]


def test_reset_switches_from_ux_to_dev() -> None:
    """Sending /reset with backend keywords switches persona from UX to DEV."""
    detector = PersonaDetector()
    # First message: UX persona
    ctx1: dict[str, object] = {"message": "صمملي landing page جميل"}
    inject_persona_context(detector, ctx1)
    assert ctx1["persona"] == "UX"

    # Second message in same context: reset + backend keywords
    ctx1["message"] = "/reset اكتب backend API مع database migration safety"
    inject_persona_context(detector, ctx1)
    # Should now detect DEV or DATA persona
    assert ctx1["persona"] in ("DEV", "DATA", "ARCH")
    assert "backend-design" in ctx1.get("lords", [])


def test_reset_arabic_switches_persona() -> None:
    """Arabic reset command /انتحل works the same as /reset."""
    detector = PersonaDetector()
    context: dict[str, object] = {
        "message": "صمملي موقع",
        "persona": "UX",
        "personas": ["UX"],
    }
    inject_persona_context(detector, context)
    assert context["persona"] == "UX"

    context["message"] = "/انتحل اكتب playwright e2e testing smoke test"
    inject_persona_context(detector, context)
    assert "qa-automation" in context.get("lords", [])
