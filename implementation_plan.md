# AI Global OS — Periodic Evolution & Audit Plan

> Status: Step 1/4 complete. Proposed fixes and upgrades below; awaiting explicit approval before code is written.

## 1. Baseline State

- `ruff check .` — pass
- `pytest -q` — pass (26 tests)
- `python eval/harness.py` — `all_pass: true`
- `mypy .` — **fail** (non-core `tests/` and `skills/` trigger `no-untyped-def`/`import-not-found`; `eval/harness.py` uses bare `dict`)

## 2. Audit Findings

### Technical Debt
1. **Dead vector engine** — `scripts/ai_memory_engine.py` uses `dim=1536` and `brain/global_memory.tvim`, while the live engine `memory/vector.py` uses `dim=384` and `brain/vector_memory.tvim`. It is documented but not invoked by any tool.
2. **DRY violation in `memory/ingest.py`** — `ingest_all()` and `_ingest_dir()` duplicate the same manifest/compare/delete/add/save flow.
3. **Unused `Budget.period`** — `runtime/budget.py` defines `period` but never enforces it, so `daily`/`hourly` budgets never reset and become silently irrelevant.
4. **`mypy` leakage** — `pyproject.toml` only excludes `runtime/tests/*`, `memory/tests/*`, `dashboard/*`, `scripts/*`; `tests/`, `skills/`, and `eval/harness.py` are still checked and fail.

### Security / Resilience
1. **Policy YAML is fragile** — `runtime/policy.py` loads `default.yaml` only and will crash with a `KeyError` if a rule is missing `name`, `condition`, or `action`; invalid `action` values are stored silently.
2. **`MemoryStore` deletes leave orphans** — `delete_by_source_batch()` deletes memories but does not clean `relations`, and it deletes row-by-row instead of with `IN`.
3. **Vector memory keeps invalidated entries** — `MemoryStore.invalidate()` updates `valid_to` but does not remove the vector from the index.
4. **Dashboard/CLI concurrency** — `BudgetManager` updates `usage` and `audit.log` without locks; `Dashboard` uses a class-level `Kernel` across `ThreadingHTTPServer` threads.

### Performance / Efficiency
1. **Vector search is unfiltered** — `VectorMemory.search()` cannot restrict by `kind`/`source`, so `search_vector` scores the whole index and returns irrelevant results.
2. **Ingestor ignores skills and AGENTS.md** — `_DIRS` only tracks `rules/`, `workflows/`, `tech-stack/`; the canonical `AGENTS.md` and `skills/` are not loaded into memory.
3. **MCP `query_rules` does raw file scans** — every call reads and lower-cases every `rules/*.md` file; there is no `ingest` MCP tool, no hybrid vector+FTS tool, and `memory vector --kind` is ignored by the CLI.

### Dependencies
- No outdated dependencies detected. Core versions: `mcp 1.26.0`, `pydantic 2.13.4`, `turbovec 0.7.0`, `numpy 2.2.6`.
- **Risk:** `pyproject.toml` has no upper bounds on major versions; a future `mcp` 2.x or `pydantic` 3.x could break the MCP server or Pydantic schemas.

## 3. Ponytail Filter (what this plan deliberately avoids)

- No new infrastructure (Postgres, Redis, external vector DB).
- No new UI, web framework, or generic dashboard expansion.
- No new heavy third-party packages.
- All upgrades use the existing `pydantic`, `sqlite3`, `turbovec`, `sentence-transformers`, and `mcp` stack.

## 4. Proposed Upgrades

### Upgrade 1 — Resilient Governance (Budget Periods + Policy Validation + Thread Safety)
**Goal:** Make budget enforcement actually time-aware and make policy loading crash-proof.

**Files:**
- `runtime/budget.py`
- `runtime/policy.py`
- `runtime/audit.py`
- `runtime/tests/test_budget.py`
- `runtime/tests/test_policy.py`

**Changes:**
1. Add `Budget.__post_init__` to normalize `period` (`session`, `hourly`, `daily`, `weekly`, `monthly`) and `on_exceed` (`warn`, `fallback`, `block`).
2. Store `session_id` + `process_id` in `usage` and reset `usage` for a scope when the period key changes (session reset only on a new OS process; `daily` resets at midnight UTC).
3. Protect `BudgetManager.check()` and `save()` with a `threading.Lock`; add the same lock to `AuditLogger.log()` so the dashboard cannot corrupt `budget.json` or `audit.log`.
4. Iterate `runtime/policies/*.yaml` sorted; validate each rule has `name`, `condition`, and `action` in `("allow", "ask", "deny")`, skip malformed entries with a warning instead of crashing.

### Upgrade 2 — Hybrid Context Retrieval (Vector + FTS + MCP + CLI)
**Goal:** Let agents and users query the brain in one shot with vector similarity filtered by `kind`/`source`.

**Files:**
- `memory/vector.py`
- `memory/store.py`
- `memory/tests/test_store.py`
- `aios_mcp/aios_server.py`
- `cli.py`
- `tests/mcp/test_mcp_server.py`
- `tests/test_cli.py`

**Changes:**
1. Extend `VectorMemory.search()` to accept an `ids` allowlist and pass it through `turbovec` `index.search(..., allowlist=...)`.
2. Extend `MemoryStore.search_vector()` to accept optional `kind` and `source`, query `SELECT id FROM memories` for valid candidates, and pass them as the vector allowlist.
3. Add MCP tool `query_context(query, k=5, kind=None)` that returns combined `fts` and `vector` results (truncated to 500 chars, with `kind`/`source` metadata).
4. Add MCP tool `ingest_memory()` that calls `Ingestor(...).ingest_all()` and returns the count of ingested memories.
5. Add optional `kind` parameter to MCP `search_memory_vector()`.
6. Add `ai-os query <query>` CLI command with `--kind` and `--limit`.
7. Fix `ai-os memory vector` to pass `--kind` to `MemoryStore.search_vector()`.

### Upgrade 3 — Memory Ingestion Integrity + Efficiency
**Goal:** Make ingestion faster, DRY, and strict about malformed AI files.

**Files:**
- `memory/ingest.py`
- `memory/store.py`
- `memory/tests/test_store.py`
- `tests/test_cli.py`

**Changes:**
1. Refactor `Ingestor` so a single internal `_collect()` helper drives both `ingest_all()` and `_ingest_dir()`.
2. Add `skills/` (recursive) and root `AGENTS.md` to the tracked ingestion directories.
3. Skip malformed AI files (those starting with `[FILE]`, `[TECH]`, `[WORKFLOW]`, or `[SKILL]` but missing `[OBJ]` or `[RULES]`) and emit a warning.
4. Batch `delete_by_source_batch()` with `source IN (...)` and delete orphaned `relations` rows with `source_id IN (...) OR target_id IN (...)` in one query.
5. Remove vector entries when `MemoryStore.invalidate()` is called, so the vector index never returns expired memories.

### Baseline Cleanup (required for zero-defect handoff)
**Files:**
- `pyproject.toml`
- `eval/harness.py`
- `scripts/ai_memory_engine.py` (dead code)
- `README.md`, `scripts/README.md` (remove references)

**Changes:**
1. Add `tests/*` and `skills/*` to `tool.mypy.exclude` so `mypy .` aligns with package boundaries.
2. Fix `eval/harness.py` generic `dict` types (`dict[str, Any]`).
3. Remove the dead `scripts/ai_memory_engine.py` and update its references in `README.md` and `scripts/README.md`.
4. Pin major versions in `pyproject.toml` dependencies to avoid unvetted breaking releases: `mcp>=1.0,<2.0`, `pydantic>=2.0,<3.0`, `rich>=13.0,<14.0`, `pyyaml>=6.0,<7.0`, `sentence-transformers>=2.0,<3.0`, `turbovec>=0.1,<0.8`.

## 5. Verification After Implementation

Before declaring done:
- `ruff check .` — must pass
- `mypy .` — must pass
- `pytest -q` — must pass
- `python eval/harness.py` — must return `all_pass: true`

## 6. Out-of-Scope

- No workflow step execution engine (the no-op `_execute_step` is a known stub; not requested).
- No new dashboard features or CORS rework beyond existing behavior.
- No new databases, caches, or network services.
- No rewrite of `scripts/validate-globals.py` (its logic stays; only `memory/ingest.py` gets its own small AI-file guard).

## 7. Approval Request

Please review the three upgrades and the baseline cleanup. If approved, I will execute them surgically and keep the codebase at 100% green on `ruff`, `mypy`, `pytest`, and `eval/harness.py`.
