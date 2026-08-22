[TECH] OpenAI API
[OBJ] Cloud API for GPT-4o, o1 reasoning models, embeddings, function calling, structured outputs, and streaming chat completions.
[RULES]
1. [REQ] Use the official `openai` Python SDK (>=1.0.0) or `openai` npm package; never hand-roll HTTP calls for production code.
2. [REQ] Load API keys from environment variables (`OPENAI_API_KEY`) or a secrets manager; never hardcode keys in source files or commit them to git.
3. [REQ] Set `timeout` and `max_retries` on the client constructor so transient network errors and 429/5xx responses are retried automatically with exponential backoff.
4. [REQ] Use `client.chat.completions.parse()` with a Pydantic model (or `response_format={"type": "json_schema", ...}`) for structured outputs rather than asking the model to "return JSON" in a plain prompt.
5. [REQ] Include `tools` and `tool_choice` parameters for function calling; always handle the `tool_calls` array in the response and dispatch to the correct local function by name.
6. [REQ] When streaming, iterate over `stream = client.chat.completions.create(stream=True)` and accumulate `delta.content` chunks; close the stream properly to avoid connection leaks.
7. [REQ] Use `tiktoken` to count tokens before sending requests (`tiktoken.encoding_for_model("gpt-4o")`); reject or truncate input that exceeds the model context window before calling the API.
8. [REQ] Use `gpt-4o-mini` for high-volume, low-latency tasks and `gpt-4o` for complex reasoning; use `o1` / `o3-mini` only when extended chain-of-thought reasoning is required and higher latency is acceptable.
9. [REQ] Use `text-embedding-3-small` for most embedding workloads and `text-embedding-3-large` only when higher dimensionality (3072) is justified by downstream retrieval quality.
10. [REQ] Implement rate-limit handling by reading `x-ratelimit-remaining-requests` and `x-ratelimit-remaining-tokens` headers; back off when either approaches zero.
11. [REQ] Use the Batch API (`client.batches`) for asynchronous workloads of up to 50,000 requests with a 24-hour completion window to cut costs by 50%.
12. [CMD] `pip install openai tiktoken` to install the SDK and tokenizer.
13. [CMD] `export OPENAI_API_KEY="sk-..."` to set the API key in the shell environment.
14. [PROHIBIT] Never log or store full request/response bodies that contain user PII without redaction; OpenAI data retention policies require careful handling of sensitive content.
15. [PROHIBIT] Never use the deprecated `/v1/completions` (text-davinci) endpoint or `openai.ChatCompletion.create()` v0 syntax; always use the v1 SDK `client.chat.completions.create()`.
[COMPAT]
- Python SDK: openai>=1.50.0 (Python 3.8+)
- Node SDK: openai>=4.70.0 (Node 18+)
- Models: gpt-4o (2024-08-06), gpt-4o-mini, o1, o1-mini, o3-mini, text-embedding-3-small/large
[REFS]
- https://platform.openai.com/docs/api-reference
- https://platform.openai.com/docs/guides/structured-outputs
- https://platform.openai.com/docs/guides/function-calling
- https://github.com/openai/tiktoken
