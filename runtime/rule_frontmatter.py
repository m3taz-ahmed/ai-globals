"""YAML frontmatter parsing and context matching for rules and skills."""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)


@dataclass
class RuleFrontmatter:
    """Conditional loading metadata for a rule or skill."""

    paths: list[str] | None = None
    personas: list[str] | None = None
    stack: list[str] | None = None
    always: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict for serialization."""
        return {
            "paths": self.paths,
            "personas": self.personas,
            "stack": self.stack,
            "always": self.always,
        }


def _as_str_list(value: Any) -> list[str] | None:
    """Normalize a YAML value to a list of strings or None."""
    if value is None:
        return None
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


@functools.lru_cache(maxsize=256)
def parse_frontmatter(text: str) -> tuple[RuleFrontmatter, str]:
    """Parse YAML frontmatter from the top of a markdown file.

    Returns the parsed frontmatter and the remaining body.
    """
    if not text:
        return RuleFrontmatter(), ""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return RuleFrontmatter(), text
    raw_yaml = match.group(1)
    body = text[match.end() :]
    try:
        data = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    return RuleFrontmatter(
        paths=_as_str_list(data.get("paths")),
        personas=_as_str_list(data.get("personas")),
        stack=_as_str_list(data.get("stack")),
        always=bool(data.get("always", False)),
    ), body


def _match_path(pattern: str, path: str) -> bool:
    """Match a single glob pattern against a file path using pathlib."""
    normalized = PurePosixPath(path.replace("\\", "/"))
    if "**" in pattern:
        full_match = getattr(PurePosixPath, "full_match", None)
        if full_match is not None:
            return bool(full_match(normalized, pattern))
    return bool(normalized.match(pattern))


def _match_paths(patterns: list[str], paths: list[Any]) -> bool:
    """Return True if any path matches any glob pattern."""
    for path in paths:
        path_str = str(path).replace("\\", "/")
        for pattern in patterns:
            if _match_path(pattern, path_str):
                return True
    return False


def _match_personas(patterns: list[str], context: dict[str, Any]) -> bool:
    """Return True if the primary or any selected persona matches."""
    selected: set[str] = set()
    primary = context.get("persona")
    if isinstance(primary, str):
        selected.add(primary.lower())
    personas = context.get("personas")
    if isinstance(personas, str):
        personas = [personas]
    if isinstance(personas, list):
        for persona in personas:
            if isinstance(persona, str):
                selected.add(persona.lower())
    patterns_lower = {p.lower() for p in patterns}
    return bool(selected & patterns_lower)


def _match_stack(patterns: list[str], stack: list[Any]) -> bool:
    """Return True if any stack package matches a pattern."""
    patterns_lower = {p.lower().strip() for p in patterns}
    for raw in stack:
        raw_str = str(raw).strip().lower()
        if raw_str in patterns_lower:
            return True
        parts = re.split(r"[/\\@\s-]+", raw_str)
        for part in parts:
            if part in patterns_lower:
                return True
    return False


def matches_context(frontmatter: RuleFrontmatter, context: dict[str, Any] | None = None) -> bool:
    """Evaluate a frontmatter against a runtime context.

    A rule matches if ``always`` is True, if no conditions are set, or if any
    condition group (paths, personas, stack) matches.
    """
    if frontmatter.always:
        return True

    ctx = context or {}
    conditions: list[bool] = []
    if frontmatter.paths:
        paths = ctx.get("paths", [])
        if isinstance(paths, str):
            paths = [paths]
        conditions.append(_match_paths(frontmatter.paths, paths))
    if frontmatter.personas:
        conditions.append(_match_personas(frontmatter.personas, ctx))
    if frontmatter.stack:
        stack = ctx.get("stack", [])
        if isinstance(stack, str):
            stack = [stack]
        conditions.append(_match_stack(frontmatter.stack, stack))
    if not conditions:
        return True
    return any(conditions)
