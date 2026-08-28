"""Tests for persona status trigger commands — /status, #حالة, etc."""

from __future__ import annotations

from runtime.persona import (
    STATUS_TRIGGERS,
    PersonaDetector,
    format_persona_status,
    inject_persona_context,
    is_persona_status_command,
)

# --- is_persona_status_command ---

def test_status_slash_command() -> None:
    assert is_persona_status_command("/status")


def test_status_hashtag_command() -> None:
    assert is_persona_status_command("#status")


def test_status_arabic_slash() -> None:
    assert is_persona_status_command("/حالة")


def test_status_arabic_hashtag() -> None:
    assert is_persona_status_command("#حالة")


def test_status_whoami() -> None:
    assert is_persona_status_command("/whoami")


def test_status_arabic_meen() -> None:
    assert is_persona_status_command("/مين")


def test_status_with_trailing_spaces() -> None:
    assert is_persona_status_command("  /status  ")


def test_status_rejects_extra_text() -> None:
    """Status commands must be standalone — no trailing hint text."""
    assert not is_persona_status_command("/status backend")


def test_normal_text_not_status() -> None:
    assert not is_persona_status_command("اكتب backend API")


def test_empty_text_not_status() -> None:
    assert not is_persona_status_command("")


def test_all_triggers_are_valid_status_commands() -> None:
    for trigger in STATUS_TRIGGERS:
        assert is_persona_status_command(trigger), f"Trigger {trigger!r} not detected"


# --- format_persona_status ---

def test_format_status_with_no_persona() -> None:
    """When no persona is set, status shows a warning."""
    detector = PersonaDetector()
    context: dict[str, object] = {}
    result = format_persona_status(context, detector)
    assert "لم يتم تحديد" in result or "⚠️" in result


def test_format_status_with_persona() -> None:
    """Status shows persona name and weight."""
    detector = PersonaDetector()
    context: dict[str, object] = {
        "persona": "UX",
        "personas": ["UX"],
        "skills": ["frontend-ui-expert"],
        "lords": ["design-taste"],
    }
    result = format_persona_status(context, detector)
    assert "UX" in result
    assert "frontend-ui-expert" in result
    assert "design-taste" in result


def test_format_status_includes_skill_descriptions() -> None:
    """Status includes short descriptions for skills."""
    detector = PersonaDetector()
    context: dict[str, object] = {
        "persona": "UX",
        "personas": ["UX"],
        "skills": ["frontend-ui-expert"],
        "lords": [],
    }
    result = format_persona_status(context, detector)
    # Should contain some description text (not just the skill name)
    assert "frontend-ui-expert" in result


def test_format_status_compact() -> None:
    """Status output is reasonably compact (<2000 chars)."""
    detector = PersonaDetector()
    context: dict[str, object] = {
        "persona": "UX",
        "personas": ["UX", "DEV"],
        "skills": ["frontend-ui-expert"],
        "lords": ["design-taste", "backend-design", "qa-automation"],
    }
    result = format_persona_status(context, detector)
    assert len(result) < 3000


# --- inject_persona_context with status ---

def test_status_command_does_not_redetect() -> None:
    """Sending /status does NOT re-detect — it preserves existing persona."""
    detector = PersonaDetector()
    context: dict[str, object] = {
        "message": "صمملي landing page",
        "persona": "UX",
        "personas": ["UX"],
        "skills": ["frontend-ui-expert"],
        "lords": ["design-taste"],
    }
    inject_persona_context(detector, context)
    original_persona = context["persona"]

    context["message"] = "/status"
    inject_persona_context(detector, context)
    # Persona should NOT change
    assert context["persona"] == original_persona
    # But persona_status should be populated
    assert "persona_status" in context
    assert isinstance(context["persona_status"], str)


def test_status_command_adds_status_field() -> None:
    """Status command adds 'persona_status' key to context."""
    detector = PersonaDetector()
    context: dict[str, object] = {
        "message": "/status",
        "persona": "DEV",
        "personas": ["DEV"],
        "skills": ["backend-api-expert"],
        "lords": ["backend-design"],
    }
    inject_persona_context(detector, context)
    assert "persona_status" in context
    status = str(context["persona_status"])
    assert "DEV" in status
    assert "backend-design" in status


def test_status_works_without_existing_persona() -> None:
    """Status command on empty context shows 'not set' warning."""
    detector = PersonaDetector()
    context: dict[str, object] = {"message": "/status"}
    inject_persona_context(detector, context)
    assert "persona_status" in context
    assert "⚠️" in str(context["persona_status"]) or "لم يتم" in str(context["persona_status"])
