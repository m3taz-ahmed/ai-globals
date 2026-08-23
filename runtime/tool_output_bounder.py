"""Tool output bounding for MCP tools.

Ported from strix (usestrix/strix) agent factory pattern.
Bounds tool output before it enters the LLM context to prevent a
single tool call from consuming the entire context budget.

Usage::

    from runtime.tool_output_bounder import bound_output
    result = bound_output(tool_output, max_lines=200, max_bytes=8000)
    # result.text is the bounded string
    # result.truncated is True if either limit was hit
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OutputBounds:
    """Configuration for tool output bounding."""

    max_lines: int = 200
    max_bytes: int = 8000
    truncation_marker: str = "\n... [output truncated: {reason}]"


@dataclass(frozen=True)
class BoundedOutput:
    """Result of bounding a tool output."""

    text: str
    truncated: bool
    original_lines: int
    original_bytes: int
    bounded_lines: int
    bounded_bytes: int
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "truncated": self.truncated,
            "original_lines": self.original_lines,
            "original_bytes": self.original_bytes,
            "bounded_lines": self.bounded_lines,
            "bounded_bytes": self.bounded_bytes,
            "reason": self.reason,
        }


# Default bounds — conservative for chat-agent context windows.
DEFAULT_BOUNDS = OutputBounds(max_lines=200, max_bytes=8000)

# Larger bounds for audit/research tools that produce structured output.
AUDIT_BOUNDS = OutputBounds(max_lines=500, max_bytes=20000)

# Smaller bounds for quick lookup tools.
QUICK_BOUNDS = OutputBounds(max_lines=50, max_bytes=2000)


def bound_output(
    output: str,
    bounds: OutputBounds | None = None,
) -> BoundedOutput:
    """Bound *output* to at most *bounds.max_lines* lines and *bounds.max_bytes* bytes.

    If both limits are hit, the more restrictive one wins (whichever
    truncates first). A truncation marker is appended when truncation
    occurs, explaining which limit was hit.
    """
    if bounds is None:
        bounds = DEFAULT_BOUNDS
    if not isinstance(output, str):
        raise TypeError(f"bound_output expects str, got {type(output).__name__}")

    original_bytes = len(output.encode("utf-8"))
    lines = output.splitlines(keepends=True)
    original_lines = len(lines)

    # Check line limit first
    truncated = False
    reason = ""
    kept_lines = lines

    if len(lines) > bounds.max_lines:
        kept_lines = lines[: bounds.max_lines]
        truncated = True
        reason = f"{len(lines)} lines > {bounds.max_lines} line limit"

    # Now check byte limit on the line-truncated text
    current_text = "".join(kept_lines)
    current_bytes = len(current_text.encode("utf-8"))

    if current_bytes > bounds.max_bytes:
        # Truncate at byte boundary, then walk back to avoid splitting a
        # multi-byte UTF-8 character.
        encoded = current_text.encode("utf-8")[: bounds.max_bytes]
        try:
            decoded = encoded.decode("utf-8")
        except UnicodeDecodeError:
            # Walk back until we have valid UTF-8
            for i in range(1, 4):
                try:
                    decoded = encoded[:-i].decode("utf-8")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                decoded = encoded.decode("utf-8", errors="replace")
        current_text = decoded
        truncated = True
        byte_reason = f"{current_bytes} bytes > {bounds.max_bytes} byte limit"
        reason = f"{reason}; {byte_reason}" if reason else byte_reason

    bounded_lines = len(current_text.splitlines())
    bounded_bytes = len(current_text.encode("utf-8"))

    if truncated:
        marker = bounds.truncation_marker.format(reason=reason)
        current_text = current_text.rstrip() + marker

    return BoundedOutput(
        text=current_text,
        truncated=truncated,
        original_lines=original_lines,
        original_bytes=original_bytes,
        bounded_lines=bounded_lines,
        bounded_bytes=bounded_bytes,
        reason=reason,
    )


def bound_json_output(
    data: Any,
    bounds: OutputBounds | None = None,
) -> BoundedOutput:
    """Serialize *data* to JSON and bound the result.

    Convenience for MCP tools that return structured data.
    """
    import json

    output = json.dumps(data, indent=2, default=str, ensure_ascii=False)
    return bound_output(output, bounds)


def bound_tool_result(
    result: Any,
    tool_name: str,
    bounds: OutputBounds | None = None,
) -> str:
    """Bound a tool result and return the string for LLM context.

    If *result* is already a string, bound it directly. If it's a dict
    or list, serialize to JSON first. The tool name is included in the
    truncation marker for debugging.
    """
    if bounds is None:
        bounds = DEFAULT_BOUNDS

    if isinstance(result, str):
        output = result
    else:
        import json

        output = json.dumps(result, indent=2, default=str, ensure_ascii=False)

    # Override marker to include tool name
    named_bounds = OutputBounds(
        max_lines=bounds.max_lines,
        max_bytes=bounds.max_bytes,
        truncation_marker=f"\n... [output from {tool_name} truncated: {{reason}}]",
    )
    bounded = bound_output(output, named_bounds)
    return bounded.text
