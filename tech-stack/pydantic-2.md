[TECH] pydantic-2
[OBJ] Pydantic 2.10+ validation standards for aiZee schemas — TypeAdapter, computed_field, model_validator, JSON Schema, performance.
[RULES]
1. [REQ] `BaseModel` with `ConfigDict(extra="allow")` for dynamic action envelopes. `extra="forbid"` for strict DTOs.
2. [REQ] `Field(..., min_length=1, ge=0)` for constraints. Never manual validation in `__init__`.
3. [REQ] `model_dump()` not `dict()`. `model_validate()` not `parse_obj()`.
4. [REQ] `model_config = ConfigDict(...)` not inner `class Config`.
5. [REQ] Custom validators via `@field_validator` (not `@validator`). `@model_validator(mode="after")` for cross-field validation. `@model_validator(mode="before")` for pre-type-coercion transforms.
6. [REQ] `StrEnum` / `IntEnum` for typed constants. Avoid raw string literals.
7. [REQ] `TypeAdapter[T]` for validating non-model types (lists, dicts, primitives, unions). Use `TypeAdapter(list[int]).validate_python(data)`. Cache `TypeAdapter` instances at module level — construction has overhead.
8. [REQ] `ValidationError` from pydantic caught at boundary, re-raised as `AizeeException` subclass.
9. [REQ] `model_dump_json()` for serialization. `model_validate_json()` for deserialization. Both are 5–10x faster than `json.dumps(model_dump())`.
10. [REQ] `@computed_field` for derived properties included in `model_dump()` / `model_dump_json()`. Use `@computed_field(return_type=int)` with `@property`. Computed fields are read-only and excluded from `model_validate()`.
11. [REQ] `@model_validator(mode="after")` for cross-field validation that needs typed values. Return `self` from the validator. Raise `ValueError` for validation failures. Use `mode="before"` only when you need raw input (pre-coercion).
12. [REQ] JSON Schema generation: `model.model_json_schema()` for `BaseModel`. `TypeAdapter(T).json_schema()` for non-model types. Use `schema_generator` with `custom_encoder` for non-standard types. Set `mode="serialization"` vs `mode="validation"` for different schema views.
13. [REQ] Use `model_config = ConfigDict(use_enum_values=True)` when enums should be serialized as their values (not names). Use `use_enum_values=False` when round-trip enum validation is required.
14. [REQ] Use `Annotated[int, Field(gt=0)]` for inline constraints in function signatures and `TypeAdapter`. Prefer `Annotated` over separate `Field()` for API boundary definitions.
15. [REQ] Use `model_config = ConfigDict(frozen=True)` for immutable models. Frozen models are hashable and can be used as dict keys / set members. Use for value objects and DTOs that should not mutate.
16. [REQ] Use `model_dump(exclude_none=True)` to omit `None` fields from output. Use `exclude_unset=True` to omit fields not explicitly set by the user. Use `exclude={"field_name"}` for selective exclusion.
17. [REQ] Use `model_copy(update={"field": value})` for immutable updates. Never mutate model fields directly when `frozen=True`.
18. [REQ] Use `pydantic.alias_generators` (`to_camel`, `to_snake`, `to_pascal`) with `ConfigDict(alias_generator=to_camel, populate_by_name=True)` for API boundary naming conventions.
19. [PROHIBIT] `parse_obj`, `parse_raw`, `dict()`, `json()` (v1 API removed in v2).
20. [PROHIBIT] Mutable default values. Use `Field(default_factory=list)`.
21. [PROHIBIT] `Optional[X] = None` when field is required. Use `X` (no default).
22. [PROHIBIT] `@validator` (v1 API). Use `@field_validator` (v2).
23. [PROHIBIT] `class Config:` inner class (v1 API). Use `model_config = ConfigDict(...)` (v2).
[COMPAT]
- v2.0: `ConfigDict`, `@field_validator`, `model_dump`.
- v2.5: `@model_validator(mode="after")`, `mode="before"`.
- v2.7: `@computed_field`, JSON Schema `mode="serialization"`.
- v2.10: `TypeAdapter` improvements, `json_schema()` for non-model types, performance improvements (core validation 5–50x faster than v1). Current installed.
- v2.x: Rust core (`pydantic-core`), Python API layer. `Annotated`-based constraints.
[REFS]
- https://docs.pydantic.dev/latest/
- https://docs.pydantic.dev/latest/concepts/type_adapter/
- https://docs.pydantic.dev/latest/concepts/fields/#computed-fields
- https://docs.pydantic.dev/latest/concepts/validators/#model-validators
- https://docs.pydantic.dev/latest/concepts/json_schema/
- https://docs.pydantic.dev/latest/perf_benchmark/
