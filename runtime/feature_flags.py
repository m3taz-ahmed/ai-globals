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
            ValidationError: if any percentage is outside [0, 100], or if
                ``segments`` configs are not dicts.
        """
        if segments is None:
            segments = {}
        if not isinstance(segments, dict):
            raise ValidationError(
                "segments must be a dict",
                context={"segments": type(segments).__name__},
            )
        self._check_pct(rollout_pct, "rollout_pct")
        for seg_name, cfg in segments.items():
            if cfg is None:
                cfg = {}
            if not isinstance(cfg, dict):
                raise ValidationError(
                    f"segments.{seg_name} must be a dict",
                    context={f"segments.{seg_name}": type(cfg).__name__},
                )
            ids = cfg.get("ids")
            # Exact identity match on list items (not substring `in` on str).
            if isinstance(ids, (list, tuple, set)):
                if identity in list(ids):
                    return True
            elif isinstance(ids, str) and identity == ids:
                return True
            seg_pct = cfg.get("pct")
            if seg_pct is not None:
                if isinstance(seg_pct, bool) or not isinstance(seg_pct, int):
                    raise ValidationError(
                        f"segments.{seg_name}.pct must be an int in [0, 100]",
                        context={f"segments.{seg_name}.pct": seg_pct},
                    )
                self._check_pct(seg_pct, f"segments.{seg_name}.pct")
                # Consistent with global: same _bucket(flag, identity) scheme;
                # segment is mixed into the identity side so buckets stay
                # isolated per segment but hashed identically.
                if _bucket(flag_name, f"{seg_name}:{identity}") < seg_pct:
                    return True

        return _bucket(flag_name, identity) < rollout_pct

    @staticmethod
    def _check_pct(value: int, label: str) -> None:
        if not 0 <= value <= 100:
            raise ValidationError(
                f"{label} must be in [0, 100]",
                context={label: value},
            )
