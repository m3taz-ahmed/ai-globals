[TECH] python-3
[OBJ] Python 3.x (3.10–3.13+) language and stdlib standards for aiZee runtime.
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
11. [REQ] PEP 695 generic syntax: `class Box[T]:` / `def first[T](xs: list[T]) -> T:` (3.12+). Use `type Point = tuple[float, float]` for type aliases (3.12+). No `TypeVar` boilerplate for new code.
12. [REQ] PEP 695 `type` statement for aliases: `type Matrix = list[list[float]]`. Replaces `TypeAlias` and `X = ... # type: TypeAlias`.
13. [REQ] `match`/`case` pattern matching (3.10+). Use class patterns (`case Point(x=0, y=0):`), mapping patterns (`case {"type": "error", **rest}:`), and guard clauses. Exhaustive matching for enums.
14. [REQ] Python 3.13 free-threaded mode (`PEP 703`): use `python3.13t` binary for GIL-free execution. Only enable for CPU-bound parallel workloads verified thread-safe. Audit C extensions for thread safety before enabling.
15. [REQ] Python 3.13 experimental JIT (`PEP 744`): enable via `PYTHON_JIT=1` env. Benchmark before/after — JIT benefits numeric hot loops, not I/O-bound code. Do not rely on JIT for correctness.
16. [REQ] `@override` decorator (3.12+, PEP 698) on all method overrides. Catches signature drift at type-check time.
17. [REQ] `ExceptionGroup` + `TaskGroup` (3.11+) for concurrent error handling. Use `async with asyncio.TaskGroup() as tg: tg.create_task(...)`. Catch groups with `except*`.
18. [REQ] Class <300 lines, method <30 lines (`[CODE-03]`).
19. [REQ] Constructor injection. Pass dependencies in `__init__`.
20. [PROHIBIT] Bare `Exception`. Always `AizeeException` subclass with `error_code` + `context`.
21. [PROHIBIT] Empty `except`/`catch`. Log with context.
22. [PROHIBIT] Inline `await import()`. Top-level imports only.
23. [PROHIBIT] `time.sleep()` in async code. Use `asyncio.sleep()`.
[COMPAT]
- 3.10: `match` statements, `ParamSpec`, `TypeAlias`.
- 3.11: `tomllib`, `ExceptionGroup`, `TaskGroup`, `except*`.
- 3.12: `type` statement (PEP 695), `@override` decorator (PEP 698), generic syntax `class Box[T]`.
- 3.13: free-threaded mode (`python3.13t`, PEP 703), experimental JIT (PEP 744), improved `match`/`case` error messages, `dbm.sqlite3` default backend.
- 3.14: `asyncio.get_event_loop()` removed. `asyncio.iscoroutinefunction()` deprecated. `t-strings` (template strings, PEP 750).
[REFS]
- PEP 563 (postponed eval), PEP 604 (`X | Y` unions), PEP 695 (`type` stmt, generics), PEP 698 (`@override`), PEP 703 (free-threaded), PEP 744 (JIT), PEP 750 (t-strings).
- https://docs.python.org/3/whatsnew/3.13.html
- https://peps.python.org/pep-0695/
- https://peps.python.org/pep-0703/
