# aiZee — SRE Onboarding

Quick-start guide for site reliability engineers managing aiZee in production.

## Architecture Overview

aiZee is a sovereign AI engineering control plane with a layered design:

```
CLI (aizee_cli.py)
  └── Kernel (runtime/kernel.py) — facade
        ├── Managers (runtime/managers/)
        │     ├── PolicyManager   — policy + guardian + probity gates
        │     ├── WorkflowManager — saga orchestration + workflows
        │     ├── AgentManager    — agent pool + personas
        │     └── ChatManager     — chat sessions
        ├── Runtime Modules (runtime/) — 85 governance modules
        │     ├── policy.py, guardian.py, probity.py — gates
        │     ├── budget.py — token/cost/call tracking
        │     ├── audit.py — hash-chained append-only audit log
        │     ├── crypto.py — Fernet at-rest encryption
        │     ├── migrations.py — SQLite schema versioning
        │     ├── telemetry.py, tracing.py — telemetry + spans + Prometheus
        │     ├── sentry_init.py — Sentry auto-init
        │     └── persona.py, skill_resolver.py — persona/skill detection
        ├── MCP Server (aizee_mcp/) — 36 tools via FastMCP
        └── Memory (memory/) — SQLite + FTS5 + vector store
```

### Key Directories

| Path | Purpose |
|------|---------|
| `runtime/` | Kernel + 85 governance modules |
| `runtime/managers/` | Policy/Workflow/Agent/Chat managers |
| `aizee_mcp/` | MCP server + tools |
| `memory/` | SQLite DB, FTS5, vector index |
| `state/` | Runtime state, audit log, telemetry, spans, budgets |
| `brain/` | Agent brain state, learned patterns, `memory.db` |
| `scripts/` | Backup, restore, migrate utilities |
| `runtime/policies/` | YAML policy files (guardian, probity, default) |
| `backups/` | Timestamped brain backups |

### Runtime Gate (every action)

Every action passes through: **Probity → Guardian → Policy → Budget** → decision (ALLOW / DENY / ASK).

## Monitoring Setup

### Dashboard (Web UI)

The dashboard server (`dashboard/server.py`) provides real-time monitoring of agents, metrics, and budget.

**Setup:**
1. Set `AIZEE_DASHBOARD_TOKEN` in `.env` (required for production).
2. Start the dashboard server (binds to `AGENT_OS_HOST`, default `127.0.0.1`).
3. Access at `http://127.0.0.1:8080`.
4. Health check: `GET /api/health` → `{"ok": true, "root": "...", "version": "..."}`

### Sentry (Error Tracking)

**Setup:**
1. Set in `.env`:
   ```
   SENTRY_DSN=https://<key>@sentry.io/<project>
   SENTRY_TRACES_SAMPLE_RATE=0.1
   SENTRY_ENVIRONMENT=production
   ```
2. Sentry auto-initializes on kernel startup via `runtime/telemetry.py`.
3. Exceptions captured via `capture_exception()`, messages via `capture_message()`.
4. Verify: check Sentry dashboard for incoming events after deployment.

### Health Checks

| Method | Command | Frequency |
|--------|---------|-----------|
| Full health | `aizee doctor` | Every deployment + daily cron |
| Dashboard | `GET /api/health` | Continuous (uptime monitor) |
| Audit chain | `AuditLogger.verify_chain()` | Weekly integrity check |
| Encryption | `aizee doctor` (encryption checks) | After key rotation |

### Prometheus Metrics

Metrics are registered in `Kernel._build_metrics()` and exported via `prometheus_export()`:

| Metric | Type | Labels |
|--------|------|--------|
| `aizee_actions_total` | Counter | action, decision |
| `aizee_workflows_total` | Counter | status |
| `aizee_sagas_total` | Counter | status |
| `aizee_guardian_denials` | Counter | rule |
| `aizee_probity_violations` | Counter | rule |
| `aizee_budget_remaining` | Gauge | scope |

## Alert Configuration

### Recommended Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| Guardian denials spike | `rate(aizee_guardian_denials[5m]) > 10` | Warning |
| Probity violations | `aizee_probity_violations > 0` | Critical |
| Budget exhausted | `aizee_budget_remaining == 0` | Warning |
| Dashboard down | `/api/health` fails 3x consecutive | Critical |
| Encryption key missing | `aizee doctor` encryption check fails | Critical |
| Disk usage | `> 90%` on aiZee root volume | Warning |
| Audit chain broken | `verify_chain()` returns False | Critical |

### Sentry Alert Routing

Configure in Sentry project settings:
- **Probity violations** → page on-call immediately (Critical).
- **Guardian denials** → notify SRE channel (Warning).
- **Budget exceeded** → notify team channel (Info).

## Common Tasks

### Backup

```powershell
# Full backup to default location (<root>/backups/)
python scripts/backup_brain.py

# Custom destination
python scripts/backup_brain.py --dest D:\backups
```
Backs up: `memory/`, `state/`, `brain/`, `graphify-out/`, `.env`.

### Restore

```powershell
# List available backups
python scripts/restore_brain.py --list

# Full restore from specific backup
python scripts/restore_brain.py --from "<root>\backups\aizee-backup-<timestamp>"

# Smart merge (only newer backups since last checkpoint)
python scripts/restore_brain.py --auto
```

### Log Rotation

Audit and telemetry logs auto-rotate at 100MB (keep 5 copies). For manual cleanup:

```powershell
# Check log sizes
Get-ChildItem state\*.log, state\*.jsonl | Select-Object Name, Length

# Remove old rotated spans
Remove-Item state\spans.jsonl.* -ErrorAction SilentlyContinue

# Vacuum SQLite to reclaim space
sqlite3 brain\memory.db "VACUUM;"
```

### Migration

```powershell
# Check if migrations are pending
python scripts/migrate.py --check

# Dry-run (show what would change)
python scripts/migrate.py --dry-run

# Apply migrations
python scripts/migrate.py

# After migration, always verify
aizee doctor
```

Migrations track version in `.aizee-version` and target version in `pyproject.toml`. Schema migrations run on `brain/memory.db` via `runtime/migrations.py`.

### Budget Finalization Reserve

The `BudgetManager` supports a `finalization_reserve` field (0.0–0.5) that reserves
a fraction of the token/cost budget for the final response. This prevents the agent
from exhausting the budget mid-task and being unable to produce a summary.

```python
# In Kernel config or policy:
budget = BudgetManager(max_tokens=10000, finalization_reserve=0.2)
# effective_max_tokens = 8000 (80% for work, 20% reserved for final response)
# would_exceed() checks against effective_max_tokens, not max_tokens
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `finalization_reserve` | float | 0.0 | Fraction [0.0, 0.5] reserved for final response |
| `effective_max_tokens` | int | `max_tokens * (1 - reserve)` | Usable tokens for work |
| `effective_max_cost` | float | `max_cost * (1 - reserve)` | Usable cost for work |
| `would_exceed(tokens)` | bool | — | Pre-flight check against effective limits |

### Kill Switch

The `Guardian` evaluates `KillSwitchRule` objects **first** (before any guardrail),
providing a hard-stop mechanism that cannot be overridden by policy. If any kill
switch triggers, a `KillSwitchError` is raised immediately.

```python
from runtime.guardian import KillSwitchRule, KillSwitchError

# Define kill switches (evaluated in order, first match wins)
rules = [
    KillSwitchRule(name="cost-ceiling", cost_ceiling=10.0),
    KillSwitchRule(name="file-touched-limit", file_touched_count=500),
    KillSwitchRule(name="tool-call-limit", tool_call_count=1000),
    KillSwitchRule(name="time-limit", time_limit_seconds=3600),
]
# Guardian.authorize() checks these before any policy/probity gate
```

| Rule Field | Type | Description |
|------------|------|-------------|
| `cost_ceiling` | float | Total cost in USD — kill if exceeded |
| `file_touched_count` | int | Max files touched in a single rollout |
| `tool_call_count` | int | Max tool calls in a single rollout |
| `time_limit_seconds` | int | Wall-clock time limit for the rollout |

### Dashboard Security

The dashboard (`dashboard/server.py`) runs on localhost by default. For production
deployments, set `AIZEE_DASHBOARD_TOKEN` to require authentication:

```powershell
# Development (loopback only, no token — default)
$env:AIZEE_DASHBOARD_HOST = "127.0.0.1"
$env:AIZEE_DASHBOARD_PORT = "7777"

# Production (require token)
$env:AIZEE_DASHBOARD_TOKEN = "aizee-<random-32-char-string>"
$env:AIZEE_DASHBOARD_HOST = "0.0.0.0"
```

| Env Var | Default | Description |
|---------|---------|-------------|
| `AIZEE_DASHBOARD_HOST` | `127.0.0.1` | Bind address (use `0.0.0.0` for external) |
| `AIZEE_DASHBOARD_PORT` | `7777` | HTTP port |
| `AIZEE_DASHBOARD_TOKEN` | _(none)_ | Bearer token for auth (required for non-loopback) |

> **Warning:** If `AIZEE_DASHBOARD_HOST` is set to a non-loopback address without
> `AIZEE_DASHBOARD_TOKEN`, the dashboard will refuse to start. This is a fail-closed
> security measure.
