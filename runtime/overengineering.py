#!/usr/bin/env python3
"""Over-engineering detector — flags gold-plating in the active task plan.

Reads the task contract's ``.task/plan.json`` plus the graphify knowledge
graph (``graphify-out/graph.json``) when present, and reports:

- ``unused_produce``: a task's ``produces:`` artifact no other task
  consumes (dead handoffs — classic over-engineering).
- ``orphan_module``: a file in the plan's declared scope that has zero
  inbound edges in graphify (created but unreferenced).
- ``single_impl_abstraction``: scope files defining an abstract
  base/protocol whose graph shows fewer than two implementors.

Advisory only — the detector never blocks; findings land in the task
review report so the human can kill scope creep before it ships.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class OverengineeringFinding:
    kind: str  # unused_produce | orphan_module | single_impl_abstraction
    subject: str
    detail: str
    severity: str = "warn"

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "subject": self.subject, "detail": self.detail, "severity": self.severity}


@dataclass
class OverengineeringReport:
    ok: bool
    findings: list[OverengineeringFinding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "findings": [f.to_dict() for f in self.findings],
            "notes": self.notes,
        }


_ABC_RE = re.compile(r"class\s+(\w+)\s*\(\s*(?:ABC|Protocol)\b")
_PLAN_CANDIDATES = (".task/plan.json", ".ai/task/plan.json", "state/plan.json")


def _load_plan(project_root: Path) -> dict[str, Any]:
    for rel in _PLAN_CANDIDATES:
        p = project_root / rel
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            return data if isinstance(data, dict) else {}
    return {}


def _load_graph(os_root: Path, project_root: Path) -> dict[str, Any] | None:
    for base in (project_root, os_root):
        p = base / "graphify-out" / "graph.json"
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            return data if isinstance(data, dict) else None
    return None


def _produces(plan: dict[str, Any]) -> dict[str, str]:
    """Map produced artifact path -> producing task id."""
    out: dict[str, str] = {}
    for task in plan.get("tasks", []):
        for artifact in task.get("produces", []):
            out[artifact] = str(task.get("id", "?"))
    return out


def _consumes(plan: dict[str, Any]) -> set[str]:
    consumed: set[str] = set()
    for task in plan.get("tasks", []):
        for field_name in ("consumes", "needs", "inputs", "deps"):
            for dep in task.get(field_name, []):
                consumed.add(str(dep))
    return consumed


def _scope_files(plan: dict[str, Any]) -> list[str]:
    scope = plan.get("scope", [])
    if isinstance(scope, dict):
        scope = scope.get("files", [])
    return [str(s) for s in scope]


def _inbound_edges(graph: dict[str, Any] | None, path: str) -> int:
    if not graph:
        return -1
    edges = graph.get("edges") or graph.get("links") or []
    count = 0
    for e in edges:
        tgt = e.get("target") or e.get("dst") or e.get("to") or ""
        if str(tgt).endswith(path) or path.endswith(str(tgt)):
            count += 1
    return count


def detect_overengineering(os_root: Path, project_root: Path) -> OverengineeringReport:
    """Scan the active task plan for gold-plating signals. Advisory only."""
    report = OverengineeringReport(ok=True)
    plan = _load_plan(project_root)
    if not plan:
        report.notes.append("no active task plan — nothing to audit")
        return report

    produced = _produces(plan)
    consumed = _consumes(plan)
    for artifact, producer in produced.items():
        if artifact not in consumed:
            report.findings.append(
                OverengineeringFinding(
                    "unused_produce", artifact,
                    f"task '{producer}' produces an artifact no later task consumes",
                )
            )

    graph = _load_graph(os_root, project_root)
    if graph is None:
        report.notes.append("graphify-out/graph.json absent — skipped orphan/abstraction checks")
        return report

    for rel in _scope_files(plan):
        hits = _inbound_edges(graph, rel)
        if hits == 0:
            report.findings.append(
                OverengineeringFinding(
                    "orphan_module", rel,
                    "declared in plan scope but has zero inbound references in the graph",
                )
            )

    for rel in _scope_files(plan):
        src_path = project_root / rel
        if not src_path.exists() or src_path.suffix != ".py":
            continue
        try:
            text = src_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in _ABC_RE.finditer(text):
            impls = _count_implementors(graph, m.group(1))
            if impls < 2:
                report.findings.append(
                    OverengineeringFinding(
                        "single_impl_abstraction", f"{rel}:{m.group(1)}",
                        f"abstract type has {impls} implementor(s) — an interface for one",
                    )
                )
    return report


def _count_implementors(graph: dict[str, Any] | None, name: str) -> int:
    if not graph:
        return 0
    count = 0
    for e in graph.get("edges") or []:
        if e.get("relation") in {"inherits", "implements", "subclass"} and name in str(e.get("target", "")):
            count += 1
    return count


__all__ = ["OverengineeringFinding", "OverengineeringReport", "detect_overengineering"]
