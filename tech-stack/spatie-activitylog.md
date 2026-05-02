# Spatie Laravel Activitylog Standards

## 1. MODEL CONFIGURATION
- **Trait:** Use `LogsActivity` trait on all business-critical models.
- **Log Options:** Define `getActivitylogOptions()` to specify which attributes to log and whether to log only changed attributes.

## 2. AUDIT TRAIL DATA
- **Context:** Use `tapActivity()` to add extra context like `request_id`, `ip_address`, or `user_agent`.
- **Formatting:** Use custom log names (e.g., `invoice_audit`, `user_auth`) for easier filtering.

## 3. CLEANUP
- **Pruning:** Implement the `Prunable` trait or use the `activitylog:clean` command to prevent the database from growing indefinitely. Default retention: 365 days.
