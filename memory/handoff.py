"""Cross-harness memory handoffs (``aizee.handoff.v1``).

Portable Markdown documents that let one agent/harness hand work to another:
the writer stamps a handoff doc into the scoped memory vault; the target
harness reads it via ``memory search`` / ``handoffs``. Two scopes:

- ``project`` — ``<repo>/brain/handoffs/`` — local-only, protected by a
  fail-closed ``.gitignore`` guard (the vault never silently commits).
- ``user``    — ``~/.aizee/handoffs/`` — follows the operator across repos.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "aizee.handoff.v1"
_VAULT_DIRNAME = "brain"  # project-scope vault dir (gitignored)
_GUARD_LINE = "brain/"
_HARNESS_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")


def scope_root(scope: str, project_root: Path) -> Path:
    """Resolve the root for a memory scope (project vault vs user vault)."""
    if scope == "user":
        return Path.home() / ".aizee"
    return project_root


def ensure_vault_guard(project_root: Path) -> None:
    """Fail-closed: project vault must be git-ignored before any write.

    - Missing ``.gitignore`` → create it with the guard line.
    - Present without ``brain/`` → append the guard line.
    - Present with an explicit ``!brain/`` negation → refuse (the operator
      deliberately un-ignored the vault; writing would risk committing it).
    """
    gi = project_root / ".gitignore"
    if not gi.exists():
        gi.write_text(f"{_GUARD_LINE}\n", encoding="utf-8")
        return
    lines = gi.read_text(encoding="utf-8").splitlines()
    if f"!{_GUARD_LINE}" in lines or "!brain" in lines:
        raise ValueError(
            ".gitignore explicitly un-ignores brain/ — refusing to write "
            "project handoffs (fail-closed vault guard)."
        )
    if _GUARD_LINE not in lines and "brain" not in lines:
        with gi.open("a", encoding="utf-8") as fh:
            fh.write(f"{_GUARD_LINE}\n")


def new_handoff_id(from_harness: str, to_harness: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}-{_slug(from_harness)}-to-{_slug(to_harness)}"


def _slug(name: str) -> str:
    if not _HARNESS_RE.fullmatch(name):
        raise ValueError(f"Invalid harness name {name!r}: use [A-Za-z0-9_.-]")
    return name


def render_handoff(
    handoff_id: str,
    title: str,
    body: str,
    from_harness: str,
    to_harness: str,
    project: str,
) -> str:
    """Render an ``aizee.handoff.v1`` Markdown document."""
    return (
        "---\n"
        f"schema: {SCHEMA}\n"
        f"id: {handoff_id}\n"
        f"title: {title}\n"
        f"from: {from_harness}\n"
        f"to: {to_harness}\n"
        f"project: {project}\n"
        f"created: {datetime.now(timezone.utc).isoformat()}\n"
        "---\n\n"
        f"# Handoff: {title}\n\n{body.strip()}\n"
    )


def write_handoff(
    project_root: Path,
    from_harness: str,
    to_harness: str,
    title: str,
    body: str,
    scope: str = "project",
) -> dict[str, Any]:
    """Write a handoff doc into the scoped vault + index it for search.

    Returns ``{"id", "path", "memory_id", "scope"}``.
    """
    root = scope_root(scope, project_root)
    if scope == "project":
        ensure_vault_guard(root)
    hid = new_handoff_id(from_harness, to_harness)
    text = render_handoff(
        hid, title, body, from_harness, to_harness, root.name or "project"
    )
    handoffs_dir = root / _VAULT_DIRNAME / "handoffs"
    handoffs_dir.mkdir(parents=True, exist_ok=True)
    path = handoffs_dir / f"{hid}.md"
    path.write_text(text, encoding="utf-8")

    from memory.store import MemoryStore

    store = MemoryStore(root)
    mem = store.add(
        "handoff",
        f"{title}\n\n{body.strip()}",
        source=f"{from_harness}-to-{to_harness}",
        meta={"handoff_id": hid, "schema": SCHEMA, "scope": scope},
        bank="handoffs",
    )
    return {"id": hid, "path": str(path), "memory_id": mem.id, "scope": scope}


def list_handoffs(project_root: Path, scope: str = "project") -> list[dict[str, Any]]:
    """List handoff docs in a scope's vault (newest first)."""
    root = scope_root(scope, project_root)
    d = root / _VAULT_DIRNAME / "handoffs"
    if not d.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(d.glob("*.md"), reverse=True):
        try:
            head = p.read_text(encoding="utf-8")[:2048]
        except OSError:
            continue
        title = ""
        for line in head.splitlines():
            if line.startswith("title: "):
                title = line[7:].strip()
                break
        out.append({"id": p.stem, "title": title, "path": str(p)})
    return out
