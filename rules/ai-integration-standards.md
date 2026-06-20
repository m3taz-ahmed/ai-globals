[FILE] ai-integration-standards
[OBJ] AI integration patterns, streaming, and context management.
[RULES]
1. [REQ] Async Processing: Push incoming AI queries to Redis queue immediately. No synchronous waiting.
2. [REQ] Streaming: Use Server-Sent Events (SSE) to stream tokens. Disable Nginx buffering (`proxy_buffering off`).
3. [REQ] Context Limits: Prevent collapse via sliding token buffers and RAG injection.
4. [REQ] Semantic Cache: Use vector similarity caching (threshold >= 0.95) to prevent redundant LLM calls.
5. [REQ] Generative UI: Enforce `OpenUI` framework. Define strict Zod components. No raw JSON-based UI output.
