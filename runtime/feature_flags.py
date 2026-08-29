"""Hash-based feature flag evaluation with segments and rollout.

Portable reimplementation of the GrowthBook / Flagsmith rollout model
(2.7.3). Flag state is derived deterministically from a hash of the flag
name plus an identity, so the same identity always gets the same result.

Raises ``ValidationError`` on out-of-range rollout percentages.
"""

from __future__ import annotations

import hashlib
from typing import Any

from runtime.schemas import ValidationError


def _bucket(flag_name: str, identity: str) -> int:
    """Map (flag, identity) to a stable integer in [0, 100)."""
    digest = hashlib.sha256(f"{flag_name}:{identity}".encode()).hexdigest()
    return int(digest[:8], 16) % 100


class FeatureFlagger:
    """Evaluates feature flags for a given identity."""

    def evaluate(
        self,
        flag_name: str,
        identity: str,
        segments: dict[str, Any],
        rollout_pct: int,
    ) -> bool:
        """Decide whether ``identity`` should see ``flag_name``.

        Args:
            flag_name: Name of the flag.
            identity: Stable per-user/entity identifier (e.g. user id).
            segments: Mapping of segment name to a config dict. Each config
                may contain ``ids`` (list of identities force-enabled) and/or
                ``pct`` (integer rollout percentage for that segment).
            rollout_pct: Global rollout percentage (0-100) used when no
                segment matches.

        Returns:
            True if the flag is enabled for this identity.

        Raises:
            ValidationError: if any percentage is outside [0, 100].
        """
        self._check_pct(rollout_pct, "rollout_pct")
        for seg_name, cfg in segments.items():
            cfg = cfg or {}
            ids = cfg.get("ids")
            if ids and identity in ids:
                return True
            seg_pct = cfg.get("pct")
            if seg_pct is not None:
                self._check_pct(seg_pct, f"segments.{seg_name}.pct")
                if _bucket(f"{flag_name}:{seg_name}", identity) < seg_pct:
                    return True

        return _bucket(flag_name, identity) < rollout_pct

    @staticmethod
    def _check_pct(value: int, label: str) -> None:
        if not 0 <= value <= 100:
            raise ValidationError(
                f"{label} must be in [0, 100]",
                context={label: value},
            )
