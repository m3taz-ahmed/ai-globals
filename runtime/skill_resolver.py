"""Resolve skill names to on-disk skill files."""

from __future__ import annotations

from pathlib import Path

import config


class SkillResolver:
    """Discover and validate skill files under the OS root.

    Supports both flat (`skills/{name}.md`) and directory
    (`skills/{name}/SKILL.md`) skill layouts so that lord skills, persona
    skills, and subskills can coexist.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or config.discover_root()
        self.skills_dir = self.root / "skills"

    def resolve(self, name: str) -> Path | None:
        """Return the absolute path for a skill name, or None if not found."""
        if not name or ".." in name or "/" in name or "\\" in name:
            return None
        candidates = [
            self.skills_dir / f"{name}.md",
            self.skills_dir / name / "SKILL.md",
        ]
        for candidate in candidates:
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
        """Return all valid skill names found in `skills/`."""
        names: set[str] = set()
        if not self.skills_dir.is_dir():
            return []
        for path in self.skills_dir.iterdir():
            if path.is_file() and path.suffix == ".md":
                names.add(path.stem)
            elif path.is_dir() and (path / "SKILL.md").is_file():
                names.add(path.name)
        return sorted(names)
