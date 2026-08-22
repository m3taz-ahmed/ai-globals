[TECH] Google Gemini API
[OBJ] Cloud API for Gemini 2.0 Flash and Pro models with multimodal input, function calling, code execution, and grounding with Google Search.
[RULES]
1. [REQ] Use the `google-genai` SDK (the unified `google-genai` package, >=1.0.0) or the `@google/genai` npm package; the older `google-generativeai` SDK is deprecated.
2. [REQ] Load the API key from `GEMINI_API_KEY` or `GOOGLE_API_KEY` environment variable; never hardcode keys in source files.
3. [REQ] Use `gemini-2.0-flash` for low-latency, high-volume tasks and `gemini-2.0-flash-thinking-exp` or `gemini-2.5-pro` for complex reasoning; pin model versions in production.
4. [REQ] For multimodal input, pass `contents` as a list of `Part` objects; images use `Part.from_image()`, video uses `Part.from_uri(uri, mime_type="video/mp4")`, and inline data uses `Part.from_bytes()`.
5. [REQ] For function calling, define `tools=[Tool(function_declarations=[...])]` with `FunctionDeclaration(name, description, parameters)`; handle `function_call` parts in the response and return `function_response` parts.
6. [REQ] Enable code execution by setting `tools=[Tool(code_execution=CodeExecution())]`; the model will generate and run Python code in a sandbox and return results in `executable_code` and `code_execution_result` parts.
7. [REQ] Enable grounding with Google Search by setting `tools=[Tool(google_search=GoogleSearch())]` on Gemini 2.0 Flash; retrieve citations from `grounding_metadata` in the response.
8. [REQ] Use `GenerateContentConfig` to set `temperature`, `top_p`, `max_output_tokens`, and `safety_settings`; override default safety thresholds explicitly when needed for legitimate content.
9. [REQ] Implement retry logic for 429 (RESOURCE_EXHAUSTED) and 503 errors with exponential backoff; respect `retry_delay` in error metadata when provided.
10. [REQ] For streaming, use `client.models.generate_content_stream(model, contents)` and iterate over chunk objects; handle `finish_reason` on the final chunk.
11. [REQ] Use structured output via `response_mime_type="application/json"` with `response_schema` (a Pydantic model or JSON schema dict) for reliable structured responses.
12. [CMD] `pip install google-genai` to install the unified Python SDK.
13. [CMD] `export GEMINI_API_KEY="AIza..."` to set the API key.
14. [PROHIBIT] Never disable all safety settings (`HarmBlockThreshold.BLOCK_NONE`) in production without explicit review; this can expose users to harmful model outputs.
15. [PROHIBIT] Never use the deprecated `google-generativeai` (`genai`) SDK for new projects; migrate to `google-genai` which supports Vertex AI and Gemini API uniformly.
[COMPAT]
- Python SDK: google-genai>=1.0.0 (Python 3.9+)
- Node SDK: @google/genai>=1.0.0 (Node 18+)
- Models: gemini-2.0-flash, gemini-2.0-flash-lite, gemini-2.5-pro, gemini-2.5-flash
[REFS]
- https://ai.google.dev/gemini-api/docs
- https://ai.google.dev/gemini-api/docs/function-calling
- https://ai.google.dev/gemini-api/docs/code-execution
- https://ai.google.dev/gemini-api/docs/grounding
