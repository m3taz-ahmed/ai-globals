#!/usr/bin/env python3
"""Memory.md auto-compaction (P2.4).

Memory.md is append-mostly and grows unboundedly; its own charter caps it
at 500 lines. The compactor:

- preserves the preamble (everything before the first ``[UPDATED]``
  block: ``[FILE]/[OBJ]/[RULES]/...`` headers),
- keeps the newest ``[UPDATED]`` sections until the line budget is hit,
- rescues any bullet marked ``[PINNED]`` from dropped sections into a
  pinned block under the preamble,
- appends dropped sections to ``memory/archive/Memory-YYYYMM.md`` so
  nothing is lost,
- rewrites Memory.md atomically (tmp + os.replace).

Dry-run is the default; compaction only writes with ``apply=True``.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_UPDATED_RE = re.compile(r"^\[UPDATED\]\s*(\d{4}-\d{2}-\d{2})")
_PINNED_RE = re.compile(r"\[PINNED\]|<!--\s*keep\s*-->", re.IGNORECASE)

MAX_LINES = 500
MIN_KEEP_SECTIONS = 1


@dataclass
class CompactResult:
    ok: bool
    dry_run: bool
    needed: bool
    before_lines: int = 0
    after_lines: int = 0
    before_bytes: int = 0
    after_bytes: int = 0
    kept_sections: int = 0
    archived_sections: int = 0
    pinned_rescued: int = 0
    archive_path: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "dry_run": self.dry_run,
            "needed": self.needed,
            "before_lines": self.before_lines,
            "after_lines": self.after_lines,
            "before_bytes": self.before_bytes,
            "after_bytes": self.after_bytes,
            "kept_sections": self.kept_sections,
            "archived_sections": self.archived_sections,
            "pinned_rescued": self.pinned_rescued,
            "archive_path": self.archive_path,
        }


@dataclass
class _Section:
    header: str  # the "[UPDATED] date" line
    body: list[str] = field(default_factory=list)

    @property
    def lines(self) -> int:
        return 1 + len(self.body)

    def render(self) -> list[str]:
        return [self.header, *self.body]


def _split(path: Path) -> tuple[list[str], list[_Section]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    preamble: list[str] = []
    sections: list[_Section] = []
    current: _Section | None = None
    for line in lines:
        if _UPDATED_RE.match(line):
            current = _Section(header=line)
            sections.append(current)
        elif current is None:
            preamble.append(line)
        else:
            current.body.append(line)
    return preamble, sections


def _pinned_lines(sections: list[_Section]) -> list[str]:
    pinned: list[str] = []
    for s in sections:
        for line in s.body:
            if _PINNED_RE.search(line):
                pinned.append(line)
    return pinned


def compact_memory(
    path: Path,
    max_lines: int = MAX_LINES,
    dry_run: bool = True,
    archive_dir: Path | None = None,
) -> CompactResult:
    """Compact ``path`` (Memory.md) to fit ``max_lines``; archive the rest."""
    if not path.exists():
        return CompactResult(ok=False, dry_run=dry_run, needed=False, before_bytes=0)
    preamble, sections = _split(path)
    before_lines = sum(s.lines for s in sections) + len(preamble)
    before_bytes = path.stat().st_size

    if not sections:
        # No [UPDATED] sections — refuse to guess a structure.
        return CompactResult(
            ok=True, dry_run=dry_run, needed=False,
            before_lines=before_lines, after_lines=before_lines,
            before_bytes=before_bytes, after_bytes=before_bytes,
        )

    if before_lines <= max_lines:
        return CompactResult(
            ok=True, dry_run=dry_run, needed=False,
            before_lines=before_lines, after_lines=before_lines,
            before_bytes=before_bytes, after_bytes=before_bytes,
            kept_sections=len(sections),
        )

    budget = max_lines - len(preamble)
    kept: list[_Section] = []
    dropped: list[_Section] = []
    used = 0
    for i, s in enumerate(sections):
        # Sections appear newest-first in practice; always keep at least
        # MIN_KEEP_SECTIONS so the file never loses its latest notes.
        if i < MIN_KEEP_SECTIONS or used + s.lines <= budget:
            kept.append(s)
            used += s.lines
        else:
            dropped.append(s)

    pinned = _pinned_lines(dropped)
    pinned_block: list[str] = []
    if pinned:
        pinned_block = ["", f"[PINNED] rescued {len(pinned)} entries", *pinned]

    new_lines = preamble + pinned_block
    for s in kept:
        new_lines.extend(s.render())
    new_text = "\n".join(new_lines).rstrip("\n") + "\n"

    stamp = datetime.now(timezone.utc).strftime("%Y%m")
    archive_path = ""
    if not dry_run:
        if dropped:
            adir = archive_dir or path.parent / "memory" / "archive"
            adir.mkdir(parents=True, exist_ok=True)
            archive = adir / f"Memory-{stamp}.md"
            with archive.open("a", encoding="utf-8", newline="\n") as fh:
                fh.write(f"\n<!-- compacted {datetime.now(timezone.utc).isoformat()} -->\n")
                for s in dropped:
                    fh.write("\n".join(s.render()) + "\n")
            archive_path = str(archive)
        _atomic_write(path, new_text)

    return CompactResult(
        ok=True,
        dry_run=dry_run,
        needed=True,
        before_lines=before_lines,
        after_lines=len(new_lines),
        before_bytes=before_bytes,
        after_bytes=len(new_text.encode("utf-8")),
        kept_sections=len(kept),
        archived_sections=len(dropped),
        pinned_rescued=len(pinned),
        archive_path=archive_path,
    )


def _atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        with __import__("contextlib").suppress(OSError):
            os.remove(tmp)
        raise


__all__ = ["MAX_LINES", "CompactResult", "compact_memory"]
