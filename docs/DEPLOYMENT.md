# aiZee — Deployment Guide

Production deployment steps, environment configuration, health checks, and rollback procedures.

## Production Deployment

### Prerequisites

- Python 3.11+
- pip (latest)
- ~500MB free disk space (minimum)

### Steps

1. **Install aiZee:**
   ```powershell
   pip install aizee
   ```

2. **Set the root directory:**
   ```powershell
   $env:AIZEE_ROOT = "D:\.ai"
   ```
   Add to system environment variables for persistence.

3. **Copy `.env.example` to `.env` and configure:**
   ```powershell
   Copy-Item .env.example .env
   # Edit .env with production values
   ```

4. **Generate an encryption key (production):**
   ```powershell
   python -c "from runtime.crypto import generate_key; print(generate_key())"
   ```
   Set `AIOS_ENCRYPTION_KEY` in `.env` with the generated value.

5. **Run migrations:**
   ```powershell
   python scripts/migrate.py
   ```

6. **Sync MCP configs:**
   ```powershell
   aizee sync
   ```

7. **Verify deployment:**
   ```powershell
   aizee doctor
   ```
   All checks must show `ok`.

8. **Take an initial backup:**
   ```powershell
   python scripts/backup_brain.py
   ```

## Environment Configuration

### Required Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `AIZEE_ROOT` | Root directory of aiZee install | `D:\.ai` |
| `AIOS_ENCRYPTION_KEY` | Fernet key for at-rest encryption | (generated key) |

> If `AIOS_ENCRYPTION_KEY` is unset, aiZee auto-generates one at `state/.encryption_key`. For production, set it explicitly.

### Optional Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `AGENT_PROJECT_ROOT` | Active project root override | (auto-detected) |
| `AIOS_VERSION` | Version tag for Sentry releases | `unknown` |
| `AIZEE_DASHBOARD_TOKEN` | Auth token for dashboard access | (none — required for prod) |
| `AIZEE_DASHBOARD_ALLOW_NO_TOKEN` | Allow dashboard without token (dev only) | (unset) |
| `AIZEE_DASHBOARD_ORIGIN` | CORS origin whitelist | (none) |
| `AGENT_OS_DASHBOARD_MAX_BODY_SIZE` | Max request body size (bytes) | `1048576` |
| `AGENT_OS_DASHBOARD_RATE_LIMIT` | Rate limit requests per window | `120` |
| `AGENT_OS_DASHBOARD_RATE_WINDOW` | Rate limit window (seconds) | `60` |
| `AGENT_OS_HOST` | Dashboard bind host | `127.0.0.1` |
| `SENTRY_DSN` | Sentry error tracking DSN | (unset — disabled) |
| `SENTRY_TRACES_SAMPLE_RATE` | Sentry trace sample rate (0.0–1.0) | `0.1` |
| `SENTRY_ENVIRONMENT` | Sentry environment name | `production` |
| `PYTHONIOENCODING` | Force UTF-8 on Windows | `utf-8` |

### Plugin Credentials (optional)

| Variable | Purpose |
|----------|---------|
| `UPWORK_CLIENT_ID` / `UPWORK_CLIENT_SECRET` | Upwork plugin OAuth |
| `FREELANCER_OAUTH_TOKEN` | Freelancer plugin auth |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn plugin auth |
| `GRAPHIFY_WRAPPER_LOG` | Graphify wrapper log path |

## Health Check Procedures

### `aizee doctor`

Run from the OS root:
```powershell
aizee doctor
```
Checks 20+ items: root dirs, policies, modules, encryption, Python deps, vector index, MCP config, guardian/probity rules, capabilities, tech-stack detection. Exit code `0` = all healthy, `1` = issues found.

### Dashboard Health Endpoint

If the dashboard server is running:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/health"
```
Returns: `{"ok": true, "root": "...", "version": "..."}`

### Continuous Monitoring

- **Sentry:** Set `SENTRY_DSN` to capture exceptions and errors automatically.
- **Prometheus:** Metrics exported via `runtime/telemetry.py` collector and `runtime/tracing.py` spans.
- **Audit log:** Monitor `state/audit.log` for policy denials and probity violations.

## Rollback Procedures

### Rollback to Previous Version

1. **Take a backup of current state:**
   ```powershell
   python scripts/backup_brain.py
   ```

2. **Install the previous version:**
   ```powershell
   pip install aizee==<previous-version>
   ```

3. **Run migrations (if downgrade requires schema changes):**
   ```powershell
   python scripts/migrate.py --check   # see if migrations needed
   python scripts/migrate.py            # apply
   ```

4. **Restore state from backup taken before the upgrade:**
   ```powershell
   python scripts/restore_brain.py --from "<root>\backups\aizee-backup-<pre-upgrade>"
   ```

5. **Verify:**
   ```powershell
   aizee doctor
   aizee version
   ```

### Rollback After Failed Deployment

1. Stop all aiZee processes.
2. `pip install aizee==<last-known-good>`
3. Restore from the most recent good backup:
   ```powershell
   python scripts/restore_brain.py --list
   python scripts/restore_brain.py --from "<selected-backup>"
   ```
4. `aizee sync` to re-register MCP configs.
5. `aizee doctor` — all checks must pass.
6. Resume operations.
