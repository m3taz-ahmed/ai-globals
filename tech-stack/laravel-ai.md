[TECH] laravel-ai
[OBJ] Laravel AI SDK (First-Party `laravel/ai`).
[RULES]
1. [REQ] Abstraction: Use `AI::text()`, `AI::embed()`. ⛔ DO NOT use provider-specific SDKs natively.
2. [REQ] Vector/RAG: PostgreSQL + `pgvector`. `whereVectorSimilarTo()`.
3. [REQ] Agents: Scaffold via `make:agent`. Enforce structured JSON schemas.
4. [PROHIBIT] Security: Treat LLM outputs as untrusted (validate schema). Use Passkey auth for AI admins.
5. [REQ] Rate Limits: SEPARATE Redis rate limiters (`RateLimiter::for('ai')`).
6. [REQ] Streaming: Use `->stream()` for real-time UI.
