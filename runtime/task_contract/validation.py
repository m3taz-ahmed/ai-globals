#!/usr/bin/env python3
"""Plan validation: id shape, deps exist, acyclicity, acceptance presence."""

from __future__ import annotations

import re

from runtime.task_contract.models import ContractTask, TaskContractError

_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate_tasks(tasks: list[ContractTask]) -> None:
    """Reject malformed task graphs before a plan becomes active."""
    if not tasks:
        raise TaskContractError("INVALID_PLAN", "plan needs at least one task")
    seen: set[str] = set()
    for t in tasks:
        if not _ID_RE.match(t.id):
            raise TaskContractError(
                "INVALID_PLAN", f"task id '{t.id}' must be kebab-case", {"id": t.id}
            )
        if t.id in seen:
            raise TaskContractError("INVALID_PLAN", f"duplicate task id '{t.id}'")
        seen.add(t.id)
        if not t.title.strip():
            raise TaskContractError("INVALID_PLAN", f"task '{t.id}' needs a title", {"id": t.id})
        if not t.acceptance:
            raise TaskContractError(
                "INVALID_PLAN", f"task '{t.id}' needs >=1 acceptance check", {"id": t.id}
            )
    for t in tasks:
        for dep in t.depends_on:
            if dep not in seen:
                raise TaskContractError(
                    "INVALID_PLAN",
                    f"task '{t.id}' depends on unknown task '{dep}'",
                    {"id": t.id, "dep": dep},
                )
            if dep == t.id:
                raise TaskContractError("INVALID_PLAN", f"task '{t.id}' cannot depend on itself")
    check_cycles(tasks)


def check_cycles(tasks: list[ContractTask]) -> None:
    """Iterative DFS — dependency graph must be acyclic."""
    deps = {t.id: list(t.depends_on) for t in tasks}
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[tuple[str, bool]] = []
    for start in deps:
        if start in visited:
            continue
        stack.append((start, False))
        while stack:
            node, expanded = stack.pop()
            if expanded:
                visiting.discard(node)
                visited.add(node)
                continue
            if node in visited:
                continue
            if node in visiting:  # pragma: no cover - unreachable: line 70 rejects re-push
                raise TaskContractError(
                    "INVALID_PLAN", f"dependency cycle through task '{node}'", {"node": node}
                )
            visiting.add(node)
            stack.append((node, True))
            for dep in deps.get(node, []):
                if dep in visiting:
                    raise TaskContractError(
                        "INVALID_PLAN",
                        f"dependency cycle through task '{dep}'",
                        {"node": dep},
                    )
                stack.append((dep, False))
