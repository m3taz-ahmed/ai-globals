[WORKFLOW] 18-data-migration
[TRIGGER] data-migration
[OBJ] Database migrations, schema changes, and data transformation.
[RULES]
1. [REQ] Backup: Create a full backup/export before any migration.
2. [REQ] Rollback: Provide a tested rollback script or command sequence.
3. [REQ] Idempotency: Migration steps must be rerunnable without data corruption.
4. [REQ] Validation: After migration, validate row counts, schema, constraints, and sample data.
5. [REQ] Downtime: Prefer zero-downtime strategies; if not possible, document the maintenance window.
6. [PROHIBIT] No production migration without dry-run in a local or staging copy.
7. [REQ] Audit: Log the migration run, duration, and validation results to `state/audit.log`.
