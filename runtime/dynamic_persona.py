"""Dynamic evolving personas for AI Global OS.

Personas accumulate experience over time across three evolutionary layers:

1. **Core Identity** (0-10 interactions) — the persona's baseline skill set.
2. **Accumulation** (11-50 interactions) — patterns and expertise start to form.
3. **Deep Personality** (51+ interactions) — refined expertise and learned
   patterns that bias persona selection toward proven performers.

The system is intentionally stdlib-only and persists state to
``state/persona_experiences.json`` relative to the OS root.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Evolution thresholds expressed as interaction counts.
CORE_THRESHOLD = 0
ACCUMULATION_THRESHOLD = 11
DEEP_THRESHOLD = 51

# Expertise scoring constants.
EXPERTISE_MAX = 100.0
EXPERTISE_INCREMENT = 5.0
EXPERTISE_FAILURE_DECAY = 1.0

# Cap on retained context history to bound state file growth.
CONTEXT_HISTORY_LIMIT = 50
# Cap on retained learned patterns.
LEARNED_PATTERNS_LIMIT = 100


def _utc_now() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _clamp_score(value: float) -> float:
    """Clamp an expertise score into the valid [0, 100] range."""
    return max(0.0, min(EXPERTISE_MAX, value))


@dataclass
class PersonaExperience:
    """Accumulated experience for a single persona.

    Attributes:
        persona_id: Unique persona code (e.g. ``"ARCH"``).
        interactions: Total number of recorded interactions.
        successes: Number of successful interactions.
        expertise_areas: Mapping of expertise area name to score (0-100).
        learned_patterns: Mapping of pattern description to observation count.
        context_history: Bounded list of recent interaction context snapshots.
        created_at: ISO-8601 timestamp of first interaction.
        updated_at: ISO-8601 timestamp of most recent interaction.
    """

    persona_id: str
    interactions: int = 0
    successes: int = 0
    expertise_areas: dict[str, float] = field(default_factory=dict)
    learned_patterns: dict[str, int] = field(default_factory=dict)
    context_history: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    @property
    def success_rate(self) -> float:
        """Return the success rate as a value in [0.0, 1.0]."""
        if self.interactions == 0:
            return 0.0
        return self.successes / self.interactions

    @property
    def evolution_level(self) -> str:
        """Return the evolution level name for this persona."""
        return _evolution_level_for(self.interactions)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the experience to a plain dict."""
        return asdict(self)


def _evolution_level_for(interactions: int) -> str:
    """Map an interaction count to an evolution level name."""
    if interactions >= DEEP_THRESHOLD:
        return "deep"
    if interactions >= ACCUMULATION_THRESHOLD:
        return "accumulation"
    return "core"


class DynamicPersonaManager:
    """Manages persona evolution and experience accumulation.

    The manager is thread-safe and persists state to
    ``<root>/state/persona_experiences.json``. When ``root`` is omitted the
    OS root is discovered via ``AGENT_OS_ROOT`` or by walking parent
    directories looking for the ``.ai`` marker.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = self._resolve_root(root)
        self.state_file = self.root / "state" / "persona_experiences.json"
        self._experiences: dict[str, PersonaExperience] = {}
        self._lock = threading.RLock()
        self._load()

    # ------------------------------------------------------------------
    # Root resolution
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_root(root: Path | None) -> Path:
        """Resolve the OS root directory."""
        if root is not None:
            return Path(root)
        env_root = os.environ.get("AGENT_OS_ROOT")
        if env_root:
            return Path(env_root)
        # Walk up from this file to find the .ai marker directory.
        here = Path(__file__).resolve()
        for parent in [here.parent, *here.parents]:
            if parent.name == ".ai":
                return parent
        return here.parent

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load(self) -> None:
        """Load experiences from the state file if it exists."""
        if not self.state_file.exists():
            return
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        for persona_id, payload in data.get("experiences", {}).items():
            self._experiences[persona_id] = PersonaExperience(
                persona_id=payload.get("persona_id", persona_id),
                interactions=int(payload.get("interactions", 0)),
                successes=int(payload.get("successes", 0)),
                expertise_areas={
                    k: float(v) for k, v in payload.get("expertise_areas", {}).items()
                },
                learned_patterns={
                    k: int(v) for k, v in payload.get("learned_patterns", {}).items()
                },
                context_history=list(payload.get("context_history", [])),
                created_at=payload.get("created_at", ""),
                updated_at=payload.get("updated_at", ""),
            )

    def save(self) -> None:
        """Persist all experiences to the state file."""
        with self._lock:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "experiences": {
                    pid: exp.to_dict() for pid, exp in self._experiences.items()
                }
            }
            tmp = self.state_file.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(self.state_file)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------
    def _get_or_create(self, persona_id: str) -> PersonaExperience:
        """Return the experience record for a persona, creating it if needed."""
        exp = self._experiences.get(persona_id)
        if exp is None:
            now = _utc_now()
            exp = PersonaExperience(persona_id=persona_id, created_at=now, updated_at=now)
            self._experiences[persona_id] = exp
        return exp

    def record_interaction(
        self,
        persona_id: str,
        success: bool,
        context: dict[str, Any] | None = None,
    ) -> PersonaExperience:
        """Record a single interaction for a persona.

        Args:
            persona_id: The persona code that handled the interaction.
            success: Whether the interaction succeeded.
            context: Optional context dict. May contain ``area`` (expertise
                area to adjust) and ``pattern`` (a learned pattern to count).

        Returns:
            The updated :class:`PersonaExperience`.
        """
        with self._lock:
            exp = self._get_or_create(persona_id)
            exp.interactions += 1
            if success:
                exp.successes += 1

            ctx = dict(context or {})
            area = ctx.get("area")
            if area:
                current = exp.expertise_areas.get(area, 0.0)
                if success:
                    current += EXPERTISE_INCREMENT
                else:
                    current -= EXPERTISE_FAILURE_DECAY
                exp.expertise_areas[area] = round(_clamp_score(current), 2)

            pattern = ctx.get("pattern")
            if pattern:
                exp.learned_patterns[pattern] = exp.learned_patterns.get(pattern, 0) + 1
                if len(exp.learned_patterns) > LEARNED_PATTERNS_LIMIT:
                    # Drop least-observed patterns first.
                    keep = sorted(
                        exp.learned_patterns.items(),
                        key=lambda kv: kv[1],
                        reverse=True,
                    )[:LEARNED_PATTERNS_LIMIT]
                    exp.learned_patterns = dict(keep)

            snapshot = {k: v for k, v in ctx.items() if k in ("area", "pattern", "task_type")}
            snapshot["success"] = bool(success)
            snapshot["timestamp"] = _utc_now()
            exp.context_history.append(snapshot)
            if len(exp.context_history) > CONTEXT_HISTORY_LIMIT:
                exp.context_history = exp.context_history[-CONTEXT_HISTORY_LIMIT:]

            exp.updated_at = _utc_now()
            return exp

    def get_experience(self, persona_id: str) -> PersonaExperience | None:
        """Return the experience record for a persona, or ``None`` if absent."""
        with self._lock:
            return self._experiences.get(persona_id)

    def get_evolution_level(self, persona_id: str) -> str:
        """Return the evolution level for a persona.

        Returns ``"core"`` for personas with no recorded experience as well,
        so that unknown personas are treated as baseline core identity.
        """
        with self._lock:
            exp = self._experiences.get(persona_id)
            if exp is None:
                return "core"
            return exp.evolution_level

    def get_recommended_persona(self, task_type: str) -> str:
        """Recommend the best persona for a task type.

        Personas are ranked by expertise score for the given ``task_type``
        (treated as an expertise area). Ties are broken by success rate then
        total interactions. Returns an empty string when no persona has
        experience with the task type.
        """
        with self._lock:
            candidates: list[tuple[str, float, float, int]] = []
            for persona_id, exp in self._experiences.items():
                score = exp.expertise_areas.get(task_type, 0.0)
                if score <= 0.0:
                    continue
                candidates.append(
                    (persona_id, score, exp.success_rate, exp.interactions)
                )
            if not candidates:
                return ""
            candidates.sort(key=lambda c: (c[1], c[2], c[3]), reverse=True)
            return candidates[0][0]

    def export_experience(self, persona_id: str) -> dict[str, Any]:
        """Export a single persona's experience as a plain dict.

        Returns an empty dict when the persona has no recorded experience.
        """
        with self._lock:
            exp = self._experiences.get(persona_id)
            if exp is None:
                return {}
            return exp.to_dict()

    def import_experience(self, data: dict[str, Any]) -> PersonaExperience:
        """Import (or overwrite) a persona experience from a plain dict.

        Args:
            data: A dict as produced by :meth:`export_experience` or
                :meth:`PersonaExperience.to_dict`.

        Returns:
            The imported :class:`PersonaExperience`.
        """
        persona_id = data.get("persona_id", "")
        if not persona_id:
            raise ValueError("import_experience requires a 'persona_id' field")
        with self._lock:
            exp = PersonaExperience(
                persona_id=str(persona_id),
                interactions=int(data.get("interactions", 0)),
                successes=int(data.get("successes", 0)),
                expertise_areas={
                    str(k): float(v) for k, v in data.get("expertise_areas", {}).items()
                },
                learned_patterns={
                    str(k): int(v) for k, v in data.get("learned_patterns", {}).items()
                },
                context_history=list(data.get("context_history", [])),
                created_at=str(data.get("created_at", "")),
                updated_at=str(data.get("updated_at", "")),
            )
            self._experiences[persona_id] = exp
            return exp

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------
    def list_personas(self) -> list[str]:
        """Return all persona IDs that have recorded experience."""
        with self._lock:
            return list(self._experiences.keys())

    def reset(self) -> None:
        """Clear all recorded experience (in-memory only; does not delete file)."""
        with self._lock:
            self._experiences.clear()
