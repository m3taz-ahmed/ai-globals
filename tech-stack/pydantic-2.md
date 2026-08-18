[TECH] pydantic-2
[OBJ] Pydantic 2.x validation standards for aiZee schemas.
[RULES]
1. [REQ] `BaseModel` with `ConfigDict(extra="allow")` for dynamic action envelopes. `extra="forbid"` for strict DTOs.
2. [REQ] `Field(..., min_length=1, ge=0)` for constraints. Never manual validation in `__init__`.
3. [REQ] `model_dump()` not `dict()`. `model_validate()` not `parse_obj()`.
4. [REQ] `model_config = ConfigDict(...)` not inner `class Config`.
5. [REQ] Custom validators via `@field_validator` (not `@validator`). `@model_validator(mode="after")` for cross-field.
6. [REQ] `StrEnum` / `IntEnum` for typed constants. Avoid raw string literals.
7. [REQ] `TypeAdapter[T]` for validating non-model types (lists, dicts, primitives).
8. [REQ] `ValidationError` from pydantic caught at boundary, re-raised as `AizeeException` subclass.
9. [REQ] `model_dump_json()` for serialization. `model_validate_json()` for deserialization.
10. [PROHIBIT] `parse_obj`, `parse_raw`, `dict()`, `json()` (v1 API removed in v2).
11. [PROHIBIT] Mutable default values. Use `Field(default_factory=list)`.
12. [PROHIBIT] `Optional[X] = None` when field is required. Use `X` (no default).
[COMPAT]
- v2.0: `ConfigDict`, `@field_validator`, `model_dump`.
- v2.5: `@model_validator(mode="after")`.
- v2.13: current installed. Stable API.
[REFS]
- docs.pydantic.dev/latest/
