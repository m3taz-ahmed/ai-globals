"""Harness exporter — install aiZee skills into agent harnesses.

Adapted from Tencent/BrowserSkill's `bsk install-skill --harness X` —
a fixed table of target directories per harness; copies a skill's
SKILL.md (and sibling files) into the harness's skills folder.

Supported harnesses:
    cursor      ~/.cursor/skills/<name>/
    claude      ~/.claude/skills/<name>/
    codex       ~/.codex/skills/<name>/
    opencode    ~/.config/opencode/skills/<name>/
    project     ./.agents/skills/<name>/    (per-repo)
    path        arbitrary --dest directory
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SKILL_FILENAME = "SKILL.md"

# Harness name -> skills dir under the user's home.
_HARNESS_DIRS: dict[str, str] = {
    "cursor": ".cursor/skills",
    "claude": ".claude/skills",
    "codex": ".codex/skills",
    "opencode": ".config/opencode/skills",
}


@dataclass
class InstallResult:
    """Outcome of a single skill install."""

    skill: str
    harness: str
    dest: str = ""
    files: list[str] = field(default_factory=list)
    ok: bool = False
    error: str = ""
    overwritten: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill": self.skill,
            "harness": self.harness,
            "dest": self.dest,
            "files": self.files,
            "ok": self.ok,
            "error": self.error or None,
            "overwritten": self.overwritten,
        }


def harnesses() -> dict[str, str]:
    """Harness name -> resolved target directory."""
    home = Path.home()
    return {name: str(home / rel) for name, rel in _HARNESS_DIRS.items()}


def resolve_harness_dir(harness: str, dest: str = "") -> Path:
    """Resolve target directory for a harness name or explicit path."""
    harness = harness.strip().lower()
    if harness == "project":
        return Path.cwd() / ".agents" / "skills"
    if harness == "path":
        if not dest:
            raise ValueError("harness 'path' requires --dest <dir>")
        return Path(dest).expanduser()
    if harness in _HARNESS_DIRS:
        return Path.home() / _HARNESS_DIRS[harness]
    raise ValueError(
        f"unknown harness '{harness}' — supported: "
        + ", ".join(sorted([*_HARNESS_DIRS, "project", "path"]))
    )


def _find_skill_dir(skills_root: Path, name: str) -> Path:
    """Locate a skill source dir: directory form or flat `<name>.md`."""
    candidate = skills_root / name
    if candidate.is_dir() and (candidate / SKILL_FILENAME).exists():
        return candidate
    flat = skills_root / f"{name}.md"
    if flat.exists():
        return flat
    raise FileNotFoundError(f"skill '{name}' not found under {skills_root}")


def install_skill(
    skills_root: Path,
    name: str,
    harness: str,
    dest: str = "",
    force: bool = False,
) -> InstallResult:
    """Install one skill into a harness directory.

    Directory skills copy recursively; flat `<name>.md` skills copy the
    single file as `<dest>/<name>.md`. Returns an InstallResult; never
    raises for missing skills (FileNotFoundError -> result.error).
    """
    result = InstallResult(skill=name, harness=harness)
    try:
        src = _find_skill_dir(Path(skills_root), name)
        target_base = resolve_harness_dir(harness, dest)
        if src.is_dir():
            target = target_base / name
            if target.exists():
                if not force:
                    result.error = f"'{target}' exists — pass --force to overwrite"
                    result.dest = str(target)
                    return result
                shutil.rmtree(target)
                result.overwritten = True
            shutil.copytree(src, target)
            result.files = [
                str(p.relative_to(target))
                for p in sorted(target.rglob("*"))
                if p.is_file()
            ]
        else:
            target_base.mkdir(parents=True, exist_ok=True)
            target = target_base / src.name
            if target.exists() and not force:
                result.error = f"'{target}' exists — pass --force to overwrite"
                result.dest = str(target)
                return result
            result.overwritten = target.exists()
            shutil.copy2(src, target)
            result.files = [src.name]
        result.dest = str(target)
        result.ok = True
        return result
    except (FileNotFoundError, ValueError, OSError) as exc:
        result.error = str(exc)
        return result


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(
        prog="aizee-install-skill",
        description="Install aiZee skills into agent harnesses",
    )
    p.add_argument(
        "name", nargs="?", help="skill name (dir or flat .md under skills/)"
    )
    p.add_argument("--all", dest="all_skills", action="store_true",
                   help="install every skill under --skills-root")
    p.add_argument(
        "--harness",
        default="project",
        help="cursor|claude|codex|opencode|project|path",
    )
    p.add_argument("--dest", default="", help="target dir when --harness path")
    p.add_argument("--force", action="store_true", help="overwrite existing")
    p.add_argument("--skills-root", default="skills")
    p.add_argument("--list", action="store_true", help="list harnesses and exit")
    args = p.parse_args(argv)

    if args.list:
        print(json.dumps(harnesses(), indent=2))
        return 0

    r = install_skill(
        Path(args.skills_root), args.name, args.harness, args.dest, args.force
    )
    print(json.dumps(r.to_dict(), indent=2))
    return 0 if r.ok else 1


if __name__ == "__main__":
    sys.exit(main())
