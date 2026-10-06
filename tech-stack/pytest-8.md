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
25. [REQ] `--cov` sources MUST be path-form (`--cov=src/`), never dotted module names (`--cov=src`). Dotted names make coverage resolve them via `importlib.util.find_spec`, which executes the parent package `__init__.py` during `pytest_load_initial_conftests`. Package init chains that import PyO3 extensions (e.g. `cryptography` `_rust`) fail with "PyO3 modules ... may only be initialized once per interpreter process" inside that reentrant import context, poisoning every later crypto import in the session. Path-form sources skip module resolution entirely.
26. [REQ] Optional heavy deps (sentence_transformers/torch, transformers) MUST be lazy-imported inside the function that uses them — never module-level try/except. Root `conftest.py` imports `memory.store` on every run; a module-level ST import cost ~7.6s cold per process (and per xdist worker). Keep a patchable module attribute + `_UNSET` sentinel so tests can still `patch.object(mod, "Dep", None)`.
27. [REQ] NEVER run `gc.collect()` in a per-test autouse fixture — a full collect costs ~0.1s+ on a large heap (~11 min across a 6.7k-test suite). Amortize (every N tests) or rely on refcounting; cyclic garbage tolerates delay.
28. [REQ] GC boot window for large suites (PostHog/Instagram pattern): `gc.disable()` at conftest import, then in `pytest_collection_modifyitems` run `gc.freeze(); gc.set_threshold(50_000, 20, 20); gc.enable()`. Freezes permanent collection-time objects so later sweeps skip them.
29. [REQ] Use `--ignore=<dir>` for whole-dir exclusions; `-m` deselect still imports the modules (module-level code runs at collection). aiZee fast tier ignores `tests/mcp`, `tests/dashboard`, `tests/e2e`, `tests/memory/test_vector.py`.
30. [REQ] pytest-xdist `-n` IS a win on Windows for large suites once heavy imports are lazy (measured: 6.7k tests in ~83s at `-n 12`). Each worker re-pays import cost via spawn — keep module imports cheap. `-n logical` uses logical cores when psutil is installed.
31. [REQ] `pytest-testmon` (`--testmon`) selects only tests affected by changed code via a coverage-derived dependency DB — ideal for FAST tier on large suites. Requires one baseline run to build `.testmondata`.
32. [REQ] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` + explicit `-p xdist -p timeout` trims startup ~40% for single-test invocations (auto-loaded plugins: cov, anyio, xdist, timeout...).
33. [REQ] Never assume an optional dep is absent in tests — transitive deps (e.g. `opentelemetry-api` via litellm) may install the API surface without the SDK. Simulate absence with `monkeypatch.setitem(sys.modules, "pkg", None)` and reset warn-once globals.
34. [REQ] Both tiers parallelize by default via pytest-xdist when installed (`aizee test`, `aizee test --full`); `--no-xdist` is the opt-out escape hatch. Workers = `os.cpu_count() - 2` (floor 2) — max out the box, leave the OS breathing room. Measured on 16-core Windows: 7,633 tests + 100% coverage in ~127s vs ~10min sequential. pytest-cov merges per-worker coverage automatically.
35. [REQ] GPU is NOT a test-suite lever by default — decide by measurement, not hope. (a) Install the CUDA build (`torch==<ver>+cu126` from the PyTorch index) only when tests run REAL GPU-bound code (un-mocked torch/TF/transformers inference). (b) Verify utilization with `nvidia-smi` during the run — compute apps + %util, not just process listing. (c) CUDA contexts cost ~200-300MB VRAM per worker; a fully-mocked suite pays init overhead for zero compute. Measured on aiZee (all model calls mocked): CPU-torch run 127s vs CUDA-torch run 151s — GPU made it *slower*; a real matmul benchmark proved the GPU itself works (100% util, 7.7x). What Windows shows as "GPU" in Task Manager is the display adapter, not compute.
36. [REQ] When C: is full or roaming-installs are heavy, install experiment packages to a scratch dir on another drive (`pip install --target <dir> --no-deps`, env `TMPDIR=<dir>`) and run via `PYTHONPATH=<dir>` — zero env pollution, delete when done.
[COMPAT]
- v8.4: current installed. `--strict-markers` enforced. `pytest-asyncio` auto mode supported.
- Plugins: `pytest-asyncio` (0.24+, auto mode), `pytest-xdist`, `pytest-timeout`, `pytest-cov`.
- Config: `pyproject.toml` `[tool.pytest.ini_options]` is the canonical config location.
[REFS]
- https://docs.pytest.org/en/stable/
- https://docs.pytest.org/en/stable/how-to/parametrize.html
- https://pytest-asyncio.readthedocs.io/en/latest/auto_mode.html
- https://docs.pytest.org/en/stable/reference/reference.html#pytest.HookimplMarker
