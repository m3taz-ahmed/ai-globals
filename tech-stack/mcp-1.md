[TECH] mcp-1
[OBJ] Model Context Protocol (FastMCP) 1.x server standards for aiZee MCP layer.
[RULES]
1. [REQ] `FastMCP` server instance per `aizee_mcp/aizee_server.py`. Tools registered via `@mcp.tool()`.
2. [REQ] Tool functions: typed args, return `str` (JSON-serialized). Validate inputs at entry.
3. [REQ] Route tool calls through `kernel().act()` for policy + budget gate. No direct destructive action.
4. [REQ] `is_safe_name()` from `tools/common.py` for user-provided identifiers (tool names, keys).
5. [REQ] `_MAX_INPUT_LENGTH` cap on string inputs to prevent resource exhaustion.
6. [REQ] Split tools by domain: `memory_tools.py`, `workflow_tools.py`, `policy_tools.py`, `context_tools.py`, `common.py`.
7. [REQ] `kernel()` singleton accessor in `common.py`. Never instantiate `Kernel` per-call.
8. [REQ] Stdio transport on Windows: `subprocess.run` (inherited handles), NOT `os.execvpe` (broken pipe handles).
9. [REQ] MCP client caching: `mcp_client.py` caches stdio processes per server/root. Reuse initialized connections.
10. [PROHIBIT] Inline `import asyncio` in tool functions. Top-level imports only.
11. [PROHIBIT] Raw `urllib.request.urlopen` without SSL context validation for remote endpoints.
12. [PROHIBIT] PII/credentials in tool responses or logs.
[COMPAT]
- v1.29: current installed. FastMCP stable.
- stdio + HTTP transports supported.
[REFS]
- modelcontextprotocol.io
- github.com/modelcontextprotocol/python-sdk
