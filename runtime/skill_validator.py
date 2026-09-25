#!/usr/bin/env python3
"""Skill contract validator — ``aizee skill validate``.

Checks every skill (``skills/<name>.md`` flat and ``skills/<name>/SKILL.md``
directory forms) against the SKILL.md contract, adapted from
``validate-skills.sh`` in the social-media-skills pattern and the
agent-skills ``docs/skill-anatomy.md`` spec:

- folder/file name is kebab-case
- SKILL.md exists and starts with YAML frontmatter
- frontmatter parses to a dict with non-empty ``name`` (== folder/stem)
- ``description`` is present, <= 1024 chars, and contains activation language
- file size is bounded
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
_ACTIVATION_RE = re.compile(
    r"use when|trigger|activates|invoke|on demand|when the user", re.IGNORECASE
)

MAX_DESCRIPTION_LEN = 1024
MAX_SKILL_BYTES = 200_000
_EXCLUDED_STEMS = {"README", "EVAL"}


@dataclass
class SkillFinding:
    """One contract finding for a skill."""

    skill: str
    level: str  # "error" | "warn"
    rule: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "skill": self.skill,
            "level": self.level,
            "rule": self.rule,
            "message": self.message,
        }


@dataclass
class SkillReport:
    """Aggregate validation report."""

    skills_checked: int = 0
    findings: list[SkillFinding] = field(default_factory=list)

    @property
    def errors(self) -> list[SkillFinding]:
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self) -> list[SkillFinding]:
        return [f for f in self.findings if f.level == "warn"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "skills_checked": self.skills_checked,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "findings": [f.to_dict() for f in self.findings],
        }


def _skill_files(skills_dir: Path) -> list[tuple[str, Path]]:
    """Enumerate (name, skill_md_path) for both skill layouts."""
    found: list[tuple[str, Path]] = []
    if not skills_dir.is_dir():
        return found
    for entry in sorted(skills_dir.iterdir()):
        if entry.is_file() and entry.suffix == ".md" and entry.stem not in _EXCLUDED_STEMS:
            found.append((entry.stem, entry))
        elif entry.is_dir() and (entry / "SKILL.md").is_file():
            found.append((entry.name, entry / "SKILL.md"))
    return found


def _frontmatter(text: str) -> dict[str, Any] | None:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _check_name(name: str, findings: list[SkillFinding]) -> None:
    if not _KEBAB_RE.match(name):
        findings.append(
            SkillFinding(name, "error", "NAME_KEBAB", f"'{name}' must be kebab-case")
        )


def _check_frontmatter(
    name: str, text: str, path: Path, findings: list[SkillFinding]
) -> None:
    meta = _frontmatter(text)
    if meta is None:
        findings.append(
            SkillFinding(name, "error", "FRONTMATTER", f"{path.name}: missing/invalid YAML frontmatter")
        )
        return
    fm_name = str(meta.get("name", "")).strip()
    if not fm_name:
        findings.append(SkillFinding(name, "error", "NAME_MISSING", "frontmatter has no 'name'"))
    elif fm_name != name:
        findings.append(
            SkillFinding(
                name, "error", "NAME_MISMATCH",
                f"frontmatter name '{fm_name}' != skill id '{name}'",
            )
        )
    description = str(meta.get("description", "")).strip()
    if not description:
        findings.append(
            SkillFinding(name, "error", "DESCRIPTION_MISSING", "frontmatter has no 'description'")
        )
        return
    if len(description) > MAX_DESCRIPTION_LEN:
        findings.append(
            SkillFinding(
                name, "error", "DESCRIPTION_LEN",
                f"description is {len(description)} chars (max {MAX_DESCRIPTION_LEN})",
            )
        )
    if not _ACTIVATION_RE.search(description) and not _has_activation_evidence(
        meta, text
    ):
        findings.append(
            SkillFinding(
                name, "warn", "DESCRIPTION_VAGUE",
                "description lacks activation language ('use when'/'trigger') and "
                "no frontmatter triggers/[TRIGGER] marker — agents route on it, "
                "tell them when to fire",
            )
        )


def _has_activation_evidence(meta: dict[str, Any], text: str) -> bool:
    """aiZee convention: frontmatter ``triggers:`` or body markers also signal activation."""
    if meta.get("triggers"):
        return True
    return "[TRIGGER]" in text or "[SKILL]" in text or "[OBJ]" in text


def validate_skills(skills_dir: Path) -> SkillReport:
    """Validate all skills under ``skills_dir``. Returns a report; never raises."""
    report = SkillReport()
    for name, skill_md in _skill_files(skills_dir):
        report.skills_checked += 1
        _check_name(name, report.findings)
        try:
            size = skill_md.stat().st_size
            text = skill_md.read_text(encoding="utf-8")
        except OSError as exc:
            report.findings.append(
                SkillFinding(name, "error", "READ_FAIL", f"cannot read {skill_md}: {exc}")
            )
            continue
        if size > MAX_SKILL_BYTES:
            report.findings.append(
                SkillFinding(
                    name, "warn", "FILE_SIZE", f"{size} bytes > {MAX_SKILL_BYTES} budget"
                )
            )
        _check_frontmatter(name, text, skill_md, report.findings)
    return report


__all__ = [
    "MAX_DESCRIPTION_LEN",
    "MAX_SKILL_BYTES",
    "SkillFinding",
    "SkillReport",
    "validate_skills",
]
