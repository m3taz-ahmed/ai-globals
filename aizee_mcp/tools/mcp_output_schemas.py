"""MCP tool output schema validation.

Ported from open-seo (every-app/open-seo) output schema pattern.
Each MCP tool can define an ``output_schema`` (Pydantic model) that
validates the tool's response before it's returned to the LLM.
This ensures downstream consumers know exactly what to expect.

Usage::

    from aizee_mcp.tools.mcp_output_schemas import validate_output
    from pydantic import BaseModel

    class SeoAuditOutput(BaseModel):
        url: str
        issues: list[dict]
        health_score: int

    @mcp.tool()
    def seo_audit_page(url: str) -> str:
        result = _do_audit(url)
        validated = validate_output(result, SeoAuditOutput, "seo_audit_page")
        return json.dumps(validated.model_dump())
"""

from __future__ import annotations

import json
import logging
from typing import Any, TypeVar

from pydantic import BaseModel, TypeAdapter, ValidationError
from pydantic import Field as PydField

from runtime.schemas import AizeeError, ErrorSeverity

_logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class OutputSchemaError(AizeeError):
    """Raised when a tool output fails schema validation."""

    def __init__(self, tool_name: str, errors: list[Any]) -> None:
        message = f"Output from {tool_name} failed schema validation"
        super().__init__(
            "OUTPUT_SCHEMA_ERROR",
            message,
            ErrorSeverity.HIGH,
            {"tool_name": tool_name, "validation_errors": errors},
        )


def validate_output(  # noqa: UP047
    data: dict[str, Any],
    schema: type[T],
    tool_name: str,
    strict: bool = True,
) -> T:
    """Validate *data* against *schema* and return the parsed model.

    If *strict* is True, validation errors raise :class:`OutputSchemaError`.
    If False, invalid fields are dropped and schema defaults apply — the
    remaining data is re-validated, so the returned model is always fully
    validated (never bypassed via ``model_construct``).
    """
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        errors = exc.errors()
        if strict:
            raise OutputSchemaError(tool_name, errors) from exc
        _logger.warning(
            "Output from %s failed schema validation (non-strict): %s",
            tool_name, errors,
        )
        # Best-effort: keep only fields that individually validate, so the
        # reconstructed model still passes schema validation.
        sanitized: dict[str, Any] = {}
        for name in schema.model_fields:
            if name not in data:
                continue
            try:
                TypeAdapter(schema.model_fields[name].annotation).validate_python(data[name])
            except ValidationError:
                continue
            sanitized[name] = data[name]
        try:
            return schema.model_validate(sanitized)
        except ValidationError as exc2:
            raise OutputSchemaError(tool_name, exc2.errors()) from exc2


def validate_json_output(  # noqa: UP047
    json_str: str,
    schema: type[T],
    tool_name: str,
    strict: bool = True,
) -> T:
    """Parse *json_str* and validate against *schema*."""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise OutputSchemaError(tool_name, [{"msg": f"Invalid JSON: {exc}"}]) from exc
    return validate_output(data, schema, tool_name, strict)


def safe_model_dump(model: BaseModel) -> dict[str, Any]:
    """Dump a Pydantic model to a JSON-safe dict."""
    dumped: dict[str, Any] = json.loads(model.model_dump_json())
    return dumped


# ---------------------------------------------------------------------------
# Common output schemas for aiZee MCP tools
# ---------------------------------------------------------------------------


class ToolMeta(BaseModel):
    """Standard metadata included in tool outputs."""

    tool_name: str = ""
    execution_time_ms: float = 0.0
    truncated: bool = False


class SeoAuditPageOutput(BaseModel):
    """Output schema for ``seo_audit_page``."""

    url: str
    status_code: int = 0
    issues: list[dict[str, Any]] = PydField(default_factory=list)
    health_score: int = 100
    issue_count: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0


class SeoAuditSiteOutput(BaseModel):
    """Output schema for ``seo_audit_site``."""

    start_url: str
    pages_crawled: int = 0
    pages_total: int = 0
    issues: list[dict[str, Any]] = PydField(default_factory=list)
    health_score: int = 100
    crawl_duration_ms: float = 0.0
    current_phase: str = "completed"


class SeoCheckCwvOutput(BaseModel):
    """Output schema for ``seo_check_cwv``."""

    url: str
    lcp: float | None = None
    inp: float | None = None
    cls: float | None = None
    ttfb: float | None = None
    fcp: float | None = None
    status: str = "good"
    metrics: dict[str, Any] = PydField(default_factory=dict)


class MemorySearchOutput(BaseModel):
    """Output schema for ``memory_search``."""

    query: str
    results: list[dict[str, Any]] = PydField(default_factory=list)
    total: int = 0
    truncated: bool = False


class PolicyCheckOutput(BaseModel):
    """Output schema for ``policy_check``."""

    action: str
    allowed: bool
    reason: str = ""
    budget_action: str = "warn"


# Registry of tool → output schema for runtime validation.
TOOL_OUTPUT_SCHEMAS: dict[str, type[BaseModel]] = {
    "seo_audit_page": SeoAuditPageOutput,
    "seo_audit_site": SeoAuditSiteOutput,
    "seo_check_cwv": SeoCheckCwvOutput,
    "memory_search": MemorySearchOutput,
    "policy_check": PolicyCheckOutput,
}


def get_tool_schema(tool_name: str) -> type[BaseModel] | None:
    """Return the output schema for *tool_name*, or None if not registered."""
    return TOOL_OUTPUT_SCHEMAS.get(tool_name)


def validate_tool_output(
    tool_name: str,
    data: dict[str, Any],
    strict: bool = True,
) -> BaseModel | None:
    """Validate a tool's output against its registered schema.

    Returns the validated model, or ``None`` if no schema is registered
    for *tool_name*.
    """
    schema = get_tool_schema(tool_name)
    if schema is None:
        return None
    return validate_output(data, schema, tool_name, strict)
