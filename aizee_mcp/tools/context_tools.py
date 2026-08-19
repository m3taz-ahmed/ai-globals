#!/usr/bin/env python3
"""Context discovery MCP tools: tech-stack, skills, changelog, active context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aizee_mcp._compat import FastMCP

from .common import (
    _MAX_RESULTS,
    is_safe_name,
    resolve_path,
    root,
    truncate,
    validate_query,
)


def register_context_tools(mcp: FastMCP) -> None:
    """Register context discovery tools and resources."""

    @mcp.tool()
    def get_tech_stack(pkg: str, ver: str) -> str:
        """Get the tech-stack file for a package version."""
        if not is_safe_name(pkg) or not is_safe_name(ver):
            return json.dumps({"ok": False, "error": "Invalid package or version name"})
        r = root()
        path = resolve_path(r, Path("tech-stack") / f"{pkg}-{ver}.md")
        if path is None:
            return json.dumps({"ok": False, "error": "Invalid path"})
        if not path.exists():
            return json.dumps({"exists": False, "path": str(path.relative_to(r))})
        return json.dumps({"exists": True, "path": str(path.relative_to(r)), "content": path.read_text(encoding="utf-8")})

    @mcp.tool()
    def search_skills(query: str, limit: int = 20) -> str:
        """Search available skills by keyword (matches name, description, and body)."""
        err = validate_query(query)
        if err:
            return err
        limit = max(1, min(limit, _MAX_RESULTS))
        r = root()
        query_lower = query.lower()
        results: list[dict[str, Any]] = []
        skills_dir = r / "skills"
        if not skills_dir.is_dir():
            return json.dumps(results, indent=2)
        for skill_file in sorted(skills_dir.rglob("*.md")):
            try:
                content = skill_file.read_text(encoding="utf-8")
            except OSError:
                continue
            if query_lower in content.lower():
                rel = str(skill_file.relative_to(r)).replace("\\", "/")
                name = skill_file.stem
                description = ""
                for line in content.splitlines():
                    if line.lower().startswith("description:"):
                        description = line.split(":", 1)[1].strip().strip('"').strip("'")
                        break
                results.append({"name": name, "file": rel, "description": truncate(description, 150)})
                if len(results) >= limit:
                    break
        return json.dumps(results, indent=2)

    @mcp.tool()
    def get_changelog(section: str = "unreleased", limit: int = 50) -> str:
        """Return the changelog (default: [Unreleased] section)."""
        if section not in ("unreleased", "latest", "full"):
            return json.dumps({"ok": False, "error": "section must be 'unreleased', 'latest', or 'full'"})
        r = root()
        path = r / "CHANGELOG.md"
        if not path.exists():
            return json.dumps({"ok": False, "error": "CHANGELOG.md not found"})
        content = path.read_text(encoding="utf-8")
        if section == "full":
            return json.dumps({"ok": True, "content": truncate(content, 5000)}, indent=2)
        lines = content.splitlines()
        output: list[str] = []
        capturing = section == "unreleased"
        for line in lines:
            if line.startswith("## ["):
                if section == "unreleased" and "[Unreleased]" in line:
                    capturing = True
                    output.append(line)
                    continue
                if section == "latest" and "[Unreleased]" not in line:
                    capturing = True
                    output.append(line)
                    continue
                if capturing and output:
                    break
                capturing = False
                continue
            if capturing:
                output.append(line)
        return json.dumps({"ok": True, "section": section, "content": truncate("\n".join(output), limit * 80)}, indent=2)

    @mcp.tool()
    def get_active_context() -> str:
        """Return the ACTIVE_CONTEXT.md handoff file content."""
        r = root()
        path = r / "ACTIVE_CONTEXT.md"
        if not path.exists():
            return json.dumps({"ok": False, "error": "ACTIVE_CONTEXT.md not found"})
        return json.dumps({"ok": True, "content": truncate(path.read_text(encoding="utf-8"), 8000)}, indent=2)

    @mcp.resource("os://AGENTS")
    def get_agents() -> str:
        r = root()
        path = r / "AGENTS.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""
