[WORKFLOW] monthly-maintenance
[OBJ] Monthly Maintenance Audit Protocol.
[RULES]
1. [REQ] Trigger: First week of month.
2. [REQ] Security: `composer/npm audit` and `outdated`. Fix CVEs. Check history for secrets.
3. [REQ] Quality: Refactor bloated controllers (>200L). Scan for N+1, dead code, slow queries.
4. [REQ] Database: Verify indexes. Add 3 indexes based on slow logs. Check FKs and rollbacks.
5. [REQ] Infra: Purge dead code/logs. Verify queues/Sentry.
6. [REQ] Docs: Update `state/MEMORY.md`, `state/CHANGELOG.md`, inline docs.
7. [REQ] Report: Output Monthly Audit Report (Critical/Recommendations/Metrics).
