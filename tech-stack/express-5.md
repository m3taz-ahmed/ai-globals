[TECH] Express 5
[OBJ] Minimal Node.js web framework with async error handling, improved router, and modern path-matching semantics.
[RULES]
1. [REQ] Use `express.Router()` to modularize routes; mount with `app.use("/api/v1", router)` — never define all routes on the top-level `app`.
2. [REQ] Use async route handlers with a wrapper (`asyncHandler`) or Express 5's native promise-rejection forwarding: rejected promises in middleware are automatically caught and forwarded to the error handler.
3. [REQ] Define a single error-handling middleware as the last `app.use((err, req, res, next) => {...})` — it must have exactly 4 parameters.
4. [REQ] Use the new path-matching syntax: `:name` for params, `*` replaced by `*splat` or named wildcards; Express 5 uses `path-to-regexp` v8 — review migrated routes for breaking changes.
5. [REQ] Validate and sanitize all input with a validation library (Zod, Joi, or express-validator); never trust `req.body`, `req.query`, or `req.params` directly.
6. [REQ] Set security headers with `helmet()` middleware; configure CSP, HSTS, and X-Frame-Options explicitly.
7. [REQ] Use `express.json()` and `express.urlencoded({ extended: true })` with a `limit` to prevent oversized payload DoS.
8. [REQ] Implement rate limiting with `express-rate-limit` per route or globally; store counts in Redis for multi-instance deployments.
9. [REQ] Use `req.params` (path), `req.query` (URL query), `req.body` (parsed body) consistently; never mix them in controller logic.
10. [REQ] Structure the project as: `src/routes/`, `src/controllers/`, `src/services/`, `src/middleware/`, `src/models/` — controllers should be thin, delegating to services.
11. [REQ] Use `process.on("unhandledRejection")` and `process.on("uncaughtException")` handlers to log and gracefully shut down; never let the process run in an inconsistent state.
12. [REQ] Run behind a reverse proxy (Nginx / Caddy) and set `app.set("trust proxy", 1)` to trust `X-Forwarded-*` headers.
13. [REQ] Use `dotenv` for environment variables and validate required vars at startup with a schema (Zod / envalid).
14. [PROHIBIT] Never use removed methods: `app.del()` (use `app.delete()`), `res.json(status, obj)` (use `res.status(n).json(obj)`), `res.send(status)` — Express 5 removes all deprecated signatures.
15. [PROHIBIT] Never use synchronous blocking calls (`fs.readFileSync`, `crypto.pbkdf2Sync`) in request handlers — use async equivalents.
[COMPAT]
- v5.0: Node.js 18+, path-to-regexp v8, native async error forwarding, removed deprecated methods, no `res.send(status)`.
- v5.1: Node.js 18+, bug fixes, improved `req.query` parsing.
[REFS]
- https://expressjs.com/en/5x/api.html
- https://github.com/pillarjs/path-to-regexp
- https://github.com/helmetjs/helmet
