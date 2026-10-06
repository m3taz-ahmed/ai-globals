"""Skill lifecycle: probation → graduation review → capacity contention → archive.

Deterministic skill-survival engine ported from tigerless-labs/autoharness
(MIT) to aiZee. Survival criterion is **call rate** (use count / requests
since the skill landed), not wall-clock:

- **Probation** — a skill whose denominator (requests since its anchor) is
  below the maturity threshold stays live, is never evicted, and does not
  count against the capacity cap.
- **Graduation review** — at the probation boundary a mature member with
  zero use AND zero view is archived: genuine dormancy. A viewed skill had
  recall value, so use==0 alone is not enough to kill it.
- **Capacity contention** — graduates die only when the mature pool exceeds
  the cap; the lowest call rates are archived first.

Safety boundary: only skills registered as ``origin="learned"`` (or another
explicit managed origin) are lifecycle-managed. Hand-authored skills are
never archived — mirroring autoharness's "only its own skills" rule.

State: ``state/skill_lifecycle.json`` (watermarks + member registry) and a
per-skill append-only ledger at ``state/skill_ledger/<name>.jsonl``.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.schemas import StorageError, ValidationError

_logger = logging.getLogger(__name__)

STATE_FILENAME = "skill_lifecycle.json"
DEFAULT_MATURITY = 100
DEFAULT_CAPACITY = 50
_MANAGED_ORIGINS = frozenset({"learned", "imported", "generated"})


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rate(use: int, denom: int) -> float:
    return use / denom if denom else 0.0


@dataclass
class SkillMember:
    """A lifecycle-managed skill's watermarks.

    Attributes:
        name: Skill identifier.
        use: Times the skill was invoked (``aizee skill invoke`` / load-for-use).
        view: Times the skill was surfaced to an agent (detect/list/inject).
        anchor: Layer request count when the skill was registered.
        origin: Management class — only ``learned``/``imported``/``generated``
            are lifecycle-managed.
    """

    name: str
    use: int = 0
    view: int = 0
    anchor: int = 0
    origin: str = "learned"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "use": self.use,
            "view": self.view,
            "anchor": self.anchor,
            "origin": self.origin,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SkillMember:
        return SkillMember(
            name=str(data.get("name", "")),
            use=int(data.get("use", data.get("calls", 0))),
            view=int(data.get("view", 0)),
            anchor=int(data.get("anchor", 0)),
            origin=str(data.get("origin", "learned")),
        )


def evaluate(
    members: list[SkillMember],
    request_count: int,
    *,
    maturity: int = DEFAULT_MATURITY,
    capacity: int = DEFAULT_CAPACITY,
    review_suspended: bool = False,
) -> list[str]:
    """Pure decision: which managed skills should be archived.

    Returns the sorted archive list. Reads only cumulative watermarks —
    deterministic and replayable from any state snapshot.
    """
    archive: set[str] = set()
    survivors: list[tuple[float, str]] = []
    for m in members:
        if m.origin not in _MANAGED_ORIGINS:
            continue  # hand-authored skills are never lifecycle-managed
        denom = max(0, request_count - m.anchor)
        if denom < maturity:
            continue  # probation: live, not evicted, not counted against cap
        if m.use == 0:
            # Graduation review (softened): zero use AND zero view = dormancy.
            if not review_suspended and m.view == 0:
                archive.add(m.name)
            continue
        survivors.append((_rate(m.use, denom), m.name))
    if len(survivors) > capacity:
        survivors.sort(key=lambda rn: rn)  # ascending rate, stable by name
        archive.update(name for _, name in survivors[: len(survivors) - capacity])
    return sorted(archive)


@dataclass
class LedgerEvent:
    """One append-only ledger record for a managed skill."""

    event: str  # register | use | view | graduate | archive | fold
    skill: str
    reason: str = ""
    evidence: str = ""
    ts: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "skill": self.skill,
            "reason": self.reason,
            "evidence": self.evidence,
            "ts": self.ts,
        }


class SkillLifecycleManager:
    """Tracks skill usage watermarks and archives dormant managed skills.

    Thread-safe. Fail-safe: missing/corrupt state -> empty registry.
    """

    def __init__(
        self, root: Path, *, maturity: int = DEFAULT_MATURITY, capacity: int = DEFAULT_CAPACITY
    ) -> None:
        self.root = root
        self.maturity = maturity
        self.capacity = capacity
        self._state_dir = root / "state"
        self._state_file = self._state_dir / STATE_FILENAME
        self._ledger_dir = self._state_dir / "skill_ledger"
        self._lock = threading.RLock()
        self._request_count = 0
        self._members: dict[str, SkillMember] = {}
        self._load()

    # --- persistence ------------------------------------------------------

    def _load(self) -> None:
        try:
            raw = json.loads(self._state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(raw, dict):
            return
        self._request_count = int(raw.get("request_count", 0))
        members = raw.get("members", {})
        if isinstance(members, dict):
            self._members = {
                name: SkillMember.from_dict({**cfg, "name": name})
                for name, cfg in members.items()
                if isinstance(cfg, dict)
            }

    def _save(self) -> None:
        try:
            self._state_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "request_count": self._request_count,
                "members": {n: m.to_dict() for n, m in self._members.items()},
            }
            tmp = self._state_file.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(self._state_file)
        except OSError as exc:
            raise StorageError(f"skill_lifecycle: cannot persist state: {exc}") from exc

    def _append_ledger(self, event: LedgerEvent) -> None:
        try:
            self._ledger_dir.mkdir(parents=True, exist_ok=True)
            target = self._ledger_dir / f"{event.skill}.jsonl"
            with target.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except OSError as exc:
            _logger.warning("skill_lifecycle: ledger write failed for %s: %s", event.skill, exc)

    def ledger(self, name: str) -> list[dict[str, Any]]:
        """Return a managed skill's ledger entries (oldest first)."""
        target = self._ledger_dir / f"{name}.jsonl"
        try:
            return [
                json.loads(line)
                for line in target.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, json.JSONDecodeError):
            return []

    # --- signals ----------------------------------------------------------

    def record_request(self, n: int = 1) -> int:
        """Advance the layer request counter (one per agent request/session)."""
        with self._lock:
            self._request_count += n
            self._save()
            return self._request_count

    @property
    def request_count(self) -> int:
        return self._request_count

    def register(self, name: str, *, origin: str = "learned", reason: str = "") -> SkillMember:
        """Put a skill under lifecycle management, anchored at current requests."""
        if not name:
            raise ValidationError("skill_lifecycle.register: name required")
        with self._lock:
            member = self._members.get(name)
            if member is None:
                member = SkillMember(name=name, anchor=self._request_count, origin=origin)
                self._members[name] = member
                self._append_ledger(
                    LedgerEvent("register", name, reason=reason or f"origin={origin}")
                )
            self._save()
            return member

    def record_use(self, name: str, n: int = 1) -> None:
        """Count a real invocation of a managed skill."""
        with self._lock:
            member = self._members.get(name)
            if member is None:
                return  # unmanaged skills are never tracked
            member.use += n
            self._append_ledger(LedgerEvent("use", name))
            self._save()

    def record_view(self, name: str, n: int = 1) -> None:
        """Count a surfacing (skill shown to an agent without invocation)."""
        with self._lock:
            member = self._members.get(name)
            if member is None:
                return
            member.view += n
            self._save()

    def members(self) -> list[SkillMember]:
        with self._lock:
            return list(self._members.values())

    # --- lifecycle ----------------------------------------------------------

    def evaluate(self, *, review_suspended: bool = False) -> list[str]:
        """Return the current archive list (deterministic, no side effects)."""
        with self._lock:
            return evaluate(
                list(self._members.values()),
                self._request_count,
                maturity=self.maturity,
                capacity=self.capacity,
                review_suspended=review_suspended,
            )

    def archive(self, name: str, *, reason: str = "evaluate") -> bool:
        """Move a managed skill into ``skills/_archive/`` and record it.

        Only members on the evaluate() archive list may be archived through
        the manager (enforced unless ``reason="manual"``). Returns True when
        the skill was archived.
        """
        with self._lock:
            member = self._members.get(name)
            if member is None:
                return False
            if reason != "manual" and name not in self.evaluate():
                return False
            skills_dir = self.root / "skills"
            archived = self._move_to_archive(skills_dir, name)
            self._append_ledger(LedgerEvent("archive", name, reason=reason))
            del self._members[name]
            self._save()
            return archived

    def _move_to_archive(self, skills_dir: Path, name: str) -> bool:
        """Relocate skill file or dir under ``skills/_archive/``. Returns success."""
        archive_dir = skills_dir / "_archive"
        moved = False
        for candidate in (skills_dir / f"{name}.md", skills_dir / name):
            if not candidate.exists():
                continue
            archive_dir.mkdir(parents=True, exist_ok=True)
            try:
                candidate.rename(archive_dir / candidate.name)
                moved = True
            except OSError as exc:
                _logger.warning("skill_lifecycle: archive move failed for %s: %s", candidate, exc)
        return moved

    def fold(self, winner: str, loser: str, *, reason: str = "") -> None:
        """Record a merge: ``loser`` was absorbed into ``winner``.

        A fold is never mistaken for a death — the ledger records which skill
        absorbed which, and the loser's use/view counters transfer to the
        winner before the loser leaves the pool.
        """
        with self._lock:
            win = self._members.get(winner)
            lose = self._members.pop(loser, None)
            if win is not None and lose is not None:
                win.use += lose.use
                win.view += lose.view
            self._append_ledger(
                LedgerEvent(
                    "fold",
                    loser,
                    reason=reason or f"absorbed into {winner}",
                    evidence=f"winner={winner}",
                )
            )
            self._save()

    def status(self) -> dict[str, Any]:
        """Report snapshot: counts by phase + the pending archive list."""
        members = self.members()
        managed = [m for m in members if m.origin in _MANAGED_ORIGINS]
        probation = [m for m in managed if (self._request_count - m.anchor) < self.maturity]
        return {
            "request_count": self._request_count,
            "maturity": self.maturity,
            "capacity": self.capacity,
            "managed": len(managed),
            "probation": len(probation),
            "mature": len(managed) - len(probation),
            "archive_pending": self.evaluate(),
        }
