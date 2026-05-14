# Tech-Stack: Laravel AI SDK (First-Party)

> [!NOTE]
> **STATUS:** STABLE — First-party package, stable with Laravel 13. Ships as `laravel/ai`.
> **TRIGGER:** LOAD ON ALL LLM, EMBEDDING, VECTOR SEARCH, OR AI AGENT TASKS.

## 1. INSTALLATION & SETUP

```bash
composer require laravel/ai
php artisan vendor:publish --provider="Laravel\Ai\AiServiceProvider"
php artisan migrate  # creates ai_conversations, ai_messages tables
```

Configure API keys in `.env`:
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

## 2. PROVIDER-AGNOSTIC LLM INTERFACE

- Use `AI::text()`, `AI::image()`, `AI::audio()`, `AI::embed()` — the same API regardless of provider.
- Configure smart failover: primary provider → backup provider on rate-limit or failure.
- NEVER import provider-specific SDKs (e.g., `OpenAI\Client`) directly in application code. Always go through `laravel/ai`.

```php
// Provider-agnostic text generation
$response = AI::text('Summarize this contract.')->using('anthropic')->get();

// Streaming (SSE) — for real-time UI
return AI::text($prompt)->stream(); // Returns StreamedResponse
```

## 3. VECTOR SEARCH & RAG (Retrieval-Augmented Generation)

- **Database:** Use PostgreSQL + `pgvector` extension for storing and querying embeddings.
- **Embedding Generation:** Use `AI::embed($text)` for consistent embeddings.
- **Storage:** Add a `vector` column via migration: `$table->vector('embedding', 1536);`
- **Query:** Use Eloquent's `whereVectorSimilarTo()` for nearest-neighbor search.

```php
// Migration
$table->vector('embedding', dimensions: 1536);

// Model usage
Document::query()
    ->whereVectorSimilarTo('embedding', AI::embed($query)->get())
    ->limit(5)
    ->get();
```

## 4. AI AGENTS

- Scaffold agents using `php artisan make:agent YourAgent`.
- Encapsulate: system instructions, conversation memory, tool definitions, and output schemas inside the Agent class.
- Use structured output schemas to enforce typed JSON responses from LLMs.

```php
// Usage
$response = (new SupportAgent)->withMemory($sessionId)->run($userMessage);

// Streaming agent
return (new SupportAgent)->stream($userMessage);
```

## 5. RATE LIMITING & SECURITY

- Apply SEPARATE rate limiting for AI endpoints. Never share the global API throttle.
- Use Redis token-bucket rate limiting per user + per tenant: `RateLimiter::for('ai', fn() => ...)`
- NEVER expose raw AI provider error messages in API responses (they may leak system prompts).
- Treat LLM outputs as **untrusted user input**. Enforce JSON Schema validation before processing.
- Use Passkey authentication for high-privilege AI admin operations.

## 6. LARAVEL MCP INTEGRATION

- Use `laravel/mcp` to expose your application as an MCP server.
- Enables external AI tools (Cursor, Antigravity) to interact with your application's routes, schema, and data securely.
- Scope MCP tool permissions using Laravel Policies. Never expose raw DB access.

---

## ✅ LARAVEL AI SDK COMPLIANCE CHECK (Mandatory)
- [ ] **Provider Abstraction:** Is all LLM interaction going through `laravel/ai`, not provider-specific SDKs?
- [ ] **Streaming:** Are all user-facing LLM responses using `->stream()` for real-time feedback?
- [ ] **Rate Limiting:** Is a SEPARATE, stricter rate limiter applied to all AI endpoints?
- [ ] **Output Validation:** Is every LLM JSON output validated against a schema before processing?
- [ ] **Embedding Storage:** Is `pgvector` used for vector columns (not `TEXT` or `JSON`)?
