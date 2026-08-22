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
        ├── Runtime Modules (runtime/) — 88 governance modules
        │     ├── policy.py, guardian.py, probity.py — gates
        │     ├── budget.py — token/cost/call tracking
        │     ├── audit.py — hash-chained append-only audit log
        │     ├── crypto.py — Fernet at-rest encryption
        │     ├── migrations.py — SQLite schema versioning
        │     ├── observability.py — Sentry + Prometheus
        │     ├── telemetry.py, tracing.py — telemetry + spans
        │     └── persona.py, skill_resolver.py — persona/skill detection
        ├── MCP Server (aizee_mcp/) — 35 tools via FastMCP
        └── Memory (memory/) — SQLite + FTS5 + vector store
```

### Key Directories

| Path | Purpose |
|------|---------|
| `runtime/` | Kernel + 88 governance modules |
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
2. Sentry auto-initializes on kernel startup via `runtime/observability.py`.
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
| `aios_actions_total` | Counter | action, decision |
| `aios_workflows_total` | Counter | status |
| `aios_sagas_total` | Counter | status |
| `aios_guardian_denials` | Counter | rule |
| `aios_probity_violations` | Counter | rule |
| `aios_budget_remaining` | Gauge | scope |

## Alert Configuration

### Recommended Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| Guardian denials spike | `rate(aios_guardian_denials[5m]) > 10` | Warning |
| Probity violations | `aios_probity_violations > 0` | Critical |
| Budget exhausted | `aios_budget_remaining == 0` | Warning |
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
