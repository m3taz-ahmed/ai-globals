"""Multi-touch attribution models.

Implements last-click, first-click, linear, and position-based (U-shaped)
attribution over an ordered list of touchpoints. Inspired by Matomo's
campaign/referrer attribution and Plausible goal events (2.7.4).

A touchpoint is a dict that must contain a ``channel`` key. The list order
represents chronological sequence. Raises ``ValidationError`` on empty or
malformed input.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from runtime.schemas import ValidationError

Touchpoint = dict[str, Any]


def _channels(touchpoints: list[Touchpoint]) -> list[str]:
    if not touchpoints:
        raise ValidationError("touchpoints must not be empty")
    channels: list[str] = []
    for idx, tp in enumerate(touchpoints):
        if not isinstance(tp, dict) or "channel" not in tp:
            raise ValidationError(
                "each touchpoint needs a 'channel' key",
                context={"index": idx},
            )
        channels.append(str(tp["channel"]))
    return channels


def last_click(touchpoints: list[Touchpoint]) -> dict[str, float]:
    """100% credit to the final touchpoint's channel."""
    channels = _channels(touchpoints)
    return {channels[-1]: 1.0}


def first_click(touchpoints: list[Touchpoint]) -> dict[str, float]:
    """100% credit to the first touchpoint's channel."""
    channels = _channels(touchpoints)
    return {channels[0]: 1.0}


def linear(touchpoints: list[Touchpoint]) -> dict[str, float]:
    """Equal credit split across every touchpoint."""
    channels = _channels(touchpoints)
    share = 1.0 / len(channels)
    credit: dict[str, float] = defaultdict(float)
    for ch in channels:
        credit[ch] += share
    return dict(credit)


def position_based(touchpoints: list[Touchpoint]) -> dict[str, float]:
    """U-shaped: 40% first, 40% last, 20% split among the middle."""
    channels = _channels(touchpoints)
    n = len(channels)
    credit: dict[str, float] = defaultdict(float)
    if n == 1:
        credit[channels[0]] = 1.0
        return dict(credit)
    if n == 2:
        credit[channels[0]] = 0.5
        credit[channels[1]] = 0.5
        return dict(credit)
    middle = n - 2
    middle_share = 0.2 / middle
    credit[channels[0]] = 0.4
    credit[channels[-1]] = 0.4
    for ch in channels[1:-1]:
        credit[ch] += middle_share
    return dict(credit)
