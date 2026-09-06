[TECH] Python 3.14
[OBJ] Python 3.14.x (released Oct 2025, latest 3.14.7 Aug 2026). t-strings (PEP 750), deferred annotations (PEP 649), stdlib subinterpreters (PEP 734), improved errors, free-threaded + JIT improvements.
[RULES]
1. [REQ] Use template strings (t-strings, PEP 750) with `t"..."` / `t'...'` / `t"""..."""` for safe string templating with automatic escaping; access parts via `Template.parts` — replaces manual `.format()` + escaping for HTML/SQL/injection-prone contexts.
2. [REQ] Use deferred evaluation of annotations (PEP 649) — annotations are no longer eagerly evaluated. Access via `typing.get_type_hints()` or `__annotations__` (lazy). `from __future__ import annotations` is now default behavior; remove redundant import.
3. [REQ] Use stdlib subinterpreters (PEP 734) via `interpreters` module for true parallelism without GIL contention: `interpreters.create()`, `interpreters.run_sync()`. Prefer over multiprocessing for CPU-bound isolated workloads.
4. [REQ] Use improved error messages: better tracebacks with caret pointers, suggestions for misspelled names, and enhanced `NameError` / `AttributeError` hints — leverage for debugging.
5. [REQ] Enable free-threaded mode (PEP 703, `--disable-gil` build / `python3.14t`) for CPU-bound multi-threaded workloads; verify C-extension compatibility before deployment.
6. [REQ] Use JIT improvements (copy-and-patch tier-2) for hot loops; benchmark with `python -X jit` vs `python -X no-jit` — JIT is opt-in experimental, not always faster.
7. [REQ] Use `python -m` for module execution; `python -X dev` for development mode (debug assertions, warnings).
8. [REQ] Use `dataclasses` with `slots=True` for memory-efficient data containers; combine with `kw_only=True` for keyword-only fields.
9. [REQ] Use `type` statement for type aliases (PEP 695): `type Vector = list[float]`. Use `type X = ...` for generic aliases.
10. [REQ] Use `match` statements (structural pattern matching) for dispatch logic; prefer over long `if/elif` chains.
11. [REQ] Use `tomllib` (stdlib) for parsing TOML configs: `tomllib.load(open("pyproject.toml", "rb"))`.
12. [REQ] Use `pathlib.Path` for all filesystem paths — never raw `os.path` string concatenation.
13. [REQ] Use `uv` for dependency management + virtual envs (fast Rust-based): `uv venv`, `uv pip install`, `uv sync`.
14. [REQ] Use `ruff` for linting + formatting (replaces flake8 + black + isort). `mypy` or `pyright` for type checking.
15. [REQ] Use Windows install manager (`py.exe` / `python.org` installer) for multi-version management on Windows.
16. [CMD] `python3.14 -X dev script.py` run in dev mode with assertions.
17. [CMD] `python3.14t script.py` run free-threaded build (no GIL).
18. [CMD] `python3.14 -X jit script.py` enable experimental JIT.
19. [PROHIBIT] Never use `eval()` / `exec()` with untrusted input.
20. [PROHIBIT] Never use `pickle` for untrusted data — use `json` / `msgspec` / `pydantic`.
21. [PROHIBIT] Never use `assert` for runtime validation in production (stripped with `-O`); use explicit `if/raise`.
22. [PROHIBIT] Never rely on annotation evaluation order — PEP 649 makes them lazy.
[COMPAT]
- Python 3.14.x (released Oct 2025, latest 3.14.7 Aug 2026).
- Python 3.15 in beta (release late 2026).
- Free-threaded build: `python3.14t` (experimental).
- Windows: new install manager (replaces legacy installer).
- pip 25+, uv 0.5+ recommended.
[REFS]
- https://docs.python.org/3.14/
- https://peps.python.org/pep-0750/ (t-strings)
- https://peps.python.org/pep-0649/ (deferred annotations)
- https://peps.python.org/pep-0734/ (subinterpreters)
