[TECH] pytest-8
[OBJ] pytest 8.x testing standards for aiZee test suites.
[RULES]
1. [REQ] AAA pattern (Arrange-Act-Assert). One behavior per test (`[TEST-02]`).
2. [REQ] Fixtures for shared setup. `conftest.py` for cross-file fixtures. Factory functions, not hardcoded IDs (`[TEST-03]`).
3. [REQ] `pytest.approx(expected, abs=tol)` for float comparisons. NEVER `==` on time-dependent floats.
4. [REQ] `pytest.importorskip("tkinter")` for optional dependencies. Never let collection break on missing modules.
5. [REQ] `pytest.raises(ExcType, match="regex")` for expected exceptions. Assert on message when relevant.
6. [REQ] Markers: `slow`, `integration`, `unit`, `fast`, `mcp`, `dashboard`, `vector`. Use `@pytest.mark.slow` for E2E.
7. [REQ] `asyncio.run(coro())` for async tests. NEVER `asyncio.get_event_loop().run_until_complete()` (removed in 3.14).
8. [REQ] `@pytest.mark.asyncio` only with `pytest-asyncio` installed. Prefer sync wrappers for simple cases.
9. [REQ] `tmp_path` fixture for filesystem tests. Never write to real cwd.
10. [REQ] `monkeypatch` for env vars and attributes. Restore in `finally` or use `monkeypatch.delenv`.
11. [REQ] Two-tier (`[TEST-07]`): FAST = `pytest <file> --no-cov` (~5s). FULL = `pytest --cov` (before done).
12. [REQ] `pytest-asyncio` auto mode: set `asyncio_mode = "auto"` in `pyproject.toml` `[tool.pytest.ini_options]`. Eliminates need for `@pytest.mark.asyncio` on every async test. All `async def test_*` functions are automatically collected as async tests.
13. [REQ] `@pytest.mark.parametrize("param,expected", [(...), ...])` for data-driven tests. Use `pytest.param(..., id="descriptive_name")` for readable test IDs. Use `ids=` callback for dynamic ID generation.
14. [REQ] `--last-failed-no-failures all` in `pyproject.toml` `[tool.pytest.ini_options]` `addopts`. When `--last-failed` is used and no failures exist, run the full suite. Prevents empty test runs after fixing all failures.
15. [REQ] `tmp_path_factory` fixture for session-scoped temp directories. Use `tmp_path_factory.mktemp("session_data")` for expensive setup shared across test modules. Never use `tmp_path` for session-scoped resources.
16. [REQ] Custom markers via `pyproject.toml`: register markers in `[tool.pytest.ini_options]` `markers` list: `slow: marks tests as slow`, `integration: marks integration tests`. Enables `--strict-markers` validation — unregistered markers cause collection errors.
17. [REQ] Use `@pytest.fixture(scope="session")` for expensive resources (database connections, model loading). Use `scope="function"` (default) for isolated state.
18. [REQ] `pytest -x` (stop on first failure) during FAST iteration. `pytest --lf` (last failed only) for rapid fix cycles. `pytest --sw` (stepwise) for sequential debugging.
19. [REQ] Use `pytest.Config` and `pytest.HookimplMarker` for plugin development. Never use deprecated `pytest.config` global (removed in 8.x).
20. [PROHIBIT] `assert x == 7.0` on floats without `approx` (time drift causes flaky failures).
21. [PROHIBIT] `asyncio.get_event_loop()` (removed Python 3.14).
22. [PROHIBIT] Hardcoded paths/dates (`[TEST-03]`). Use fixtures/factories.
23. [PROHIBIT] Empty `except`. Use `pytest.raises` or assert on outcome.
24. [PROHIBIT] `pytest.config` global (removed in 8.x). Use `request.config` or `pytest.Config`.
[COMPAT]
- v8.4: current installed. `--strict-markers` enforced. `pytest-asyncio` auto mode supported.
- Plugins: `pytest-asyncio` (0.24+, auto mode), `pytest-xdist`, `pytest-timeout`, `pytest-cov`.
- Config: `pyproject.toml` `[tool.pytest.ini_options]` is the canonical config location.
[REFS]
- https://docs.pytest.org/en/stable/
- https://docs.pytest.org/en/stable/how-to/parametrize.html
- https://pytest-asyncio.readthedocs.io/en/latest/auto_mode.html
- https://docs.pytest.org/en/stable/reference/reference.html#pytest.HookimplMarker
