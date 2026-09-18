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
  - web vulnerability
  - أمن الويب
  - ثغرات
personas:
  - SEC
  - DEV
tech_stack: []
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
14. [PROHIBIT] Never paste real secrets, tokens, or PII into code, tests, logs, or this checklist's examples.
15. [REQ] Pair with `security-auditor` for LLM/agent-layer threats (prompt injection, MCP CVEs, SARC) — this skill covers the web layer below it.

[WORKFLOWS]
1. Web feature review: identify inputs → validation allowlist → authN/authZ checks → output encoding → error handling → headers → run the relevant per-vuln rules above.
2. Pre-release audit: run `aizee_mcp` security tools + walk rules 1-13 for every new endpoint/upload/query → record findings in the audit trail.

---
Adapted from [VibeSec-Skill](https://github.com/BehiSecc/VibeSec-Skill) — Apache License 2.0. Condensed and restructured into aiZee rule format; see upstream for the full detailed checklist.
