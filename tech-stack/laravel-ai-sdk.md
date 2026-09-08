[TECH] Laravel AI SDK (latest 0.11.0, Aug 2026)
[OBJ] First-party Laravel AI SDK (`laravel/ai`) — unified API for OpenAI, Anthropic, Gemini, Groq, xAI. Text, image, audio, embeddings, agents. Human-in-the-Loop (HITL) API for agent tool call approval.
[RULES]
1. [REQ] Install via Composer: `composer require laravel/ai`. Configure providers in `config/ai.php`.
2. [REQ] Use unified API for multiple providers: `Ai::provider('openai')->text(...)`, `Ai::provider('anthropic')->text(...)`. No provider-specific SDKs needed.
3. [REQ] Use streaming responses: `Ai::stream(...)->each(fn($chunk) => ...)`. SSE-compatible.
4. [REQ] Use embeddings: `Ai::embeddings($text)` — vector representation for semantic search.
5. [REQ] Use image generation: `Ai::image(prompt: '...')` — DALL-E, Imagen, etc.
6. [REQ] Use audio transcription: `Ai::transcribe($audioFile)` — Whisper, etc.
7. [REQ] Use agents with tool calling: `Ai::agent(tools: [...])->run(...)`. Tools are PHP closures.
8. [REQ] Use Human-in-the-Loop (HITL) API — approve/deny/modify agent tool calls before execution. `Ai::agent(tools: [...], hitl: true)`.
9. [REQ] Use `AsVector` Eloquent cast for vector storage: `$model->embedding = $vector;`.
10. [REQ] Use `whereVectorSimilarTo()` for semantic search in Eloquent: `Model::whereVectorSimilarTo('embedding', $query, 10)->get()`.
11. [REQ] Use JSON:API Resources with AI-generated structure constants.
12. [REQ] Use Laravel MCP (`laravel/mcp` v1.0.0-beta) to expose your app as MCP server for AI clients.
13. [PROHIBIT] Never hardcode API keys — use `config/ai.php` + `.env` (`AI_OPENAI_API_KEY`, etc.).
14. [PROHIBIT] Never call provider APIs directly — use `Ai::` facade for abstraction.
[COMPAT]
- Laravel AI SDK 0.11.0 (released Aug 19 2026).
- Laravel 12+ / 13+ required.
- PHP 8.3+ required.
- Providers: OpenAI, Anthropic, Gemini, Groq, xAI.
- Laravel MCP v1.0.0-beta.1 (Aug 14 2026) for MCP server.
- Laravel Boost v2.7.0 (Aug 26 2026) for AI agent context.
[REFS]
- https://packagist.org/packages/laravel/ai
- https://laravel.com/docs/ai-sdk
- https://laravel.com/docs/13.x/mcp
