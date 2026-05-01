# Phase 5: Code Review Protocol

## 1. REVIEW SCOPE & MINDSET
- **Purpose:** Code review is a quality gate, not a gatekeeping exercise. Focus on correctness, security, performance, and maintainability.
- **Scope:** Review every line that changed. Understand the context — read surrounding code, not just the diff.
- **Tone:** Constructive and specific. "This could cause N+1 — use `with('relation')` here" not "This is wrong".

## 2. SECURITY-FIRST REVIEW
Priority checks (block the PR if any fail):
- [ ] No raw SQL queries or string concatenation in database operations.
- [ ] No secrets, API keys, or credentials in code or comments.
- [ ] All user inputs validated via FormRequest or equivalent.
- [ ] Authorization checks (Policies/Gates) present for all state-changing actions.
- [ ] No `$guarded = []` or unprotected mass assignment.
- [ ] File uploads validated for type, size, and stored outside web root.

## 3. PERFORMANCE REVIEW
- [ ] No N+1 queries — all relationship access uses eager loading.
- [ ] Database queries are bounded (pagination, limits, chunking for batch operations).
- [ ] No unnecessary loops that could be replaced with Collection methods or SQL.
- [ ] Heavy operations are queued, not executed synchronously in HTTP requests.
- [ ] Caching is applied for expensive, rarely-changing data.

## 4. CODE QUALITY REVIEW
- [ ] Follows the project's naming conventions (PSR-12 for PHP, project-specific for JS).
- [ ] Functions/methods are focused — one responsibility, reasonable length (<30 lines preferred).
- [ ] No dead code, commented-out blocks, or `TODO` without a linked ticket.
- [ ] Error handling is explicit — no empty catch blocks, no `@` suppression.
- [ ] Tests exist and meaningfully cover the new behavior.

## 5. ARCHITECTURE REVIEW
- [ ] Changes align with established patterns (Service-Repository, thin controllers).
- [ ] No new dependencies added without documented justification.
- [ ] Database schema changes include proper migrations, indexes, and foreign keys.
- [ ] API changes are backward-compatible or versioned.

## 6. REVIEW ETIQUETTE
- **Author:** Keep PRs small (<400 lines). Write a clear description. Self-review before requesting review.
- **Reviewer:** Review within 24 hours. Distinguish between "must fix" (blocking) and "suggestion" (non-blocking).
- **Resolution:** Author addresses all blocking comments. Non-blocking suggestions can be deferred with a ticket.
