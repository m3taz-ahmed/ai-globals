[TECH] Google Gemini API 2026
[OBJ] Google Gemini API 2026. Gemini 3.8 Flash/Cyber (Sep 2026), 3.7/3.6/3.5 Flash-Lite, 3.5 Transcribe, Omni 1.1 Flash. Interactions API GA, agentic video (88% token / 66% cost reduction). Legacy generateContent still supported.
[RULES]
1. [REQ] Use `gemini-3.8-flash` (latest, Sep 2026) for balanced speed/intelligence. Use `gemini-3.8-cyber` for security-focused tasks. Use `gemini-3.7-flash-lite` / `3.6` / `3.5` for cost-sensitive high-volume.
2. [REQ] Use Interactions API (GA) for agentic workflows: `client.interactions.create` with tools, sessions, multi-turn orchestration. Replaces manual conversation management.
3. [REQ] Use agentic video for video understanding: 88% token reduction + 66% cost reduction vs frame-by-frame analysis. `client.models.generate_content(model="gemini-3.8-flash", contents=video_uri)`.
4. [REQ] Use `gemini-3.5-transcribe` for audio transcription: streaming + batch modes, multi-language, speaker diarization.
5. [REQ] Use `gemini-omni-1.1-flash` for multimodal real-time: text + image + audio + video input, streaming output.
6. [REQ] Use `google-genai` SDK (Python) or `@google/genai` (Node.js) — unified SDK replaces `google-generativeai`. `from google import genai`.
7. [REQ] Use `client.models.generate_content(model=..., contents=...)` for basic calls. Legacy `generateContent` still supported but prefer new SDK pattern.
8. [REQ] Use structured output: `config=GenerateContentConfig(response_mime_type="application/json", response_schema=...)`. Schema via Pydantic / dataclass / JSON schema.
9. [REQ] Use function calling: `tools=[func1, func2]` with auto-discovery (SDK inspects docstrings/signatures). Handle `function_call` parts, return `function_response`.
10. [REQ] Use streaming: `client.models.generate_content_stream(...)` — yields chunks. Parse `chunk.text` / `chunk.function_call`.
11. [REQ] Use context caching: `client.caches.create(model=..., contents=large_context)` — cache large docs/video, reference by cache ID. Reduces cost for repeated context.
12. [REQ] Use `gemini-3.8-flash` with 1M+ token context for long-context tasks. Verify tier limits.
13. [REQ] Use `GEMINI_API_KEY` env var or Google Cloud ADC (Application Default Credentials) for Vertex AI.
14. [REQ] Use Vertex AI for enterprise: IAM, VPC-SC, CMEK, data residency. `client = genai.Client(vertexai=True, project=..., location=...)`.
15. [REQ] Use safety settings: `config=GenerateContentConfig(safety_settings=[{"category": "HARM_CATEGORY_...", "threshold": "BLOCK_..."}])`. Default blocks harmful content.
16. [CMD] `pip install google-genai` install Python SDK.
17. [CMD] `npm install @google/genai` install Node SDK.
18. [CMD] `export GEMINI_API_KEY="..."` set API key (AI Studio).
19. [PROHIBIT] Never use `google-generativeai` (legacy SDK) for new code — use `google-genai`.
20. [PROHIBIT] Never hardcode API keys in client code — use backend proxy / ADC.
21. [PROHIBIT] Never disable all safety filters without documented enterprise approval.
22. [PROHIBIT] Never send PII to consumer-tier API without data processing agreement — use Vertex AI.
[COMPAT]
- Google Gemini API 2026.
- Models: gemini-3.8-flash, gemini-3.8-cyber (Sep 2026), 3.7/3.6/3.5-flash-lite, 3.5-transcribe, omni-1.1-flash.
- Interactions API GA.
- SDK: google-genai 1.0+ (Python), @google/genai 1.0+ (Node.js).
- Legacy generateContent supported (backward compat).
- Vertex AI for enterprise features.
[REFS]
- https://ai.google.dev/gemini-api/docs
- https://ai.google.dev/gemini-api/docs/interactions
- https://ai.google.dev/gemini-api/docs/video-understanding
- https://github.com/googleapis/python-genai
