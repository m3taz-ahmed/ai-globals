"""Marketing compliance pre-send checks.

Validates email/social sends against opt-in, unsubscribe, and GDPR/CAN-SPAM
requirements before any publish action (2.7.11). Raises no exception on
failure (returns a violation list) so callers can gate the action.

Returns a ``(compliant, violations)`` tuple.
"""

from __future__ import annotations

from runtime.schemas import ValidationError

ALLOWED_CHANNELS = {"email", "sms", "push", "social"}


def check_compliance(
    channel: str,
    has_optin: bool,
    has_unsubscribe: bool,
    is_gdpr: bool,
) -> tuple[bool, list[str]]:
    """Check a planned send for compliance violations.

    Args:
        channel: Delivery channel (email/sms/push/social).
        has_optin: Whether the recipient consented.
        has_unsubscribe: Whether an unsubscribe mechanism is present.
        is_gdpr: Whether GDPR rules apply to this send.

    Returns:
        Tuple of (``compliant``, ``violations``) where ``violations`` is a
        list of human-readable reason strings (empty when compliant).

    Raises:
        ValidationError: on an unknown channel.
    """
    if channel not in ALLOWED_CHANNELS:
        raise ValidationError(
            f"unknown channel: {channel}",
            context={"channel": channel, "allowed": sorted(ALLOWED_CHANNELS)},
        )

    violations: list[str] = []

    if channel in {"email", "sms", "push"}:
        if not has_optin:
            violations.append(f"{channel} send requires explicit opt-in")
        if not has_unsubscribe:
            violations.append(f"{channel} send requires an unsubscribe mechanism")

    if is_gdpr:
        if not has_optin:
            violations.append("GDPR requires lawful basis / opt-in")
        if channel in {"email", "sms"} and not has_unsubscribe:
            violations.append("GDPR requires an unsubscribe / opt-out for this channel")

    if channel == "email" and is_gdpr and not has_optin:
        violations.append("CAN-SPAM/GDPR: no consent for commercial email")

    return (len(violations) == 0, violations)
