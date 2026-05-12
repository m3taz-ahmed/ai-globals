# AI Integration Standards (Streaming, Queues & Context)

> [!NOTE]
> **TRIGGER:** LOAD ON ANY TASK INVOLVING AI INTEGRATION, LLM CHAT INTERFACES, OR RAG SYSTEMS.
> **SCOPE:** MANDATORY ARCHITECTURAL PROTOCOLS FOR AI-GLOBALS AND MANAGED PROJECTS.

## 1. ASYNCHRONOUS AI PROCESSING (NO HTTP BOTTLENECK)
- **Zero Synchronous Waiting:** Never process LLM calls directly inside an HTTP request lifecycle. Synchronous HTTP waiting leads to connection pool exhaustion and gateway timeouts.
- **Queue-First Architecture:** Incoming AI queries MUST be pushed to a Redis Queue immediately. The API returns an immediate acknowledgment or a streaming stream initialization.
- **Background Workers:** Dedicated queue workers handle the actual inference calls to the AI models.

## 2. REAL-TIME STREAMING (SSE MANDATE)
- **Streaming Technology:** Use **Server-Sent Events (SSE)** for streaming responses from the backend to the frontend. WebSockets should be avoided unless bidirectional streaming is strictly required.
- **Time To First Token ($T_{TTFT}$):** Optimize the user experience by streaming tokens as they are generated, reducing perceived latency to the first token.
- **Nginx Config:** Ensure proxy buffering is disabled for SSE endpoints (`proxy_buffering off;`) to prevent delayed delivery of tokens.

## 3. CONTEXT MANAGEMENT & TOKEN LIMITS
- **Context Collapse Prevention:** Never send the raw, uncompressed chat history to the LLM. 
- **Sliding Window:** Maintain a maximum historical token buffer. Older interactions must be truncated or summarized automatically.
- **Semantic Injection:** Use Retrieval-Augmented Generation (RAG) to dynamically inject only semantically relevant documents into the context window.

## 4. SEMANTIC CACHING
- **Redundancy Reduction:** Implement a semantic caching layer (using vector similarity) before invoking the LLM. If a user asks a question semantically identical to a cached entry (e.g., similarity threshold ≥ 0.95), return the cached response immediately.
- **Database Latency ($T_{db}$):** Caching drastically reduces both token costs and backend database wait times.
