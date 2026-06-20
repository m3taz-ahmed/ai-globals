[TECH] api-design-standards
[OBJ] RESTful API Design & Architecture.
[RULES]
1. [REQ] URLs: Plural nouns (e.g., `/invoices`). `kebab-case` URLs, `snake_case` JSON. Max 1 level nesting (`/users/{id}/posts`).
2. [REQ] Methods: GET (Read), POST (Create/Action), PUT (Replace), PATCH (Update), DELETE (Remove).
3. [REQ] Idempotency: Mutating POSTs require `Idempotency-Key` header.
4. [REQ] Envelope: `{ "data": {}, "meta": {} }`. Errors must follow RFC 7807 (Problem Details).
5. [REQ] Pagination: Cursor for high-frequency/large datasets. Offset + Limit for admin panels.
6. [REQ] Versioning: URL versioning (`/api/v1/`). Gracefully deprecate old endpoints.
