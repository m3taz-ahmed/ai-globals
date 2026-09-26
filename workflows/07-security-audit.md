[WORKFLOW] 07-security-audit
[OBJ] Security review and infrastructure hardening.
[TRIGGER] security audit
[RULES]
0. [REQ] Execution layer first: run `aizee security scan <project-root> --json` — built-in OWASP-2025 rules + bandit/ruff-S/pip-audit/npm-audit/composer-audit/trivy when installed. Exit 1 = blockers present; fix or document before continuing.
1. [REQ] Dependencies: Run `composer audit`, `npm audit`. Check for outdated/GPL packages.
2. [REQ] Code Review: Check for mass assignment (`guarded = []`), raw SQL, unescaped XSS, missing auth gates, unprotected file uploads, missing CSRF.
3. [REQ] Auth Audit: Enforce 12+ char passwords. Ensure `Session::regenerate()`. Throttle auth routes. Check privilege escalation.
4. [REQ] Infra Scan: Scan history for secrets (`git log -p | grep secret`). Check file permissions, force HTTPS, security headers, `APP_DEBUG=false`, strict CORS.
5. [REQ] Data Protection: Encrypt PII at rest. Enforce data retention and backup encryption.
6. [REQ] Report: Output Audit Report (Critical/High/Med/Low) against OWASP Top 10.
