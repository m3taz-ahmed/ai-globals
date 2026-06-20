[WORKFLOW] 06-maintenance
[OBJ] System Maintenance & Global Optimization.
[RULES]
1. [REQ] Trigger: User requests "Maintenance Audit" or "Global Optimization".
2. [REQ] Pre-Sync: Reload `rules/` folder. Sync tech stack via `composer.json`.
3. [REQ] Audit: Recursively audit workspace for SOLID, OWASP, N+1, PHPDoc completeness.
4. [REQ] Optimization: Fix low-risk immediately. Propose medium-risk. Flag high-risk to user.
5. [REQ] Gap Fill: Add missing workflows, `.editorconfig`, test coverage.
6. [REQ] Report: Update `state/MEMORY.md` and `state/CHANGELOG.md` with findings.
