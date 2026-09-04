"""Contract-first artifact emitter â€" emit machine-readable JSON + type stubs.

Inspired by Prisma's contract-first design which emits ``contract.json`` +
``contract.d.ts`` as machine-readable artifacts (no executable codegen),
enabling AI agent understanding and runtime validation.

This module emits JSON schemas + TypeScript stubs from aiZee's Pydantic
schemas so external tools (AI agents, dashboards, MCP clients) can consume
the contract without importing Python.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity


class ContractEmitError(AizeeError):
    """Raised when contract emission fails."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("CONTRACT_EMIT_ERROR", message, ErrorSeverity.MEDIUM, context)


@dataclass
class ContractArtifact:
    """A single emitted contract artifact (JSON or TS)."""

    name: str
    json_schema: dict[str, Any]
    typescript_stub: str

    def to_json(self) -> str:
        """Serialize the JSON schema to a pretty string."""
        return json.dumps(self.json_schema, indent=2, sort_keys=True)

    def to_typescript(self) -> str:
        """Return the TypeScript stub string."""
        return self.typescript_stub


def _py_type_to_ts(py_type: str) -> str:
    """Map a Python/JSON-Schema type string to a TypeScript type string."""
    mapping = {
        "str": "string",
        "string": "string",
        "int": "number",
        "integer": "number",
        "float": "number",
        "number": "number",
        "bool": "boolean",
        "boolean": "boolean",
        "list": "Array<any>",
        "array": "Array<any>",
        "dict": "Record<string, any>",
        "object": "Record<string, any>",
        "Any": "any",
        "any": "any",
        "None": "null",
        "null": "null",
    }
    return mapping.get(py_type, "any")


def _field_def_to_ts(field_def: dict[str, Any], root_schema: dict[str, Any]) -> str:
    """Map a JSON-Schema field def to TS, resolving $ref/anyOf where known."""
    if "$ref" in field_def:
        ref = str(field_def["$ref"])
        # Resolve local refs like #/$defs/Name or #/definitions/Name.
        name = ref.rsplit("/", 1)[-1]
        return name or "any"
    if "anyOf" in field_def and isinstance(field_def["anyOf"], list):
        parts = [_field_def_to_ts(p, root_schema) for p in field_def["anyOf"]]
        seen: list[str] = []
        for p in parts:
            if p not in seen:
                seen.append(p)
        return " | ".join(seen) if seen else "any"
    if "type" in field_def:
        ftype = field_def["type"]
        if isinstance(ftype, list):
            return " | ".join(_py_type_to_ts(str(t)) for t in ftype)
        return _py_type_to_ts(str(ftype))
    return "any"


def emit_contract(
    schema_class: type,
    *,
    name: str | None = None,
) -> ContractArtifact:
    """Emit a ContractArtifact from a Pydantic schema class or dataclass.

    For Pydantic v2 models, uses ``model_json_schema()``.
    For plain dataclasses, builds a minimal schema from annotations.
    """
    artifact_name = name or schema_class.__name__
    json_schema: dict[str, Any]
    fields_info: dict[str, str] = {}

    if hasattr(schema_class, "model_json_schema"):
        try:
            json_schema = schema_class.model_json_schema()
        except Exception as exc:
            raise ContractEmitError(f"Cannot emit contract for {artifact_name}: {exc}") from exc
        props = json_schema.get("properties", {})
        for field_name, field_def in props.items():
            fields_info[field_name] = _field_def_to_ts(field_def, json_schema)
    elif hasattr(schema_class, "__annotations__") and schema_class.__annotations__:
        json_schema = {
            "type": "object",
            "title": artifact_name,
            "properties": {
                fname: {"type": "any"} for fname in schema_class.__annotations__
            },
        }
        for fname, ftype in schema_class.__annotations__.items():
            ts_type = _py_type_to_ts(getattr(ftype, "__name__", str(ftype)))
            fields_info[fname] = ts_type
    else:
        raise ContractEmitError(
            f"Cannot emit contract for {artifact_name}: not a Pydantic model or dataclass"
        )

    ts_lines = [f"export interface {artifact_name} {{"]
    required = set(json_schema.get("required", [])) if isinstance(json_schema.get("required", []), list) else set()
    for fname, ftype in fields_info.items():
        # Honor required[]: only listed fields are required; others optional.
        mark = "" if fname in required else "?"
        # When schema has no required[] (dataclass fallback), keep all required for compat.
        if "required" not in json_schema:
            mark = ""
        ts_lines.append(f"  {fname}{mark}: {ftype};")
    ts_lines.append("}")
    ts_stub = "\n".join(ts_lines)

    return ContractArtifact(name=artifact_name, json_schema=json_schema, typescript_stub=ts_stub)


def emit_contracts(
    schema_classes: list[type],
    *,
    output_dir: Path | None = None,
) -> dict[str, ContractArtifact]:
    """Emit contracts for multiple schema classes. Optionally write to disk.

    Returns a mapping of artifact name â†' ContractArtifact.
    If ``output_dir`` is provided, writes ``<name>.json`` and ``<name>.d.ts``
    for each artifact.
    """
    artifacts: dict[str, ContractArtifact] = {}
    resolved_dir: Path | None = None
    if output_dir is not None:
        try:
            resolved_dir = output_dir.resolve()
            resolved_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ContractEmitError(f"Cannot create output_dir {output_dir}: {exc}") from exc
    for cls in schema_classes:
        try:
            artifact = emit_contract(cls)
        except ContractEmitError:
            raise
        except Exception as exc:
            raise ContractEmitError(f"Cannot emit contract: {exc}") from exc
        artifacts[artifact.name] = artifact
        if resolved_dir is not None:
            for filename, content in (
                (f"{artifact.name}.json", artifact.to_json()),
                (f"{artifact.name}.d.ts", artifact.to_typescript()),
            ):
                target = (resolved_dir / filename).resolve()
                try:
                    target.relative_to(resolved_dir)
                except ValueError:
                    raise ContractEmitError(f"Refusing to write outside output_dir: {filename}") from None
                try:
                    target.write_text(content, encoding="utf-8")
                except OSError as exc:
                    raise ContractEmitError(f"Cannot write {target}: {exc}") from exc
    return artifacts


def validate_contract(artifact: ContractArtifact, data: dict[str, Any]) -> list[str]:
    """Validate a data dict against a contract artifact's JSON schema.

    Returns a list of error messages (empty if valid). This is a lightweight
    structural check â€" for full JSON Schema validation use ``jsonschema``.
    """
    errors: list[str] = []
    props = artifact.json_schema.get("properties", {})
    if "required" not in artifact.json_schema:
        required_set = set(props)
    else:
        required = artifact.json_schema.get("required", [])
        required_set = set(required) if isinstance(required, list) else set(props)
    for field_name in required_set:
        if field_name not in data:
            errors.append(f"missing required field: {field_name}")
    for key, value in data.items():
        if key not in props:
            errors.append(f"unknown field: {key}")
            continue
        expected_type = props[key].get("type", "any")
        if expected_type == "string" and not isinstance(value, str):
            errors.append(f"{key}: expected string, got {type(value).__name__}")
        elif expected_type == "number" and not isinstance(value, (int, float)):
            errors.append(f"{key}: expected number, got {type(value).__name__}")
        elif expected_type == "boolean" and not isinstance(value, bool):
            errors.append(f"{key}: expected boolean, got {type(value).__name__}")
    return errors
