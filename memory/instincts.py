"""Learned instincts (``aizee.instinct.v1``) — atomic trigger→action pairs.

Minimal continuous-learning layer over :class:`MemoryStore`. An instinct is a
single observed behavior ("when X happens, do Y") that starts at low
confidence and strengthens with each reinforcement. Scopes:

- ``project`` — lives in the repo vault; isolated so one project's quirks
  never leak into another.
- ``user``    — follows the operator; an instinct *promotes* here once the
  same behavior is observed in two or more projects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from memory.handoff import scope_root

SCHEMA = "aizee.instinct.v1"
_KIND = "instinct"
_BANK = "instincts"
_BASE_CONF = 0.3
_STEP = 0.15
_MAX_CONF = 0.9
_PROMOTE_PROJECTS = 2


def _store(root: Path, scope: str) -> Any:
    from memory.store import MemoryStore

    return MemoryStore(scope_root(scope, root))


def _meta(mem: Any) -> dict[str, Any]:
    try:
        return json.loads(mem.meta) if mem.meta else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def add_instinct(
    project_root: Path,
    trigger: str,
    action: str,
    scope: str = "project",
    project: str | None = None,
) -> dict[str, Any]:
    """Record an instinct. Identical trigger+action dedups to the same id —
    use :func:`reinforce` to strengthen it."""
    if not trigger.strip() or not action.strip():
        raise ValueError("instinct requires non-empty trigger and action")
    store = _store(project_root, scope)
    mem = store.add(
        _KIND,
        f"when {trigger.strip()} -> {action.strip()}",
        source="instinct",
        meta={
            "schema": SCHEMA,
            "trigger": trigger.strip(),
            "action": action.strip(),
            "confidence": _BASE_CONF,
            "hits": 1,
            "scope": scope,
            "projects": [project or project_root.name or "project"],
        },
        bank=_BANK,
    )
    return {"id": mem.id, "scope": scope, **_meta(mem)}


def reinforce(
    project_root: Path,
    instinct_id: str,
    scope: str = "project",
    project: str | None = None,
) -> dict[str, Any]:
    """Bump an instinct's hits/confidence; auto-promotes to ``user`` scope
    once the same instinct is observed in >=2 projects."""
    store = _store(project_root, scope)
    mem = store.get(instinct_id)
    if mem is None:
        raise KeyError(f"instinct {instinct_id} not found in {scope} scope")
    meta = _meta(mem)
    meta["hits"] = int(meta.get("hits", 1)) + 1
    meta["confidence"] = round(
        min(_BASE_CONF + _STEP * (meta["hits"] - 1), _MAX_CONF), 3
    )
    projects = list(meta.get("projects", []))
    pname = project or project_root.name or "project"
    if pname not in projects:
        projects.append(pname)
    meta["projects"] = projects
    store.update_meta(instinct_id, meta)

    promoted = None
    if scope == "project" and len(projects) >= _PROMOTE_PROJECTS:
        promoted = _promote_to_user(project_root, mem, meta)
        store.update_meta(instinct_id, {"promoted_to": "user"})
    return {"id": instinct_id, "scope": scope, "promoted": promoted is not None, **meta}


def _promote_to_user(project_root: Path, mem: Any, meta: dict[str, Any]) -> dict[str, Any]:
    """Copy a project instinct into the user vault (cross-project promotion)."""
    user = _store(project_root, "user")
    promoted_meta = dict(meta, scope="user", promoted_from=project_root.name)
    new_mem = user.add(
        _KIND, mem.content, source="instinct", meta=promoted_meta, bank=_BANK
    )
    return {"id": new_mem.id, "scope": "user"}


def list_instincts(
    project_root: Path,
    scope: str = "project",
    min_confidence: float = 0.0,
) -> list[dict[str, Any]]:
    """List instincts in a scope, strongest first."""
    store = _store(project_root, scope)
    out: list[dict[str, Any]] = []
    for mem in store.list_all(kind=_KIND, bank=_BANK):
        meta = _meta(mem)
        if float(meta.get("confidence", 0.0)) < min_confidence:
            continue
        out.append({"id": mem.id, "content": mem.content, "scope": scope, **meta})
    out.sort(key=lambda i: float(i.get("confidence", 0.0)), reverse=True)
    return out
