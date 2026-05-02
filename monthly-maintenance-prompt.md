# Monthly Maintenance Audit Protocol
> **Frequency:** First week of every month | **Role:** Principal Chief Architect

## Purpose

Perform a structured monthly audit to catch regressions, dependency vulnerabilities, and performance degradation before they compound.

## Audit Checklist

### 1. Dependency Security
- [ ] Run `composer audit` â€” check for known vulnerabilities in PHP packages.
- [ ] Run `npm audit` â€” check for known vulnerabilities in Node.js packages.
- [ ] Run `composer outdated` / `npm outdated` â€” identify packages with pending updates.
- [ ] Review any critical/high severity advisories and create upgrade tickets.

### 2. Code Quality & Smells
- [ ] Review the latest major features added since last audit.
- [ ] Check for bloated controllers (>200 lines) â€” extract to Services.
- [ ] Identify slow queries using Telescope/Debugbar logs or slow query log.
- [ ] Scan for N+1 issues in new Eloquent code.
- [ ] Check for dead code, unused imports, and orphaned routes.

### 3. Database Optimization
- [ ] Review new tables/columns added â€” verify indexes exist for filtered/sorted columns.
- [ ] Recommend 3 specific indexes or query refactors based on slow query analysis.
- [ ] Check for missing foreign key constraints on new relationship columns.
- [ ] Verify migration rollbacks are properly defined for all new migrations.

### 4. Security Hardening
- [ ] Verify no secrets/credentials have been committed to git history.
- [ ] Check that all new API endpoints have proper authentication and authorization.
- [ ] Review CORS and CSP headers for any changes.
- [ ] Verify rate limiting is applied to new routes.

### 5. Infrastructure & Clean Up
- [ ] Identify unused files, legacy routes, or dead code for purging.
- [ ] Check disk usage of logs, temp files, and cached data.
- [ ] Verify queue workers and scheduled tasks are running correctly.
- [ ] Review error monitoring (Sentry/Bugsnag) for recurring unresolved errors.

### 6. Documentation Sync
- [ ] Verify `MEMORY.md` reflects all major changes from the past month.
- [ ] Update `CHANGELOG.md` if not already current.
- [ ] Check that inline documentation matches current implementation.

## Output Format

After completing the audit, produce a structured report:
```markdown
# Monthly Audit Report â€” [Month Year]

## Summary
[1-2 sentence overview]

## Critical Findings (Action Required)
- [Finding 1]
- [Finding 2]

## Recommendations (Non-Urgent)
- [Recommendation 1]

## Metrics
- Dependencies with updates: X
- Security advisories: X
- Slow queries identified: X
- Dead code files removed: X
```
