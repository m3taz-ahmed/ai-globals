#!/usr/bin/env python3
# Sync agent config files across tools from AGENTS.md canonical source.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

ROOT = config.discover_root()
AGENTS = ROOT / "AGENTS.md"


def read_agents() -> str:
    if not AGENTS.exists():
        print("AGENTS.md missing")
        sys.exit(1)
    return AGENTS.read_text(encoding="utf-8")

def canonical_to_cursor_mdc(agents: str, description: str, globs: list, extra: str = "") -> str:
    globs_part = ", ".join(f'"{g}"' for g in globs) if globs else ""
    globs_s = f"[{globs_part}]" if globs else "[]"
    # strip YAML frontmatter from AGENTS.md
    body = agents.strip()
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            body = body[end + 4:].strip()
    return f"---\ndescription: {description}\nglobs: {globs_s}\nalwaysApply: true\n---\n\n{extra}{body}\n"

def canonical_to_claude(agents: str) -> str:
    return f"# AI Global OS — Claude Code Native\n\n{agents}\n"

def canonical_to_clinerules(agents: str) -> str:
    body = agents.strip()
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            body = body[end + 4:].strip()
    return f"# AI Global OS\n\n{body}\n"

def canonical_to_windsurf(agents: str) -> str:
    return canonical_to_clinerules(agents)

def canonical_to_aider(agents: str) -> str:
    return f"# AI Global OS\n\n{agents}\n"

def canonical_to_copilot(agents: str) -> str:
    return canonical_to_clinerules(agents)

def main() -> None:
    agents = read_agents()
    # .cursor/rules/ai-global-os.mdc
    (ROOT / ".cursor" / "rules" / "ai-global-os.mdc").write_text(
        canonical_to_cursor_mdc(agents, "AI Global OS canonical adapter", [], ""),
        encoding="utf-8"
    )
    # .claude/CLAUDE.md
    (ROOT / ".claude" / "CLAUDE.md").write_text(
        canonical_to_claude(agents), encoding="utf-8"
    )
    # .clinerules/ai-global-os.md
    (ROOT / ".clinerules" / "ai-global-os.md").write_text(
        canonical_to_clinerules(agents), encoding="utf-8"
    )
    # .windsurfrules
    (ROOT / ".windsurfrules").write_text(
        canonical_to_windsurf(agents), encoding="utf-8"
    )
    # .aider.conf.yml preamble
    aider = (
        "read:\n  - AGENTS.md\n  - global-roles.md\n  - global-workflow.md\n"
        "model: claude-sonnet-4-6\nauto-commits: false\ndirty-commits: false\n\n"
        f"# AI Global OS\n{agents}\n"
    )
    (ROOT / ".aider.conf.yml").write_text(aider, encoding="utf-8")
    # .github/copilot-instructions.md
    (ROOT / ".github" / "copilot-instructions.md").write_text(
        canonical_to_copilot(agents), encoding="utf-8"
    )
    print("Synced agent configs from AGENTS.md")

if __name__ == "__main__":
    main()
