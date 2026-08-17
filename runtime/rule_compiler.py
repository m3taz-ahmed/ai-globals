#!/usr/bin/env python3
"""Markdown rule compiler for aiZee.

Re-implements the AI-RULES rule compiler pattern: parse project-authored
rule/skill markdown files into a normalized Rule IR that agents, validators,
and audit flows can consume.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from runtime.rule_frontmatter import parse_frontmatter

_FILE_TAG_RE = re.compile(r"^\[(?:FILE|SKILL|WORKFLOW|SAGA)\]\s*(.+)$", re.MULTILINE)
_OBJ_TAG_RE = re.compile(r"^\[OBJ\]\s*(.+)$", re.MULTILINE)
_RULES_TAG_RE = re.compile(r"^\[RULES\]\s*$", re.MULTILINE)
_STOP_TAG_RE = re.compile(r"^\[(?:FILE|OBJ|RULES)\]", re.MULTILINE)
_ENUM_RE = re.compile(r"^(\d+)\.\s*")
_BULLET_RE = re.compile(r"^[-*]\s*")
_CODE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*-\d+$")
_BRACKET_SPLIT_RE = re.compile(r"(\[[A-Za-z0-9_-]+\])")


@dataclass
class RuleEntry:
    """A single rule extracted from a markdown file."""

    index: int
    kind: str
    code: str | None
    text: str


@dataclass
class RuleIR:
    """Normalized intermediate representation for a rule/skill file."""

    source: Path | str
    file: str
    obj: str
    frontmatter: dict[str, Any]
    rules: list[RuleEntry]


def _code_prefix(code: str) -> str:
    """Return the category prefix of a code such as ``BEH-01`` -> ``BEH``."""
    return code.rsplit("-", 1)[0]


def _extract_tag(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _split_rules_section(body: str) -> tuple[str, str]:
    """Split body into the tag prefix (before [RULES]) and the rules section."""
    match = _RULES_TAG_RE.search(body)
    if not match:
        return body, ""
    return body[: match.start()], body[match.end() :]


def _parse_rules(section: str) -> list[RuleEntry]:
    """Parse the [RULES] section into RuleEntry objects."""
    entries: list[RuleEntry] = []
    current_group: str | None = None
    sequence = 1

    for raw in section.splitlines():
        line = raw.strip()
        if not line:
            continue

        if _STOP_TAG_RE.match(line):
            break

        if re.fullmatch(r"\[([A-Za-z0-9_-]+)\]", line):
            current_group = line[1:-1]
            continue

        index = 0
        enum_match = _ENUM_RE.match(line)
        if enum_match:
            index = int(enum_match.group(1))
            line = line[enum_match.end() :]
        else:
            bullet_match = _BULLET_RE.match(line)
            if bullet_match:
                line = line[bullet_match.end() :]

        if not line.startswith("["):
            continue

        parts = [p for p in _BRACKET_SPLIT_RE.split(line) if p]
        if not parts or not (parts[0].startswith("[") and parts[0].endswith("]")):
            continue

        token = parts[0][1:-1]
        rest = parts[1:]
        code: str | None = None
        kind: str | None = None

        if _CODE_RE.fullmatch(token):
            code = token
            kind = current_group if current_group is not None else _code_prefix(code)
        else:
            kind = token
            for i, seg in enumerate(rest):
                if seg.startswith("[") and seg.endswith("]"):
                    maybe_code = seg[1:-1]
                    if _CODE_RE.fullmatch(maybe_code):
                        code = maybe_code
                        rest = rest[:i] + rest[i + 1 :]
                        break

        if not kind:  # pragma: no cover
            continue

        text = "".join(rest).strip()
        if text.startswith(":"):
            text = text[1:].strip()
        if not text:
            continue

        if index == 0:
            index = sequence

        entries.append(RuleEntry(index=index, kind=kind, code=code, text=text))
        sequence += 1

    return entries


def compile_rule_file(path: Path) -> RuleIR:
    """Compile a single rule/skill markdown file into RuleIR."""
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    prefix, rules_section = _split_rules_section(body)

    return RuleIR(
        source=path,
        file=_extract_tag(_FILE_TAG_RE, prefix),
        obj=_extract_tag(_OBJ_TAG_RE, prefix),
        frontmatter=frontmatter.to_dict(),
        rules=_parse_rules(rules_section),
    )


def compile_rules(root: Path, globs: list[str] | None = None) -> list[RuleIR]:
    """Compile all rule/skill/workflow markdown files matching ``globs`` under ``root``."""
    if globs is None:
        globs = ["rules/*.md", "skills/**/*.md", "workflows/*.md"]

    paths: set[Path] = set()
    for pattern in globs:
        paths.update(root.glob(pattern))

    return [
        compile_rule_file(path)
        for path in sorted(paths, key=lambda p: str(p))
        if path.is_file()
    ]


def _rule_ir_to_dict(rule: RuleIR) -> dict[str, Any]:
    data: dict[str, Any] = asdict(rule)
    data["source"] = str(rule.source)
    return data


def to_json(rule: RuleIR | list[RuleIR]) -> str:
    """Serialize one or more RuleIR objects to a JSON string."""
    data = [_rule_ir_to_dict(r) for r in rule] if isinstance(rule, list) else _rule_ir_to_dict(rule)
    return json.dumps(data, indent=2, ensure_ascii=False)

