#!/usr/bin/env python3
"""Docs <-> reality sync for aiZee.

Single source of truth is the filesystem. This script verifies (and by
default repairs) documentation drift:

1. Counts runtime modules, skills, numbered workflows, tech-stack refs.
2. Rewrites stale counts in ``AGENTS.md`` and ``spec.md``.
3. Regenerates the ``workflows/README.md`` numbered-workflow routing table
   from each workflow file's own ``[TRIGGER]``/``trigger`` + ``[OBJ]``
   metadata, guaranteeing every workflow is listed exactly once.

Usage::

    python scripts/sync_docs.py            # repair docs in place
    python scripts/sync_docs.py --check    # CI mode: exit 1 if out of sync
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------


def count_runtime_modules(root: Path) -> int:
    """Top-level governance modules in runtime/ (excluding __init__.py)."""
    return len([p for p in (root / "runtime").glob("*.py") if p.name != "__init__.py"])


def count_skills(root: Path) -> int:
    """Skill units: directories with SKILL.md + flat <name>.md files."""
    skills = root / "skills"
    if not skills.exists():
        return 0
    dirs = [p for p in skills.iterdir() if p.is_dir() and (p / "SKILL.md").exists()]
    flats = [p for p in skills.glob("*.md") if p.name not in ("README.md", "EVAL.md")]
    return len(dirs) + len(flats)


def numbered_workflows(root: Path) -> list[Path]:
    wf = root / "workflows"
    if not wf.exists():
        return []
    return sorted(p for p in wf.glob("*.md") if re.match(r"^\d{2}-", p.name))


def count_workflows_md(root: Path) -> int:
    return len(list((root / "workflows").glob("*.md")))


def count_tech_stack(root: Path) -> int:
    return len(list((root / "tech-stack").glob("*.md")))


def gather_counts(root: Path) -> dict[str, int]:
    return {
        "runtime": count_runtime_modules(root),
        "skills": count_skills(root),
        "numbered": len(numbered_workflows(root)),
        "workflows_total": count_workflows_md(root),
        "stack": count_tech_stack(root),
    }


# ---------------------------------------------------------------------------
# Workflow metadata extraction (both legacy and frontmatter formats)
# ---------------------------------------------------------------------------

_MAX_PURPOSE = 90
_MAX_TRIGGER = 46


def _sanitize_cell(value: str, max_len: int) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = value.replace("|", "/")
    if len(value) > max_len:
        value = value[: max_len - 1].rstrip() + "…"
    return value


def describe_workflow(path: Path) -> tuple[str, str]:
    """Return (trigger, purpose) from a workflow file."""
    text = path.read_text(encoding="utf-8")

    def tagged(tag: str) -> str:
        m = re.search(rf"^\[{tag}\]\s*(.+)$", text, re.MULTILINE)
        return m.group(1).strip() if m else ""

    def yaml(field: str) -> str:
        m = re.search(rf"^{field}:\s*(.+)$", text, re.MULTILINE)
        return m.group(1).strip() if m else ""

    trigger = yaml("trigger") or tagged("TRIGGER")
    purpose = tagged("OBJ")
    if not purpose:
        # First plain line after the H1 title (skip quotes/headings/tables).
        parts = re.split(r"^# .+?$", text, maxsplit=1, flags=re.MULTILINE)
        if len(parts) > 1:
            for line in parts[1].splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith(("#", ">", "|", "-")):
                    continue
                purpose = stripped
                break
    # Primary trigger = first comma-separated item.
    primary = trigger.split(",")[0].strip() if trigger else path.stem
    return _sanitize_cell(primary, _MAX_TRIGGER), _sanitize_cell(purpose, _MAX_PURPOSE)


# ---------------------------------------------------------------------------
# Repairs
# ---------------------------------------------------------------------------

# (pattern, template) applied to AGENTS.md and spec.md.
_COUNT_SUBS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d+ governance modules\b"), "{runtime} governance modules"),
    (re.compile(r"\b\d+ persona \+ lord skills?(?: files)?\b"), "{skills} persona + lord skills"),
    (
        re.compile(r"\b\d+ trigger-based(?: execution)? protocols\b"),
        "{numbered} trigger-based execution protocols",
    ),
    (re.compile(r"\b\d+ version-locked stack references\b"), "{stack} version-locked stack references"),
]

_DOC_FILES = ("AGENTS.md", "spec.md")


def _substitute_counts(text: str, counts: dict[str, int]) -> str:
    for pattern, template in _COUNT_SUBS:
        def _repl(_m: re.Match[str], t: str = template) -> str:
            return t.format(**counts)

        text = pattern.sub(_repl, text)
    return text


def build_numbered_section(counts: dict[str, int], files: list[Path]) -> str:
    """Render the full 'Numbered Workflows' README section."""
    last = files[-1].name[:2] if files else "00"
    lines = [
        "## Numbered Workflows (Trigger-Based)",
        "",
        f"This directory contains **{counts['workflows_total']}** `.md` files: "
        f"**{counts['numbered']}** numbered trigger-based workflows "
        f"(`00`-`{last}`) plus standards protocols and reference files.",
        "",
        "| Trigger / Task Type | Workflow File | When to Use |",
        "|---|---|---|",
    ]
    for f in files:
        trigger, purpose = describe_workflow(f)
        lines.append(f"| {trigger} | `{f.name}` | {purpose} |")
    lines.append("")
    return "\n".join(lines)


_SECTION_START = "## Numbered Workflows (Trigger-Based)"
_SECTION_END = "## Standards & Reference Files"


def rebuild_readme(root: Path, counts: dict[str, int]) -> str:
    """Return the repaired workflows/README.md content."""
    readme = root / "workflows" / "README.md"
    text = readme.read_text(encoding="utf-8")
    new_section = build_numbered_section(counts, numbered_workflows(root))
    pattern = re.compile(
        re.escape(_SECTION_START) + r".*?(?=" + re.escape(_SECTION_END) + ")", re.DOTALL
    )
    if not pattern.search(text):
        return text
    return pattern.sub(new_section + "\n", text)


def sync(root: Path) -> dict[str, bool]:
    """Apply all repairs. Returns per-file changed flags."""
    counts = gather_counts(root)
    changed: dict[str, bool] = {}

    for name in _DOC_FILES:
        doc = root / name
        if not doc.exists():
            continue
        original = doc.read_text(encoding="utf-8")
        updated = _substitute_counts(original, counts)
        changed[name] = updated != original
        if changed[name]:
            doc.write_text(updated, encoding="utf-8", newline="\n")

    readme = root / "workflows" / "README.md"
    original = readme.read_text(encoding="utf-8")
    updated = rebuild_readme(root, counts)
    changed["workflows/README.md"] = updated != original
    if changed["workflows/README.md"]:
        readme.write_text(updated, encoding="utf-8", newline="\n")
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync-docs", description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="aiZee root")
    parser.add_argument(
        "--check", action="store_true", help="Exit 1 if docs are out of sync (no writes)"
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    counts = gather_counts(root)

    if args.check:
        drifted: list[str] = []
        for name in (*_DOC_FILES, "workflows" + "/" + "README.md"):
            doc = root / name
            if not doc.exists():
                continue
            original = doc.read_text(encoding="utf-8")
            if name in _DOC_FILES:
                updated = _substitute_counts(original, counts)
            else:
                updated = rebuild_readme(root, counts)
            if updated != original:
                drifted.append(name)
        if drifted:
            print("OUT OF SYNC: " + ", ".join(drifted))
            print("Run: python scripts/sync_docs.py")
            return 1
        print(f"In sync: runtime={counts['runtime']} skills={counts['skills']} "
              f"workflows={counts['numbered']} tech-stack={counts['stack']}")
        return 0

    changed = sync(root)
    touched = [name for name, did in changed.items() if did]
    for name in touched:
        print(f"updated {name}")
    if not touched:
        print("docs already in sync")
    print(f"counts: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
