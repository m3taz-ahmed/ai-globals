---
name: web-security-checklist
description: Practical web-application security checklist — SSRF bypass variants, file upload magic bytes, XXE, JWT pitfalls, mass assignment, GraphQL hardening, input validation, output encoding. Complements aiZee's agent-focused security-auditor with implementation-level web vulns.
triggers:
  - web security
  - ssrf
  - file upload
  - xxe
  - jwt security
  - mass assignment
  - graphql security
  - input validation
  - output encoding
  - owasp
  - owasp 2025
  - csrf
  - open redirect
  - prototype pollution
  - ssti
  - template injection
  - command injection
  - clickjacking
  - redos
  - web vulnerability
  - أمن الويب
  - ثغرات
personas:
  - SEC
  - DEV
tech_stack:
  - appsec-hardening
license: Apache-2.0
source: https://github.com/BehiSecc/VibeSec-Skill
---

# Web Security Checklist

[OBJ] Implementation-level web vulnerability checks. Adapted from VibeSec-Skill (Apache-2.0, BehiSecc) — complements aiZee's `security-auditor` (agent/LLM-era threats) with classic web-app vulns. Use during code review, feature implementation, and security audits of web-facing code.

[RULES]
1. [REQ] SSRF: validate against ALL bypass forms — decimal/octal/hex IP literals (`2130706433`, `0177.0.0.1`, `0x7f.0.0.1`), IPv6 `::1`, `0.0.0.0`, `169.254.169.254` metadata, DNS rebinding (resolve-then-connect TOCTOU — pin the resolved IP), redirects to internal hosts, URL parser confusion (`@`, `#`, userinfo). Denylist private ranges AND resolve hostnames yourself.
2. [REQ] File upload: verify magic bytes server-side, not just extension/MIME header. Re-encode images. Store outside webroot with random names. Limit size + decompression bombs. Content-Disposition: attachment for user files.
3. [REQ] XXE: disable external entities + DTDs in every XML parser (language-specific flags — verify, don't assume defaults are safe). Prefer JSON where possible.
4. [REQ] JWT: pin the algorithm server-side (reject `alg: none` and RS256→HS256 confusion), enforce exp/iat/aud/iss, use strong secrets (>=32 bytes, from env not code), short TTL + rotation.
5. [REQ] Mass assignment: whitelist bindable fields (DTO/`$fillable`/`strong params`/`shouldIgnore`). Never pass raw request body to ORM `create`/`update`.
6. [REQ] GraphQL: enforce query depth + complexity limits, disable introspection in production, rate-limit + reject batching abuse, apply field-level auth (IDOR via node IDs).
7. [REQ] Input validation: server-side allowlists (type, length, format, range) on every input — params, headers, cookies, file content. Never trust client validation.
8. [REQ] Output encoding: context-aware escaping (HTML body vs attribute vs JS vs URL vs CSS). Auto-escaped templates only; audit any `|safe`/`dangerouslySetInnerHTML`/`v-html`.
9. [REQ] AuthN/session: HttpOnly+Secure+SameSite cookies, regenerate session on login, idle+absolute timeout, no tokens in URL.
10. [REQ] AuthZ: check object-level ownership on EVERY request (IDOR/BOLA) — not just "is logged in".
11. [REQ] Crypto: TLS everywhere, modern algorithms only (bcrypt/argon2 for passwords), no secrets in code/logs/client bundles.
12. [REQ] Headers: CSP, X-Content-Type-Options, X-Frame-Options/frame-ancestors, Referrer-Policy, HSTS.
13. [REQ] Error handling: no stack traces/SQL/framework versions to clients; log internally with correlation IDs.
14. [REQ] CSRF: state-changing requests verify Origin/Referer OR a CSRF token (synchronizer or double-submit) — SameSite cookies help but don't cover GET side-effects, subdomains, or legacy flows; never mutate state on GET.
15. [REQ] Command injection: pass arguments as arrays (`execve`-style lists, `subprocess` without `shell=True`), never string-concatenate user input into shell commands; allowlist binaries + arguments.
16. [REQ] SSTI: never render user input inside a template string — templates are code; user data goes in as data only. Audit `render_template_string`, `Template(user_input)`, `eval`-family, and expression-language surfaces.
17. [REQ] Open redirect: redirect targets allowlisted (relative paths or an explicit host list) — never `?next=`/`returnUrl` straight to `Location`; logouts, OAuth callbacks, and payment returns are the hot spots.
18. [REQ] Prototype pollution: reject `__proto__`/`constructor`/`prototype` keys in user JSON, merge via safe utilities or `Object.create(null)` records, schema-validate before deep-merging config; PHP analog = unserialize on user data.
19. [REQ] ReDoS & resource abuse: no nested-quantifier regex on user input; cap input length before regex; bound request sizes, decompression ratios (zip bombs), loop iterations over user counts.
20. [REQ] Fail-closed & exceptional conditions (OWASP 2025 A10): errors default to DENY on authz/validation — never `except: allow`; partial failures roll back (transactions); retry/circuit-breaker bounded; degraded mode defined per feature.
21. [REQ] OWASP 2025 mapping: A01 access control (incl. SSRF+BOLA/BFLA), A02 misconfiguration, A03 supply chain, A04 crypto, A05 injection, A06 insecure design, A07 authN, A08 integrity, A09 logging/alerting, A10 exceptional conditions — run reviews against the 2025 list, not 2021 memory.
22. [REQ] Python/desktop layer: `yaml.safe_load`, no `pickle` on untrusted bytes, `shell=False`, keyring not plaintext for desktop secrets, local UI servers bound to 127.0.0.1 with per-session tokens — full matrix in `tech-stack/appsec-hardening.md`.
23. [PROHIBIT] Never paste real secrets, tokens, or PII into code, tests, logs, or this checklist's examples.
24. [REQ] Pair with `security-auditor` for LLM/agent-layer threats (prompt injection, MCP CVEs, SARC) — this skill covers the web layer below it.

[WORKFLOWS]
1. Web feature review: identify inputs → validation allowlist → authN/authZ checks → output encoding → error handling → headers → run the relevant per-vuln rules above.
2. Pre-release audit: run `aizee_mcp` security tools + walk rules 1-13 for every new endpoint/upload/query → record findings in the audit trail.

---
Adapted from [VibeSec-Skill](https://github.com/BehiSecc/VibeSec-Skill) — Apache License 2.0. Condensed and restructured into aiZee rule format; see upstream for the full detailed checklist.
