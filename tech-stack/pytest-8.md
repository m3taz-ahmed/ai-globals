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
12. [PROHIBIT] `assert x == 7.0` on floats without `approx` (time drift causes flaky failures).
13. [PROHIBIT] `asyncio.get_event_loop()` (removed Python 3.14).
14. [PROHIBIT] Hardcoded paths/dates (`[TEST-03]`). Use fixtures/factories.
15. [PROHIBIT] Empty `except`. Use `pytest.raises` or assert on outcome.
[COMPAT]
- v8.4: current installed. `--strict-markers` enforced.
- Plugins: `pytest-asyncio`, `pytest-xdist`, `pytest-timeout`, `pytest-cov`.
[REFS]
- docs.pytest.org/en/stable/
