[TECH] python-3
[OBJ] Python 3.x (3.10+) language and stdlib standards for aiZee runtime.
[RULES]
1. [REQ] `from __future__ import annotations` in every module (PEP 563).
2. [REQ] Strict typing. No `Any` without justification. Use `dict[str, X]` not `Dict[str, X]`.
3. [REQ] Dataclasses for value objects. Pydantic for validated envelopes.
4. [REQ] Enums/constants over magic strings (`[CODE-04]`).
5. [REQ] `pathlib.Path` over `os.path`. Never hardcode paths.
6. [REQ] `subprocess` with command lists (never `shell=True` with user input).
7. [REQ] Structured logging (dict-based) in hot paths. No f-string logs in perf-critical code.
8. [REQ] `asyncio.run()` for top-level async. NEVER `asyncio.get_event_loop()` (removed in 3.14).
9. [REQ] `inspect.iscoroutinefunction()` not `asyncio.iscoroutinefunction()` (deprecated 3.14, removed 3.16).
10. [REQ] `tomllib` for TOML parsing (stdlib 3.11+). Fallback to `tomli` only on 3.10.
11. [REQ] Class <300 lines, method <30 lines (`[CODE-03]`).
12. [REQ] Constructor injection. Pass dependencies in `__init__`.
13. [PROHIBIT] Bare `Exception`. Always `AizeeException` subclass with `error_code` + `context`.
14. [PROHIBIT] Empty `except`/`catch`. Log with context.
15. [PROHIBIT] Inline `await import()`. Top-level imports only.
16. [PROHIBIT] `time.sleep()` in async code. Use `asyncio.sleep()`.
[COMPAT]
- 3.10: `match` statements, `ParamSpec`, `TypeAlias`.
- 3.11: `tomllib`, `ExceptionGroup`, `TaskGroup`.
- 3.12: `type` statement, `@override` decorator.
- 3.14: `asyncio.get_event_loop()` removed. `asyncio.iscoroutinefunction()` deprecated.
[REFS]
- PEP 563 (postponed eval), PEP 604 (`X | Y` unions), PEP 695 (`type` stmt).
