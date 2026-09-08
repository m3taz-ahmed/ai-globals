[TECH] Google Agent Development Kit (ADK) v2.7
[OBJ] First-party Google agent framework v2.7 (latest 2.7.1, Aug 2026). Graph-based workflow engine, task delegation, multi-agent orchestration, Gemini integration, MCP support, deployment to Google Cloud. Available in Python, Java, Go, TypeScript, Kotlin.
[RULES]
1. [REQ] Use Google ADK v2.0+ as first-party Google agent framework — Gemini integration native, Google Cloud deployment built-in. GA across Python, Java, Go, TypeScript, Kotlin.
2. [REQ] Use Workflow Runtime (v2.0+): graph-based execution engine where Agents/Tools/Functions are nodes in a workflow graph. Separates execution routing from language processing.
3. [REQ] Use Task API for structured agent-to-agent delegation: parallel sub-agent workers, nested hierarchical team structures, resilient dynamic scheduling.
4. [REQ] Use programmatic routing in workflows: transitions evaluated in code (not LLM) between deterministic nodes — reduces token consumption and latency.
5. [REQ] Use Gemini models via ADK — `Agent(model="gemini-2.5-pro", ...)` — no separate API client needed.
6. [REQ] Use tool use via ADK — `FunctionTool` / `LangchainTool` / `CrewaiTool` wrappers for custom tools.
7. [REQ] Use MCP support — ADK agents can consume MCP servers as tool sources; `adk.tools.mcp.MCPToolset`.
8. [REQ] Use multi-agent orchestration — `SequentialAgent`, `LoopAgent`, `ParallelAgent` for agent composition.
9. [REQ] Use `Agent` class with `instruction`, `tools`, `sub_agents` for hierarchical agent design.
10. [REQ] Use session/state management — `SessionService` + `State` for persistent conversation context.
11. [REQ] Use `adk deploy` for one-command deployment to Vertex AI Agent Engine.
12. [REQ] Use Go workflows (v2.7+): graph-based workflows now available for Go (previously Python-only in v2.0).
8. [REQ] Use `Runner` for agent execution — `Runner(agent=my_agent, app_name="my_app", session_service=...)`.
9. [REQ] Deploy to Google Cloud — Cloud Run, Vertex AI Agent Builder; `adk deploy` CLI.
10. [REQ] Use `adk web` for local dev UI — test agents in browser before deploy.
11. [REQ] Use `adk eval` for agent evaluation — golden datasets, regression testing.
12. [REQ] Use Google Cloud IAM + Secret Manager for credentials — never hardcode API keys.
13. [PROHIBIT] Never hardcode Gemini API keys — use Google Cloud auth / Secret Manager.
14. [PROHIBIT] Never use non-Gemini models without explicit adapter — ADK is Gemini-first.
15. [PROHIBIT] Never deploy without `adk eval` passing — regression test agents.
16. [PROHIBIT] Never bypass `Runner` for agent execution — use `Runner.run()` / `Runner.run_async()`.
17. [CMD] `pip install google-adk` — install.
18. [CMD] `adk web` — local dev UI.
19. [CMD] `adk deploy cloud_run` — deploy to Cloud Run.
20. [CMD] `adk eval` — run evaluation suite.
[COMPAT]
- Google ADK: Python (primary), TypeScript.
- Gemini models: 2.5 Pro, 2.5 Flash, etc.
- MCP: consumes MCP servers as tool sources.
- Google Cloud: Cloud Run, Vertex AI deployment.
- Multi-agent: Sequential, Loop, Parallel orchestration.
[REFS]
- https://google.github.io/adk-docs/
- https://github.com/google/adk-python
- https://cloud.google.com/products/agent-builder
