"""MCP input-schema profiles.

``AIZEE_MCP_INPUT_SCHEMA_PROFILE=compact`` strips advertised input schemas
to their validation-relevant core (no examples/titles/multi-line field
guidance) - same tool set, same canonical server-side validation, smaller
agent context. Ported from REA's schema-profile pattern; default ``full``
keeps complete advertised guidance for existing clients.

Apply AFTER the manifest lock fingerprints tools so fingerprints always
cover the canonical full schema.
"""

from __future__ import annotations

import logging
import os
from typing import Any

_logger = logging.getLogger(__name__)

PROFILE_ENV = "AIZEE_MCP_INPUT_SCHEMA_PROFILE"
COMPACT = "compact"

_SCHEMA_DROP_KEYS = frozenset({"examples", "example", "title", "$comment", "markdownDescription"})


def schema_profile() -> str:
    """Active profile name from the environment (``full`` unless compact)."""
    return os.environ.get(PROFILE_ENV, "full").strip().lower()


def compact_schema_node(node: Any) -> Any:
    """Strip agent-facing noise from a JSON-schema node (guidance only)."""
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key in _SCHEMA_DROP_KEYS:
                continue
            if key == "description" and isinstance(value, str):
                first_line = next(
                    (line.strip() for line in value.splitlines() if line.strip()), ""
                )
                if not first_line:
                    continue
                out[key] = first_line
                continue
            out[key] = compact_schema_node(value)
        return out
    if isinstance(node, list):
        return [compact_schema_node(item) for item in node]
    return node


def compact_tool_schema(tool: Any) -> None:
    """Compact one tool's advertised input schema in place."""
    params = getattr(tool, "parameters", None)
    if isinstance(params, dict):
        tool.parameters = compact_schema_node(params)


def apply_schema_profile(tool_manager: Any, profile: str | None = None) -> int:
    """Compact every tool's input schema when the compact profile is active.

    Returns the number of tools processed (0 when the profile is not compact).
    """
    if (profile or schema_profile()) != COMPACT:
        return 0
    tools = getattr(tool_manager, "_tools", None)
    if not isinstance(tools, dict):
        return 0
    for tool in tools.values():
        compact_tool_schema(tool)
    _logger.info("MCP input schema profile: compact (%d tools)", len(tools))
    return len(tools)
