# AI Integration Standards (Streaming, Queues & Context)
> [!NOTE]
> Trigger: AI integration, LLM chat interfaces, or RAG systems.

## Asynchronous AI Processing `[API-05]`
- **Zero Synchronous Waiting:** Push incoming queries to a Redis queue worker immediately. Return immediate acknowledgment or stream initialization.

## Real-Time Streaming (SSE Mandate) `[API-06]`
- **SSE:** Stream tokens to client using Server-Sent Events. Disable Nginx proxy buffering (`proxy_buffering off;`).

## Context Management `[API-07]`
- **Collapse Prevention:** Sliding token buffer window, truncate/summarize old interactions, inject only relevant metadata/docs using RAG.

## Semantic Caching `[API-08]`
- **Vector Cache:** Cache responses using vector similarity (threshold >= 0.95) to prevent redundant API calls.
