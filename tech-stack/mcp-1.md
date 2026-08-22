[TECH] mcp-1
[OBJ] Model Context Protocol (FastMCP) 1.x server standards for aiZee MCP layer — streamable HTTP, OAuth 2.1, resource templates, elicitation, sampling, roots.
[RULES]
1. [REQ] `FastMCP` server instance per `aizee_mcp/aizee_server.py`. Tools registered via `@mcp.tool()`. Resources via `@mcp.resource()`. Prompts via `@mcp.prompt()`.
2. [REQ] Tool functions: typed args, return `str` (JSON-serialized). Validate inputs at entry.
3. [REQ] Route tool calls through `kernel().act()` for policy + budget gate. No direct destructive action.
4. [REQ] `is_safe_name()` from `tools/common.py` for user-provided identifiers (tool names, keys).
5. [REQ] `_MAX_INPUT_LENGTH` cap on string inputs to prevent resource exhaustion.
6. [REQ] Split tools by domain: `memory_tools.py`, `workflow_tools.py`, `policy_tools.py`, `context_tools.py`, `common.py`.
7. [REQ] `kernel()` singleton accessor in `common.py`. Never instantiate `Kernel` per-call.
8. [REQ] Streamable HTTP transport (MCP 2025-03-26 spec): use `mcp.run(transport="streamable-http")` for remote servers. Replaces deprecated SSE transport. Single endpoint `/mcp` handles all requests with session resumption via `Mcp-Session-Id` header.
9. [REQ] OAuth 2.1 authentication for HTTP transport: configure `FastMCP` with `auth_server_provider` implementing `OAuthServerProvider`. Support PKCE (`S256` challenge method). Token endpoint returns JWT with scoped claims.
10. [REQ] Resource templates via `@mcp.resource("db://tables/{table_name}/schema")`. Use URI templates (RFC 6570) for parameterized resources. Validate template variables at access time.
11. [REQ] Elicitation: servers can request structured input from users via `ctx.elicit({"type": "object", "properties": {...}})`. Use for confirmations, parameter gathering, and interactive workflows. Always provide a schema for the elicited response.
12. [REQ] Sampling: servers can request LLM completions via `ctx.sample(messages, model_preferences={...})`. Use for agentic workflows where the server needs the client's model. Respect `model_preferences` hints (cost, speed, intelligence). Never assume a specific model is available.
13. [REQ] Roots: servers can discover client filesystem roots via `ctx.list_roots()`. Use roots to scope file operations to approved directories. Never access paths outside discovered roots.
14. [REQ] Stdio transport on Windows: `subprocess.run` (inherited handles), NOT `os.execvpe` (broken pipe handles).
15. [REQ] MCP client caching: `mcp_client.py` caches stdio processes per server/root. Reuse initialized connections. Support session resumption for streamable HTTP with `Last-Event-ID` header.
16. [PROHIBIT] Inline `import asyncio` in tool functions. Top-level imports only.
17. [PROHIBIT] Raw `urllib.request.urlopen` without SSL context validation for remote endpoints.
18. [PROHIBIT] PII/credentials in tool responses or logs.
19. [PROHIBIT] Deprecated SSE transport for new servers. Use streamable HTTP. SSE transport removed in future spec versions.
[COMPAT]
- v1.29+: FastMCP stable. Streamable HTTP transport (2025-03-26 spec). OAuth 2.1, resource templates, elicitation, sampling, roots.
- v1.20+: Resource templates, elicitation support.
- Transports: stdio (local), streamable HTTP (remote). SSE deprecated.
- Python SDK: `mcp` package. Node SDK: `@modelcontextprotocol/sdk`.
[REFS]
- https://modelcontextprotocol.io
- https://modelcontextprotocol.io/docs/concepts/transports
- https://modelcontextprotocol.io/specification/2025-03-26
- https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization
- https://modelcontextprotocol.io/specification/2025-03-26/server/resource-templates
- https://modelcontextprotocol.io/specification/2025-03-26/server/elicitation
- https://github.com/modelcontextprotocol/python-sdk
