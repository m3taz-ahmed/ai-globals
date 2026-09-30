#!/usr/bin/env python3
"""Curriculum synthesis — turn a target stack into an ordered learning plan.

Given stack names (``laravel-11``, ``react-19`` …) the synthesizer reads
matching ``tech-stack/<pkg>-<ver>.md`` references and emits a staged
curriculum: *foundations* (language/runtime prerequisites) → *core*
(the requested stacks) → *operations* (deploy/security/testing
complements). Output is either a human plan or a ``.task/plan.json``
fragment compatible with ``aizee task decompose``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CurriculumStage:
    name: str
    items: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class Curriculum:
    target: list[str]
    stages: list[CurriculumStage] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "stages": [{"name": s.name, "items": s.items, "rationale": s.rationale} for s in self.stages],
            "missing": self.missing,
        }

    def to_plan_tasks(self) -> list[dict[str, Any]]:
        """Export as a task-contract ``--tasks`` fragment."""
        tasks: list[dict[str, Any]] = []
        prev_id: str | None = None
        for i, stage in enumerate(self.stages):
            tid = f"stage-{i + 1}-{re.sub(r'[^a-z0-9]+', '-', stage.name.lower()).strip('-')}"
            tasks.append(
                {
                    "id": tid,
                    "title": f"{stage.name}: {', '.join(stage.items) or 'review'}",
                    "depends_on": [prev_id] if prev_id else [],
                    "verify_cmd": "",
                    "description": stage.rationale,
                }
            )
            prev_id = tid
        return tasks


_FOUNDATION_PATTERNS = re.compile(
    r"python|node|typescript|javascript|php|go|rust|sql|git|linux|bash", re.IGNORECASE
)
_OPERATIONS_PATTERNS = re.compile(
    r"docker|k8s|kubernetes|nginx|caddy|deploy|ci|github-actions|terraform|security|test|pytest|vitest",
    re.IGNORECASE,
)


def _stack_files(os_root: Path) -> dict[str, Path]:
    ts = os_root / "tech-stack"
    if not ts.is_dir():
        return {}
    return {p.stem.lower(): p for p in ts.glob("*.md")}


def synthesize_curriculum(os_root: Path, targets: list[str]) -> Curriculum:
    """Build a staged curriculum for ``targets`` from ``tech-stack/``."""
    known = _stack_files(os_root)
    cur = Curriculum(target=targets)

    foundations: list[str] = []
    core: list[str] = []
    operations: list[str] = []
    for t in targets:
        key = t.lower()
        matched = next((k for k in known if k == key or k.startswith(key.split("-")[0])), None)
        if matched is None:
            cur.missing.append(t)
            continue
        if _FOUNDATION_PATTERNS.search(matched):
            foundations.append(matched)
        elif _OPERATIONS_PATTERNS.search(matched):
            operations.append(matched)
        else:
            core.append(matched)

    if foundations:
        cur.stages.append(
            CurriculumStage("Foundations", foundations, "language/runtime prerequisites for the target stack")
        )
    if core:
        cur.stages.append(
            CurriculumStage("Core", core, "the requested technologies, in dependency order")
        )
    if operations:
        cur.stages.append(
            CurriculumStage("Operations", operations, "deploy/security/testing complements")
        )
    if not cur.stages:
        cur.stages.append(CurriculumStage("Survey", targets, "no tech-stack refs matched — manual study"))
    return cur


__all__ = ["Curriculum", "CurriculumStage", "synthesize_curriculum"]
