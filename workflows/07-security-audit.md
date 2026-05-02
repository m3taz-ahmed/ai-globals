# Phase 7: Security Audit & Hardening

## 1. STATIC ANALYSIS
- **Composer Audit:** Run `composer audit` to check for known vulnerabilities in PHP packages.
- **NPM Audit:** Run `npm audit` for JS dependencies.
- **SCA:** Use tools like `Snyk` or `GitHub Dependabot` for continuous monitoring.

## 2. CODE REVIEW FOR SECURITY
Audit the codebase for:
- **Mass Assignment:** Check for `$guarded = []` or missing `$fillable`.
- **Raw Queries:** Search for `DB::raw` or string concatenation in queries.
- **XSS:** Verify all user output is escaped or sanitized.
- **Auth Gates:** Ensure no routes are missing middleware or policy checks.

## 3. INFRASTRUCTURE SCAN
- **ENV Check:** Ensure no secrets are hardcoded or committed.
- **Permissions:** Verify file system permissions (e.g., `storage` and `bootstrap/cache` should be writable but not world-readable).
- **SSL:** Ensure all traffic is forced over HTTPS.

## 4. REMEDIATION
1. **Critical:** Patch immediately.
2. **High:** Schedule for the next sprint.
3. **Medium/Low:** Document and monitor.
