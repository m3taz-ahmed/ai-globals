# API Design & Architecture Standards
> [!NOTE]
> Trigger: Designing new RESTful APIs, endpoints, webhooks, or JSON structures.

## 1. RESTful Naming Conventions
- **Nouns, Not Verbs:** Use plural nouns for resources (e.g., `/users`, `/invoices`). ⛔ `/getUsers` or `/createInvoice`.
- **Nesting:** Limit nesting to one level deep for relationships (e.g., `/users/{id}/posts`). For deeper structures, query the child directly (`/posts?user_id={id}`).
- **Case:** Use `kebab-case` for URLs and `snake_case` for JSON fields to align with database column naming.

## 2. HTTP Methods & Idempotency
- **GET:** Read only. Cacheable.
- **POST:** Create new resources or execute non-idempotent actions (e.g., `/invoices/calculate`).
- **PUT:** Complete replacement of a resource.
- **PATCH:** Partial update.
- **DELETE:** Remove a resource (soft or hard).
- **Idempotency:** POST requests that mutate state (payments, orders) must accept an `Idempotency-Key` header.

## 3. Response Format
- **Standard Envelope:**
  ```json
  {
    "data": { ... },
    "meta": { ... }
  }
  ```
- **Errors:** Must follow RFC 7807 (Problem Details for HTTP APIs).
  ```json
  {
    "error": {
      "code": "VALIDATION_FAILED",
      "message": "The given data was invalid.",
      "details": { "email": ["Invalid format."] }
    }
  }
  ```

## 4. Pagination
- **Cursor Pagination:** Preferred for high-frequency feeds, massive datasets (>1M rows), or infinite scroll (e.g., `?cursor=xyz`).
- **Offset Pagination:** Acceptable for admin panels or small datasets where users need to jump to specific pages (e.g., `?page=2&per_page=50`). Use `limit` instead of unbounded queries.

## 5. Versioning
- **URL Versioning:** e.g., `/api/v1/users`.
- **Breaking Changes:** Require a version bump (`v2`). Deprecate the old version gracefully using `Warning` headers.
