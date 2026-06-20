[TECH] spatie-activitylog
[OBJ] Spatie Laravel Activitylog Standards.
[RULES]
1. [REQ] Config: `LogsActivity` trait on critical models. Define `getActivitylogOptions()`.
2. [REQ] Audit: `tapActivity()` for context (`request_id`, `ip_address`). Custom log names.
3. [REQ] Cleanup: `Prunable` trait or `activitylog:clean` (365 days retention).
