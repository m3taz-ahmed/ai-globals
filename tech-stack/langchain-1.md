[TECH] LangChain 1.3
[OBJ] LangChain 1.3.x (latest 1.3.18 Aug 2026). Native MCP support in `langchain.mcp`, stateless protocol support, elicitation via LangGraph interrupts, tool-list caching, `deepagents` updates. `langchain-mcp-adapters` deprecated.
[RULES]
1. [REQ] Use `langchain.mcp` (native MCP support) for Model Context Protocol integration — replaces deprecated `langchain-mcp-adapters` package. `from langchain.mcp import MCPToolkit`.
2. [REQ] Migrate from `langchain-mcp-adapters` to `langchain.mcp` — deprecated package will not receive updates. Use `MCPToolkit.from_server(...)` for stdio/SSE/streamable HTTP transports.
3. [REQ] Use stateless protocol support: MCP servers can be stateless (no session required). Configure with `transport="streamable_http"` for HTTP, `transport="stdio"` for local.
4. [REQ] Use elicitation via LangGraph interrupts: MCP servers can request user input mid-tool-execution via `interrupt()`. Handle in LangGraph with `Command(resume=...)`.
5. [REQ] Use tool-list caching: cache MCP server tool discovery to avoid repeated `list_tools` calls. `MCPToolkit(cache_tools=True)`.
6. [REQ] Use `deepagents` module for multi-step agent workflows: `from langchain.deepagents import create_deep_agent`. Updated with MCP + LangGraph integration.
7. [REQ] Use LangChain 1.x modular imports: `from langchain_core.language_models import BaseChatModel`. Avoid `from langchain import ...` (legacy).
8. [REQ] Use `langchain_core` for primitives (messages, prompts, output parsers). `from langchain_core.messages import HumanMessage, AIMessage, SystemMessage`.
9. [REQ] Use LCEL (LangChain Expression Language) for chains: `chain = prompt | model | parser`. Compose with `|` pipe operator.
10. [REQ] Use `langchain.chat_models` for LLM integration: `init_chat_model("openai:gpt-6-astra")`, `init_chat_model("anthropic:claude-fable-5-1")`. Unified interface.
11. [REQ] Use `langchain_community` for third-party integrations (vector stores, document loaders, tools). Pin versions — community package changes frequently.
12. [REQ] Use `langchain_openai` / `langchain_anthropic` / `langchain_google_genai` for official provider integration packages.
13. [REQ] Use `langchain.text_splitters` (`RecursiveCharacterTextSplitter`) for chunking. Use `langchain_community.document_loaders` for file ingestion.
14. [REQ] Use `langchain_core.runnables` for runnable protocol: `RunnablePassthrough`, `RunnableLambda`, `RunnableParallel`. Enables LCEL composition.
15. [REQ] Use structured output: `model.with_structured_output(Schema)` — returns Pydantic model / dataclass / dict.
16. [CMD] `pip install langchain langchain-core langchain-mcp` install core + MCP.
17. [CMD] `pip install langchain-openai langchain-anthropic` install provider packages.
18. [CMD] `langchain serve` deploy LangServe app (if using LangServe).
19. [PROHIBIT] Never use `langchain-mcp-adapters` — deprecated, use `langchain.mcp`.
20. [PROHIBIT] Never use `from langchain import ...` legacy imports — use modular `langchain_core` / `langchain_community`.
21. [PROHIBIT] Never hardcode API keys — use environment variables / secrets manager.
22. [PROHIBIT] Never use `ConversationChain` (deprecated) — use LangGraph for stateful conversations.
[COMPAT]
- LangChain 1.3.x (latest 1.3.18 Aug 2026).
- Native MCP support via `langchain.mcp`.
- `langchain-mcp-adapters` deprecated — migrate to `langchain.mcp`.
- LangGraph 1.1 integration (v2 streaming).
- Python 3.10+ (3.14 compatible).
- Provider packages: langchain-openai, langchain-anthropic, langchain-google-genai.
[REFS]
- https://python.langchain.com/docs/
- https://python.langchain.com/docs/integrations/mcp/
- https://github.com/langchain-ai/langchain
- https://docs.langchain.com/oss/python/langchain
