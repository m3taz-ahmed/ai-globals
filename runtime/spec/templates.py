#!/usr/bin/env python3
"""Spec-driven template resolution and rendering.

Templates live in ``tech-stack/spec-driven-templates/`` (relative to the
aiZee root) and use ``{{PLACEHOLDER}}`` tokens. All helpers degrade
gracefully: a missing template directory or file yields an empty string,
never an exception.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

# Discovered relative to aiZee root; robust against exec()/runpy contexts
# where __file__ may be undefined.
_THIS_FILE = Path(__file__).resolve() if "__file__" in globals() else Path.cwd() / "templates.py"
_TEMPLATE_DIR_CANDIDATES = [
    _THIS_FILE.parent.parent.parent / "tech-stack" / "spec-driven-templates",
    Path("tech-stack") / "spec-driven-templates",
]


def resolve_template_dir() -> Path | None:
    """Resolve the spec-driven templates directory (aiZee root-relative)."""
    for candidate in _TEMPLATE_DIR_CANDIDATES:
        if candidate.is_dir():
            return candidate
    return None


def render_template(template_name: str, context: dict[str, str]) -> str:
    """Render a template by replacing ``{{PLACEHOLDER}}`` tokens.

    Returns empty string if the template directory or file is absent.
    ``template_name`` is confined to the template directory (no ``..``,
    no absolute paths, no separators) so callers cannot escape it.
    """
    if (
        not template_name
        or template_name.startswith((".", "/", "\\"))
        or ".." in template_name
        or "/" in template_name
        or "\\" in template_name
    ):
        return ""
    template_dir = resolve_template_dir()
    if template_dir is None:
        return ""
    try:
        template_path = (template_dir / template_name).resolve()
        template_path.relative_to(template_dir.resolve())
    except (OSError, ValueError):
        return ""
    if not template_path.is_file():
        return ""
    content = template_path.read_text(encoding="utf-8")
    for key, value in context.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content


def spec_context(
    spec_id: str,
    title: str,
    description: str = "",
    created_at: str = "",
) -> dict[str, str]:
    """Build the template placeholder context for a spec."""
    date_str = created_at[:10] if created_at else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:30] or "spec"
    return {
        "TITLE": title,
        "SPEC_ID": spec_id,
        "FEATURE_BRANCH": f"{spec_id}-{slug}",
        "DATE": date_str,
        "DESCRIPTION": description,
        "PROJECT_NAME": title,
    }
