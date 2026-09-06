[TECH] mcp-2
[OBJ] Model Context Protocol 2026-07-28 specification — stateless core, MRTR, extensions framework, OAuth 2.1 Resource Server, header-based routing, cacheable listings. Supersedes mcp-1 (2025-03-26 spec).
[RULES]
1. [REQ] Stateless core: NO `initialize`/`notifications/initialized` handshake. Every request is self-contained and carries `io.modelcontextprotocol/protocolVersion`, `io.modelcontextprotocol/clientInfo`, and `io.modelcontextprotocol/clientCapabilities` in `_meta`.
2. [REQ] No protocol-level sessions: `Mcp-Session-Id` header REMOVED. Any request can land on any server instance behind a round-robin load balancer. Design servers stateless.
3. [REQ] `server/discover` RPC: clients fetch supported versions, capabilities, and server identity up front. Implement `discover` handler returning `{protocolVersion, capabilities, serverInfo}`.
4. [REQ] Header-based routing: HTTP POSTs carry `Mcp-Method` and `Mcp-Name` headers. Gateways/WAFs route and rate-limit without parsing JSON bodies. Set these headers on every request.
5. [REQ] Cacheable tool listings: `tools/list`, `resources/list`, `prompts/list` carry cache hints (`cacheControl`) and deterministic order. Set `cacheTTL` on listings to reduce redundant calls.
6. [REQ] Multi Round-Trip Requests (MRTR): replaces persistent bidirectional server-initiated requests. Tools request follow-up input via `InputRequiredResult`/guard pattern. Use for confirmations, parameter gathering, interactive workflows.
7. [REQ] Extensions framework: formal opt-in extensions. Known extensions: `io.modelcontextprotocol/tasks` (long-running poll-based jobs), `io.modelcontextprotocol/apps` (server-rendered UI widgets), `io.modelcontextprotocol/skills` (rich agent instructions), Enterprise Managed Authorization (EMA).
8. [REQ] OAuth 2.1 Resource Server: MCP server = OAuth 2.1 Resource Server. MUST publish OAuth 2.0 Protected Resource Metadata (RFC 9728). Client MUST send `resource` parameter (RFC 8707) in auth and token requests.
9. [REQ] Client ID Metadata Documents (CIMD): Dynamic Client Registration (DCR) DEPRECATED. Use CIMD for client registration. Validate issuer per RFC 9207.
10. [REQ] PKCE for public clients: Use PKCE (`S256` challenge method). Use DPoP / capability tokens where possible for token binding.
11. [REQ] stdio transports: SHOULD NOT follow OAuth auth spec — it is HTTP-transport only. stdio = local trust boundary.
12. [REQ] Transports: stdio (stateless per process, local/dev), Streamable HTTP (single POST endpoint, per-request SSE stream, no GET stream, no session resumption). HTTP+SSE (legacy) DEPRECATED — avoid for new work.
13. [REQ] Deprecation policy: minimum 12-month deprecation window. Deprecated features: Roots, Sampling, Logging, HTTP+SSE transport. Plan migration before deprecation window expires.
14. [REQ] Tool naming: `snake_case`, `verb_noun` pattern (e.g., `search_customer_orders`, `create_invoice`). Allowed chars: `A-Z a-z 0-9 _ - . /`. Length ≤64 chars, ideally ≤32 for client search. NO version numbers in names — use `version` field. Short domain prefix to avoid collisions: `billing_search_customer_orders`.
15. [REQ] Tool schema: JSON Schema `inputSchema` with `additionalProperties: false`. Narrow enums, examples, descriptions explaining when NOT to use. Set `title` and tool annotations: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`.
16. [REQ] Tool vs Resource vs Prompt: Tool = model invokes, actions with side effects. Resource = addressable, read-only data, keeps tool list short. Prompt = user-triggered templates/slash commands.
17. [REQ] One server = one domain = one auth boundary: Group related tools under one server (e.g., GitHub, billing, database). Shared types/schemas inside that server. Authenticate, redact, rate-limit at server boundary.
18. [REQ] Error handling: structured, actionable errors. Spec-correct error codes. NEVER fail silently. Explicit timeouts and rate limits. Long calls async via Tasks extension.
19. [REQ] Dual-era support: support both `2026-07-28` (modern) and `2025-11-25` (legacy) clients in same deployment via multi-era negotiation. Detect client era from `protocolVersion` in `_meta`.
20. [REQ] FastMCP v4.0.0 or Python MCP SDK v2.1.0: upgrade from FastMCP v3 / MCP SDK v1.x. `FastMCP` → `MCPServer` (`from mcp.server.mcpserver import MCPServer`). Wire field names `snake_case` (`input_schema`, `mime_type`, `is_error`). `get_context()` removed — declare `ctx: Context` parameter.
21. [REQ] Security — tool poisoning defense: hash-pin or sign allowed tool definitions. Re-validate on every list refresh. Tool descriptions and outputs = untrusted input. Allowlist approved servers. Sandbox MCP server processes with least privilege.
22. [REQ] Security — per-tool scopes: implement per-tool authorization, not one global token. Audit every tool call as user–agent–tool triple. Redact secrets in tool outputs and logs.
23. [REQ] Security — CVE tracking: monitor MCP CVEs. Known 2026 CVEs: CVE-2026-52869 (Python SDK session-ID injection, fixed 1.27.2), CVE-2026-52870 (cross-client task access, fixed 1.27.2), CVE-2026-59950 (WebSocket origin bypass, fixed 1.28.1), CVE-2026-25536 (TypeScript SDK cross-client data leak, fixed 1.26.0), CVE-2026-27896 (Go SDK case-insensitive key parsing, fixed 1.3.1), CVE-2025-54136 (tool poisoning/rug-pull, CVSS 8.8).
24. [REQ] Testing: use `@modelcontextprotocol/inspector` v0.22.0 for test/debug. Run in CLI mode for CI. Verify `server/discover`, schema validity, error code compliance. `npx @modelcontextprotocol/inspector` against all tools.
25. [REQ] Client configs: provide ready-to-paste `mcp.json` for Cursor, Claude Code, VS Code, Cline, Windsurf. Support OAuth for remote users. Register in official registry + at least one directory (findmcp.dev / mcpfind.org).
26. [PROHIBIT] Using `initialize`/`notifications/initialized` handshake (removed in 2026-07-28).
27. [PROHIBIT] Relying on `Mcp-Session-Id` header (removed in 2026-07-28).
28. [PROHIBIT] Using HTTP+SSE transport for new servers (deprecated).
29. [PROHIBIT] Using Dynamic Client Registration (DCR) — use CIMD instead.
30. [PROHIBIT] Auto-executing project-defined MCP servers with OS privileges without allowlist validation.
[COMPAT]
- 2026-07-28 (current): stateless core, MRTR, extensions, OAuth 2.1 Resource Server, CIMD, header-based routing, cacheable listings.
- 2025-11-25 (legacy): stateful, initialize handshake, Mcp-Session-Id, DCR. Support via dual-era negotiation.
- 2025-03-26 (deprecated): original streamable HTTP. Avoid.
- FastMCP v4.0.0 (GA 31 Aug 2026): builds on Python SDK v2. Multi-era negotiation, stateless UserSession, fastmcp.Client, enterprise identity, extensions, fastmcp-tasks.
- Python MCP SDK v2.1.0: `MCPServer` class, `mcp_types`, `httpx2`, `Client` for tests.
[REFS]
- https://modelcontextprotocol.io/specification/2026-07-28/basic/index
- https://blog.modelcontextprotocol.io/posts/2026-07-28/
- https://modelcontextprotocol.io/specification/2026-07-28/changelog.md
- https://gofastmcp.com/getting-started/upgrading/
- https://py.sdk.modelcontextprotocol.io/v2/migration
- https://github.com/modelcontextprotocol/registry
