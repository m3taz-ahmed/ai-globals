# Phase 7: Security Audit & Hardening

> [!IMPORTANT]
> **Trigger:** When the user requests a "Security Audit", "Security Hardening", or "Penetration Test Prep".
> This protocol runs a systematic security review from dependency analysis to infrastructure hardening.

## 1. Dependency Analysis
- **Composer Audit:** Run `composer audit` to check for known vulnerabilities in PHP packages.
- **NPM Audit:** Run `npm audit` for JS dependencies. Use `npm audit fix` for auto-fixable issues.
- **SCA Tools:** Use `Snyk`, `GitHub Dependabot`, or `SonarQube` for continuous monitoring.
- **Outdated Check:** Run `composer outdated` / `npm outdated` to identify packages with pending security patches.
- **License Compliance:** Verify no GPL-licensed packages in proprietary projects (use `composer licenses` or `license-checker`).

## 2. Code Review for Security
Audit the codebase for:
- **Mass Assignment:** Check for `$guarded = []` or missing `$fillable`. Use `grep -r "guarded" app/Models/`.
- **Raw Queries:** Search for `DB::raw`, `DB::select`, or string concatenation in queries.
- **XSS:** Verify all user output is escaped or sanitized (`{{ }}` in Blade, not `{!! !!}` with user input).
- **Auth Gates:** Ensure no routes are missing middleware or policy checks. Cross-reference `routes/` with `app/Policies/`.
- **File Uploads:** Check upload endpoints for type validation, size limits, and storage outside web root.
- **Encryption:** Verify sensitive fields use Laravel's `encrypt()` cast or database-level encryption.
- **CSRF:** Confirm CSRF protection is not disabled on any POST/PUT/DELETE routes without documented justification.

## 3. Authentication & Authorization Audit
- **Password Policy:** Verify `Password::defaults()` enforces minimum length (12+), complexity rules.
- **2FA:** Check if two-factor authentication is available and enforced for admin users.
- **Session Security:** Verify `Session::regenerate()` is called after login. Check `session.secure` and `session.httponly` config.
- **JWT Rotation:** If using JWT, verify token rotation and revocation mechanisms are implemented.
- **Brute Force Protection:** Confirm `ThrottleRequests` middleware is applied to all auth routes.
- **Privilege Escalation:** Test that non-admin users cannot access admin routes or Filament panels.

## 4. Infrastructure Scan
- **ENV Check:** Ensure no secrets are hardcoded or committed. Run `git log -p | grep -i "password\|api_key\|secret"` to scan history.
- **Permissions:** Verify file system permissions (`storage` and `bootstrap/cache` writable but not world-readable).
- **SSL:** Ensure all traffic is forced over HTTPS (`AppServiceProvider` forceScheme or middleware).
- **Headers:** Verify security headers: `X-Frame-Options`, `X-Content-Type-Options`, `Content-Security-Policy`, `Strict-Transport-Security`.
- **Debug Mode:** Confirm `APP_DEBUG=false` in production. Never expose debug pages to end users.
- **CORS:** Verify `config/cors.php` does not use `*` for `allowed_origins`.

## 5. Data Protection Audit
- **PII Handling:** Identify all columns storing personal data (email, phone, national ID). Verify encryption at rest.
- **Data Retention:** Check if data retention policies exist and are enforced (automated purging of expired data).
- **Export Controls:** Verify data export endpoints respect tenant boundaries and authorization.
- **Backup Security:** Confirm database backups are encrypted and access-controlled.

## 6. Remediation Priority
1. **Critical (Patch Immediately):** Active exploits, exposed secrets, authentication bypasses.
2. **High (Next Sprint):** Known CVEs without active exploits, authorization gaps, missing input validation.
3. **Medium (Plan & Schedule):** Suboptimal configurations, missing headers, outdated dependencies without known exploits.
4. **Low (Document & Monitor):** Code quality improvements with security implications, defense-in-depth recommendations.

## 7. Audit Report Template
```markdown
# Security Audit Report — [Date]

## Critical Findings (Action Required)
- [CRITICAL] [Finding with affected file/endpoint]

## High Priority Findings
- [HIGH] [Finding with remediation plan]

## Medium/Low Recommendations
- [MEDIUM/LOW] [Recommendation]

## Compliance Status
- OWASP Top 10: [Pass/Fail per category]
- PCI DSS (if applicable): [Status]
- Data Protection: [Status]
```
