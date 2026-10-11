# aiZee — Periodic Maintenance: Implementation Plan

**Date:** 2026-10-11 · **Base:** v6.2.0 (`f0f9542`, clean tree) · **Personas:** SEC + QA + DEV
**Scope:** Evolutionary upgrades. No identity changes, no breaking behavior, no heavy infra.

---

## 1. Audit Baseline — what is already green

| Gate | Result |
|---|---|
| `ruff check .` | 0 warnings |
| `aizee doctor` | All health checks ok; wiring table truthful |
| Dependencies | All installed versions within pins (pytest 9.1.1, pytest-cov 7.1.0, graphifyy 0.9.72, pydantic 2.13.5, rich 15.0.0, cryptography 50.0.1, mcp 2.2.0, ST 6.1.0, turbovec 1.0.0) |
| Targeted pytest | 25/25 pass (strict-mode + dual_llm sample) |
| `aizee security scan runtime` | 0 blockers; 1 HIGH + 2 MEDIUM (see F4) |
| Memory.md items verified closed | adapters.py fully implemented (Codex/ClaudeCode/RemoteA2A real, SSRF-guarded); `status().tech_stack` now real via `detect_tech_stack()`; env drift resolved; ingest already has sha256 dedup + stale-source deletion + deterministic IDs |

## 2. Findings

| # | Sev | Finding | Evidence |
|---|-----|---------|----------|
| F1 | **High** | **~16k LOC (~27% of 60k) produces zero runtime effect.** 25 orphan modules = 7,632 LOC + ~60 test files (tested dead code). 20 "constructed-only" services = 6,956 LOC built on every `Kernel()`. 12 marketing modules eagerly imported in `runtime/__init__.py` = 1,451 LOC while marketing tools are config-disabled. ARCH-06 governance theater made visible but not resolved. | doctor wiring table; `__init__.py:30-43`; LOC census |
| F2 | Med | **Startup tax:** `import runtime` = 0.46s (122 submodules, all eager); `Kernel()` = 0.59s. Every CLI call and every one of 7,637 tests pays it. | `importtime`, direct measure |
| F3 | Med | **CODE-03 violations (class <300):** `MemoryStore` 762, `DashboardHandler` 725, `Kernel` 562, `BudgetManager` 412 lines. | AST census |
| F4 | Low | `codemode/_child.py:94` `exec()` flagged HIGH — intentional sandbox runner but lacks the `aizee-scan: ignore` marker convention (8 exist elsewhere). `executor.py:235,246` empty `except (OSError, ValueError): pass` violates "no empty except — log with context". | `aizee security scan` |
| F5 | Low | Memory.md auto-compaction is manual-only (`aizee memory compact` exists; nothing triggers it >500 lines). | `memory/compactor.py`, CLI wiring |

## 3. Proposed upgrades (Ponytail-filtered)

### P0 — Wire the truth (kills real governance theater, surgical)

- **P0-a. Wire `mcp_manifest_lock` into `aizee_mcp` server startup.** security-auditor rule 15 requires "tool definitions hash-pinned and re-validated on refresh". The module exists (327 LOC), is constructed, and is never called. Plan: on server boot, hash all registered tool definitions; first run writes `brain/mcp_manifest.lock`, subsequent runs verify and log/block on drift. Wires 1 constructed-only service into a real call path.
- **P0-b. Wire `hallucination_detector` + `stale_api_detector` into the `lint_python` MCP tool** as advisory findings alongside AstryxLinter results. One call site, two more constructed-only services made real, direct value to IDE agents pre-write.
- **P0-c. Scan hygiene:** add justified `aizee-scan: ignore` marker on `_child.py` exec (sandbox-by-design, documented) and add `logging.debug` context to the two empty excepts in `executor.py` reader threads.

### P1 — Subtract (startup + honest surface)

- **P1-a. Lazy `runtime/__init__.py` via PEP 562 `__getattr__`.** Convert the ~250 eager `from runtime.x import Y` re-exports to a lazy export table. `import runtime` 0.46s → ~0.02s; every CLI command and test worker benefits. `from runtime import X` keeps working unchanged.
- **P1-b. Lazy-construct the remaining 17 constructed-only services** (first-access `kernel.<name>` via `__getattr__` or explicit `get_<svc>()` accessors). `Kernel()` 0.59s → target <0.2s; `constructed_only` doctor table empties by definition.
- **P1-c. Orphan decision point (needs your call):**
  - **Option A — Quarantine:** move the 25 orphans + their tests to `runtime/experimental/` — still tested, clearly non-production, doctor reports "experimental".
  - **Option B — Wire top-3 + delete rest:** wire `output_gate` (chat output path), `learning_loop`/`skill_lifecycle` synergy, `service_catalog` (skill/workflow discovery) if they earn a call site; delete the other ~22 + tests (~7.6k LOC gone, suite faster, coverage honest).
  - **Option C — Delete all 25 + tests.** Maximum debt destruction; the code stays in git history if ever needed.

### P2 — Polish (small, real DevEx wins)

- **P2-a. Expose `doctor` + `security_scan` as MCP tools** (`aizee_mcp/tools/audit_tools.py`, ~60 LOC). IDE agents gain self-audit capability — the wiring table and OWASP scan become reachable pre-write.
- **P2-b. Auto-compact Memory.md:** `aizee memory ingest` runs `compact_memory(dry_run=False)` when Memory.md >500 lines. Closes the last open "auto-truncation" item.

### Discarded by the Ponytail filter
Wholesale god-class splits (F3 — medium-risk, low immediate value; revisit when a class next needs surgery); external vector DB / Postgres / Redis; LLM-judge (L3) live wiring (no key dependency allowed); new dashboard UI; spec-converge CI (no `specs/` dir exists in this repo).

## 4. Execution plan (if approved)

| Order | Item | Est. blast radius | Verify |
|---|---|---|---|
| 1 | P0-c scan markers + except logs | 3 lines | `aizee security scan` clean |
| 2 | P0-a mcp_manifest_lock wiring | `aizee_mcp/aizee_server.py` + lock file path | new tests; tamper → deny |
| 3 | P0-b lint_python advisory wiring | `tools/policy_tools.py` | new tests; findings present |
| 4 | P1-a lazy `__init__` | `runtime/__init__.py` | import-time measure; full suite |
| 5 | P1-b lazy service construction | `runtime/kernel.py` | Kernel() <0.2s; doctor table empty |
| 6 | P1-c orphan strategy | 25 modules + ~60 test files | suite green; doctor honest |
| 7 | P2-a MCP audit tools | new file + registration | tool list + smoke test |
| 8 | P2-b auto-compact hook | `aizee_cli.py` | Memory.md >500 → compacted |

**Gates after execution:** `ruff check .` · `mypy` (strict) · targeted tests per change · `aizee test --full` + `python eval/harness.py` before done. No commit without approval.

## 5. Decisions needed from you

1. **Orphan strategy (P1-c):** A (quarantine), B (wire-3 + delete-rest), or C (delete-all)?
2. **Scope:** run all of P0-P2, or a subset (e.g., P0+P1 only)?
3. **P2-a MCP tools:** new tools mean MCP surface 39→41 — OK?
