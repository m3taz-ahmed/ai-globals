"""Resolve skill names to on-disk skill files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import config
from runtime.rule_frontmatter import RuleFrontmatter, matches_context, parse_frontmatter


class SkillResolver:
    """Discover and validate skill files under the OS root.

    Supports both flat (`skills/{name}.md`) and directory
    (`skills/{name}/SKILL.md`) skill layouts so that lord skills, persona
    skills, and subskills can coexist.
    """

    def __init__(self, root: Path | None = None, project_root: Path | None = None) -> None:
        self.root = root or config.discover_root()
        self.project_root = project_root
        self.skills_dir = self.root / "skills"
        self.project_skills_dir = self.project_root / ".ai" / "skills" if self.project_root else None

    def _candidate_paths(self, name: str) -> list[Path]:
        """OS and project-level skill candidates."""
        if not name or ".." in name or "/" in name or "\\" in name:
            return []
        candidates: list[Path] = []
        if self.project_skills_dir and self.project_skills_dir.is_dir():
            candidates.extend([
                self.project_skills_dir / f"{name}.md",
                self.project_skills_dir / name / "SKILL.md",
            ])
        candidates.extend([
            self.skills_dir / f"{name}.md",
            self.skills_dir / name / "SKILL.md",
        ])
        return candidates

    def resolve(self, name: str) -> Path | None:
        """Return the absolute path for a skill name, or None if not found."""
        for candidate in self._candidate_paths(name):
            if candidate.is_file():
                return candidate
        return None

    def exists(self, name: str) -> bool:
        """True if the named skill has a file on disk."""
        return self.resolve(name) is not None

    def load(self, name: str) -> str | None:
        """Read a skill file's text, or None if missing."""
        path = self.resolve(name)
        if path is None:
            return None
        return path.read_text(encoding="utf-8")

    def list_skills(self) -> list[str]:
        """Return all valid skill names found in OS and project `skills/`."""
        _excluded = {"README", "EVAL"}
        names: set[str] = set()
        for directory in (self.project_skills_dir, self.skills_dir):
            if directory is None or not directory.is_dir():
                continue
            for path in directory.iterdir():
                if path.is_file() and path.suffix == ".md":
                    if path.stem in _excluded:
                        continue
                    names.add(path.stem)
                elif path.is_dir() and (path / "SKILL.md").is_file():
                    names.add(path.name)
        return sorted(names)

    def _load_skill(self, name: str) -> tuple[Path, RuleFrontmatter, str] | None:
        """Load the first candidate skill file and parse its frontmatter."""
        for candidate in self._candidate_paths(name):
            if not candidate.is_file():
                continue
            text = candidate.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(text)
            return candidate, frontmatter, body
        return None

    def resolve_with_frontmatter(
        self, name: str, context: dict[str, Any] | None = None
    ) -> Path | None:
        """Resolve a skill only if its frontmatter matches the runtime context."""
        loaded = self._load_skill(name)
        if loaded is None:
            return None
        path, frontmatter, _ = loaded
        return path if matches_context(frontmatter, context or {}) else None

    def load_with_frontmatter(
        self, name: str, context: dict[str, Any] | None = None
    ) -> str | None:
        """Return a skill's body only if its frontmatter matches the context."""
        loaded = self._load_skill(name)
        if loaded is None:
            return None
        _, frontmatter, body = loaded
        return body if matches_context(frontmatter, context or {}) else None

    def list_active_skills(self, context: dict[str, Any] | None = None) -> list[str]:
        """Return all skill names whose frontmatter matches the runtime context."""
        active_context = context or {}
        return sorted(
            name for name in self.list_skills() if self.resolve_with_frontmatter(name, active_context)
        )
