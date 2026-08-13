# AI Global OS — Feature Documentation

**Version:** 4.22.1

This document describes the key features added or enhanced in AI Global OS v4.22.1.

## Table of Contents

1. [Approval Cache](#approval-cache)
2. [Hybrid Memory](#hybrid-memory)
3. [Rule Frontmatter](#rule-frontmatter)
4. [Fresh Context](#fresh-context)
5. [At-Rest Encryption](#at-rest-encryption)
6. [Schema Migrations](#schema-migrations)
7. [Observability](#observability)
8. [MCP Tool Modules](#mcp-tool-modules)
9. [Kernel Facade Pattern](#kernel-facade-pattern)

---

## Approval Cache

The `ApprovalCache` stores user-approved actions to avoid re-prompting for
the same action within a session.

**Location:** `runtime/approval_cache.py`

**How it works:**
- When an action requires approval (`decision: ask`), the kernel checks
  the approval cache first.
- If a matching approval exists (same action type + args hash), the action
  proceeds without re-prompting.
- Approvals are scoped to the current session and expire on session end.

**Usage:**
```python
from runtime.kernel import Kernel

k = Kernel(root)
# First call requires approval
result = k.act("Write", args={"path": "foo.txt"}, approved=True)
# Subsequent calls with same args use cached approval
result2 = k.act("Write", args={"path": "foo.txt"})
```

---

## Hybrid Memory

The memory store combines full-text search (FTS) and vector similarity
search for hybrid retrieval.

**Location:** `memory/store.py`, `memory/hybrid.py`

**How it works:**
- **FTS:** SQLite FTS5 index for keyword matching.
- **Vector:** Sentence-transformers embeddings with turbovec for
  cosine similarity search.
- **Hybrid:** `query_context` tool merges FTS + vector results, deduplicating
  by memory ID and annotating which mode matched.

**Usage:**
```python
from memory.store import MemoryStore

store = MemoryStore(root)
# FTS search
results = store.search("Python", kind="semantic", limit=10)
# Vector search
vector_results = store.search_vector("Python programming", k=5)
```

---

## Rule Frontmatter

Rules, skills, and workflows support YAML frontmatter for context-aware
filtering.

**Location:** `runtime/rule_frontmatter.py`

**Supported fields:**
- `paths:` List of glob patterns to match file paths.
- `personas:` List of persona names that should see this rule.
- `stack:` List of tech-stack packages that activate this rule.
- `always:` Boolean — if true, rule is always active regardless of context.

**Example:**
```yaml
---
paths:
  - "src/**/*.py"
personas:
  - python-engineer
stack:
  - pydantic
always: false
---
# Rule title

Rule body...
```

**Matching:** `matches_context(frontmatter, context)` checks if the
frontmatter matches the current context (file path, active personas,
detected stack).

---

## Fresh Context

The `fresh_context` flag resets session-scoped state for a single action.

**Location:** `runtime/kernel.py`

**How it works:**
- When `fresh_context=True` is passed to `act()`, `chat_message()`, or
  `run_workflow()`, the kernel:
  1. Resets the budget session scope (clears `session` usage).
  2. Creates a new chat session (for `chat_message`).
  3. Resets derived workflow context (for `run_workflow`).

**Usage:**
```python
# Normal call — uses existing session budget
k.act("Read", tokens=10)

# Fresh call — resets session budget before executing
k.act("Read", tokens=10, fresh_context=True)
```

---

## At-Rest Encryption

Sensitive state files can be encrypted at rest using Fernet (AES-128-CBC +
HMAC-SHA256).

**Location:** `runtime/crypto.py`

**Configuration:**
- Set `AIOS_ENCRYPTION_KEY` environment variable to a Fernet key.
- Generate a key with: `python -c "from runtime.crypto import generate_key; print(generate_key())"`

**Affected files:**
- `state/budget.json` — encrypted when key is set.

**Behavior:**
- When key is set: files are encrypted with a magic prefix (`AIOS_ENC:`).
- When key is not set: files are stored in plaintext (backward compatible).
- Encrypted files cannot be read without the key.

---

## Schema Migrations

A lightweight migration framework tracks and applies schema changes to
the SQLite memory database.

**Location:** `runtime/migrations.py`

**How it works:**
- A `_schema_version` table tracks the current schema version.
- Migrations are registered with `@migration(from_version)` decorator.
- `MigrationRunner.run_migrations()` applies pending migrations.
- `backup_database()` creates timestamped backups with retention.

**Usage:**
```python
from runtime.migrations import MigrationRunner, backup_database
from pathlib import Path

runner = MigrationRunner(Path("brain/memory.db"))
version = runner.run_migrations()
backup_database(Path("brain/memory.db"), Path("backups"), max_backups=5)
```

---

## Observability

Optional Sentry integration and Prometheus metrics export.

**Location:** `runtime/observability.py`

**Sentry:**
- Set `SENTRY_DSN` to enable error tracking.
- Set `SENTRY_TRACES_SAMPLE_RATE` for performance monitoring (default: 0.1).
- Set `SENTRY_ENVIRONMENT` (default: `production`).

**Prometheus:**
- `format_metrics(kernel)` returns Prometheus exposition text.
- Available via the `get_metrics` MCP tool.
- Metrics: `aios_workflows_total`, `aios_rules_total`, `aios_budgets_total`,
  `aios_budget_tokens_total`, `aios_budget_calls_total`.

---

## MCP Tool Modules

The MCP server (`aios_mcp/aios_server.py`) is now a thin facade that
delegates tool registration to specialized modules:

| Module | Tools |
|--------|-------|
| `tools/memory_tools.py` | search_memory, search_memory_vector, query_context, ingest_memory, get_related_memories, add_memory, invalidate_memory, build_schema_graph |
| `tools/workflow_tools.py` | query_rules, run_workflow, list_rules, get_rule, list_workflows, get_workflow, compile_rule_files, run_mcp_plan |
| `tools/policy_tools.py` | check_policy, analyze_budget, run_guardian_check, get_metrics, get_os_status, list_capabilities, lint_python |
| `tools/context_tools.py` | get_tech_stack, search_skills, get_changelog, get_active_context |
| `tools/common.py` | Shared helpers: kernel(), memory(), is_safe_name(), resolve_path() |

---

## Kernel Facade Pattern

The runtime kernel (`runtime/kernel.py`) is now a facade that delegates to
specialized manager modules:

| Manager | Responsibility |
|---------|---------------|
| `managers/policy_manager.py` | Policy evaluation, guardian, probity, budget checks |
| `managers/workflow_manager.py` | Workflow execution, saga orchestration |
| `managers/agent_manager.py` | Agent spawning, process pool management |
| `managers/chat_manager.py` | Chat session lifecycle |

**Benefits:**
- Each manager is independently testable.
- Kernel.py is under 300 lines (was 800+).
- Clear separation of concerns.
- Backward-compatible API — all existing methods still work.
