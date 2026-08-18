# aiZee — Operations Runbook

Operational reference for incident response, troubleshooting, and emergency procedures.

## Common Incidents

### Database Corruption (`brain/memory.db`)

**Symptoms:** `sqlite3.DatabaseError`, `database disk image is malformed`, memory queries fail.

**Resolution:**
1. Stop all aiZee processes (CLI, MCP server, dashboard).
2. Back up the corrupt DB: `Copy-Item brain\memory.db brain\memory.db.corrupt`
3. Restore from latest backup:
   ```powershell
   python scripts/restore_brain.py --from "<root>\backups\aizee-backup-<latest>"
   ```
4. If no backup exists, rebuild from scratch:
   ```powershell
   Remove-Item brain\memory.db
   aizee memory ingest   # rebuilds indexes from rules/tech-stack/workflows
   ```
5. Verify: `aizee doctor` — check `vector index` shows `ok`.
6. Run `python scripts/migrate.py` to reapply schema migrations.

### Out of Memory (OOM)

**Symptoms:** Python process killed, `MemoryError`, dashboard returns 500.

**Resolution:**
1. Check memory DB size: `Get-Item brain\memory.db | Select-Object Length`
2. If >500MB, run vacuum: `sqlite3 brain\memory.db "VACUUM;"`
3. Prune old telemetry/audit logs (see Log Rotation below).
4. Reduce `SENTRY_TRACES_SAMPLE_RATE` to `0.01` to lower overhead.
5. Restart MCP server: `aizee sync`.
6. If vector index is large, clear and rebuild: delete `memory/vector.index`, then `aizee memory ingest`.

### Disk Full

**Symptoms:** `OSError: No space left on device`, writes fail, backups fail.

**Resolution:**
1. Identify large directories:
   ```powershell
   Get-ChildItem -Recurse | Sort-Object Length -Descending | Select-Object -First 20
   ```
2. Prune old backups: keep only the 3 most recent in `backups/`.
3. Rotate logs (see below).
4. Clear `graphify-out/` if disk critical (regenerable via `graphify update .`).
5. Clear `state/spans.jsonl.*` rotated files.
6. Verify free space, then `aizee doctor`.

## Troubleshooting

### `aizee doctor`

Run `aizee doctor` from the OS root. It checks 20+ health items and prints a table.
Any `missing` status indicates a problem.

| Check | Fix |
|-------|-----|
| `encryption key set` = missing | Set `AIOS_ENCRYPTION_KEY` env var or `state/.encryption_key` auto-generates |
| `encryption fernet valid` = missing | Key is malformed — regenerate with `Fernet.generate_key()` |
| `vector index` = missing | Run `aizee memory ingest` |
| `guardian.yaml (load error)` | Fix YAML syntax in `runtime/policies/guardian.yaml` |
| `probity.yaml (load error)` | Fix YAML syntax in `runtime/policies/probity.yaml` |
| `global mcp config` = missing | Run `aizee sync` to register MCP servers |
| `pip: <pkg>` = missing | `pip install <pkg>` — see `pyproject.toml` for deps |

### Log Locations

| Log | Path | Rotation |
|-----|------|----------|
| Audit log | `state/audit.log` | Auto at 100MB, keeps 5 rotated |
| Telemetry | `state/telemetry.jsonl` | Auto at max size, keeps rotated copies |
| Traces/spans | `state/spans.jsonl` | Manual — delete old files |
| Chat sessions | `state/chat_sessions.jsonl` | Manual |
| Dashboard | stdout / Sentry | N/A |

### Common Errors

- **`PolicyDeniedError`** — Action blocked by policy/guardian. Check `runtime/policies/` rules.
- **`BudgetExceededError`** — Token/cost budget exhausted. Check `state/budget.json` or raise limits.
- **`Invalid encryption key or corrupted data`** — `AIOS_ENCRYPTION_KEY` mismatch. Restore correct key or decrypt from backup with old key first.
- **`AIOS_ENCRYPTION_KEY is not set`** — File is encrypted but no key configured. Set the env var.
- **`config.discover_root()` fails** — Set `AIZEE_ROOT` env var explicitly.

## Emergency Procedures

### Restore from Backup

```powershell
# 1. Stop all aiZee processes
# 2. List available backups
python scripts/restore_brain.py --list

# 3. Full restore (overwrite) from specific backup
python scripts/restore_brain.py --from "<root>\backups\aizee-backup-2026-01-15-103000"

# 4. Or smart merge (only newer backups since last checkpoint)
python scripts/restore_brain.py --auto

# 5. Verify
aizee doctor
```

Backups contain: `memory/`, `state/`, `brain/`, `graphify-out/`, `.env`.

### Rotate Encryption Key

1. **Decrypt all files with the OLD key:**
   ```powershell
   $env:AIOS_ENCRYPTION_KEY = "<old-key>"
   python -c "from pathlib import Path; from runtime.crypto import decrypt_file, is_encrypted; [decrypt_file(f) for f in Path('state').rglob('*.json') if is_encrypted(f)]"
   ```
2. **Generate a new key:**
   ```powershell
   python -c "from runtime.crypto import generate_key; print(generate_key())"
   ```
3. **Set the new key and re-encrypt:**
   ```powershell
   $env:AIOS_ENCRYPTION_KEY = "<new-key>"
   # Re-encryption happens automatically on next write; or force:
   python -c "from pathlib import Path; from runtime.crypto import encrypt_file; [encrypt_file(f) for f in Path('state').rglob('*.json')]"
   ```
4. **Update `.env`** with the new `AIOS_ENCRYPTION_KEY` value.
5. **Take a fresh backup** immediately: `python scripts/backup_brain.py`
6. **Verify:** `aizee doctor` — `encryption fernet valid` must show `ok`.

> **Warning:** If the old key is lost, encrypted files in `state/` cannot be recovered. Always store the key securely before rotation.
