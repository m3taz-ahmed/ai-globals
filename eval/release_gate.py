#!/usr/bin/env python3
"""Release gate: block a release when recorded rollouts fail the
reliability priority ladder.

Rollout evidence lives in ``state/release_rollouts.jsonl`` (one JSON
object per line: ``{"task_id", "rollout_id", "status"}``). The gate:

- **skips** (ok) when the evidence file is absent — local/dev runs have
  no rollout data; release pipelines produce it before invoking the gate;
- **fails** when any task verdicts ``KILL`` or ``INSUFFICIENT`` under
  ``eval.reliability.priority_ladder``;
- **passes** when every task with evidence verdicts ``PASS``.

The target threshold and minimum power (``k_min``) are configurable via
``AIZEE_RELEASE_TARGET`` / ``AIZEE_RELEASE_KMIN`` env vars.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.reliability import RolloutStatus, priority_ladder
from runtime.schemas import AizeeError, ErrorSeverity


class ReleaseGateError(AizeeError):
    """Raised when release-gate evaluation fails unexpectedly."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("RELEASE_GATE_ERROR", message, ErrorSeverity.HIGH, context)


DEFAULT_TARGET = 0.80
DEFAULT_KMIN = 5
ROLLOUTS_FILE = "release_rollouts.jsonl"


def main(argv: list[str] | None = None) -> int:
    """CLI entry: ``python eval/release_gate.py [--project DIR]``."""
    import argparse

    parser = argparse.ArgumentParser(description="Reliability release gate")
    parser.add_argument("--project", default="", help="Project root (default: CWD)")
    args = parser.parse_args(argv)
    root = Path(args.project).resolve() if args.project else Path.cwd()
    verdict = ReleaseGate(root).evaluate()
    print(json.dumps(verdict.to_dict(), indent=2))
    return 0 if verdict.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


@dataclass
class GateVerdict:
    """Aggregate release-gate verdict."""

    ok: bool
    skipped: bool
    task_verdicts: dict[str, dict[str, Any]] = field(default_factory=dict)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "skipped": self.skipped,
            "reason": self.reason,
            "task_verdicts": self.task_verdicts,
        }


def load_rollouts(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Group rollout records by task_id. Malformed lines are skipped."""
    tasks: dict[str, list[dict[str, Any]]] = {}
    if not path.exists():
        return tasks
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        task_id = rec.get("task_id")
        status = rec.get("status")
        if not task_id or status not in {s.value for s in RolloutStatus}:
            continue
        tasks.setdefault(task_id, []).append(rec)
    return tasks


class ReleaseGate:
    """Evaluate rollout evidence and decide pass/fail for a release."""

    def __init__(self, project_root: Path, rollouts_file: str = ROLLOUTS_FILE) -> None:
        self.project_root = project_root
        self.rollouts_path = project_root / "state" / rollouts_file

    def record_rollout(self, task_id: str, status: str, rollout_id: int = 0) -> None:
        """Append a rollout record to the evidence file."""
        if status not in {s.value for s in RolloutStatus}:
            raise ReleaseGateError(f"Invalid rollout status: {status!r}", {"status": status})
        self.rollouts_path.parent.mkdir(parents=True, exist_ok=True)
        rec = {"task_id": task_id, "rollout_id": rollout_id, "status": status}
        with self.rollouts_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")

    def evaluate(
        self,
        target: float | None = None,
        k_min: int | None = None,
    ) -> GateVerdict:
        """Run the priority ladder per task over recorded evidence."""
        if target is None:
            target = float(os.environ.get("AIZEE_RELEASE_TARGET", DEFAULT_TARGET))
        if k_min is None:
            k_min = int(os.environ.get("AIZEE_RELEASE_KMIN", DEFAULT_KMIN))

        tasks = load_rollouts(self.rollouts_path)
        if not tasks:
            return GateVerdict(ok=True, skipped=True, reason="no rollout evidence — gate skipped")

        verdicts: dict[str, dict[str, Any]] = {}
        ok = True
        for task_id, recs in tasks.items():
            n = len(recs)
            c = sum(1 for r in recs if r["status"] == RolloutStatus.PASS.value)
            has_sec_fail = any(r["status"] == RolloutStatus.SECURITY_FAIL.value for r in recs)
            audit = priority_ladder(
                n=n, c=c, target=target, k_min=k_min, has_critical_event=has_sec_fail,
            )
            verdicts[task_id] = audit.to_dict()
            if audit.verdict.value != "pass":
                ok = False

        reason = "all tasks pass the reliability ladder" if ok else "one or more tasks failed the release gate"
        return GateVerdict(ok=ok, skipped=False, task_verdicts=verdicts, reason=reason)


__all__ = [
    "DEFAULT_KMIN",
    "DEFAULT_TARGET",
    "ROLLOUTS_FILE",
    "GateVerdict",
    "ReleaseGate",
    "ReleaseGateError",
    "load_rollouts",
]
