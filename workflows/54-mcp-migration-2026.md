# Workflow 54 — MCP Migration 2025-11-25 → 2026-07-28

[TRIGGER] mcp migration, mcp upgrade, mcp 2026, stateless mcp, mcp 2.0, ترحيل mcp
[PERSONA] ARCH, API, SEC, DEVX
[TECH] mcp-2, fastmcp-4

## Objective

Migrate aiZee MCP server from MCP spec 2025-11-25 (stateful, initialize handshake, Mcp-Session-Id) to 2026-07-28 (stateless core, MRTR, extensions, OAuth 2.1 Resource Server, CIMD).

## Steps

1. **Audit current state.** Read `aizee_mcp/aizee_server.py` and identify all 2025-11-25 patterns: `initialize`/`notifications/initialized` handshake, `Mcp-Session-Id` usage, Roots/Sampling/Logging server-initiated requests, HTTP+SSE transport, DCR.

2. **Upgrade SDK.** Upgrade from FastMCP v3 / MCP SDK v1.x to FastMCP v4.0.0 or Python MCP SDK v2.1.0. `pip install "mcp>=2.1,<3.0"` or `pip install fastmcp>=4.0.0`. Update imports: `FastMCP` → `MCPServer` (`from mcp.server.mcpserver import MCPServer`). Wire field names to `snake_case` (`input_schema`, `mime_type`, `is_error`). Replace `get_context()` with `ctx: Context` parameter.

3. **Remove stateful patterns.** Remove `initialize`/`notifications/initialized` handshake. Remove `Mcp-Session-Id` header usage. Every request must be self-contained with `io.modelcontextprotocol/protocolVersion`, `io.modelcontextprotocol/clientInfo`, `io.modelcontextprotocol/clientCapabilities` in `_meta`.

4. **Implement dual-era negotiation.** Detect client era from `protocolVersion` in `_meta`. Support both `2026-07-28` (modern, stateless) and `2025-11-25` (legacy, stateful) clients in same deployment. Modern path = stateless. Legacy path = backward-compat shim.

5. **Implement `server/discover` RPC.** Add `discover` handler returning `{protocolVersion, capabilities, serverInfo}`. Clients fetch supported versions and capabilities up front.

6. **Add header-based routing.** Set `Mcp-Method` and `Mcp-Name` headers on every HTTP POST. Enables gateway/WAF routing and rate-limiting without parsing JSON bodies.

7. **Cacheable tool listings.** Add `cacheControl` with `cacheTTL` to `tools/list`, `resources/list`, `prompts/list` responses. Deterministic order.

8. **MRTR for elicitation.** Replace server-initiated elicitation with `InputRequiredResult`/guard pattern (Multi Round-Trip Requests). Tools request follow-up input via structured response.

9. **OAuth 2.1 Resource Server.** Publish OAuth 2.0 Protected Resource Metadata (RFC 9728). Enforce RFC 8707 `resource` parameter in auth and token requests. Replace DCR with Client ID Metadata Documents (CIMD). Validate issuer per RFC 9207. PKCE for public clients. DPoP/capability tokens where possible.

10. **Deprecation cleanup.** Remove Roots, Sampling, Logging server-initiated requests. Remove HTTP+SSE transport. Document migration path for clients using deprecated features (12-month deprecation window).

11. **Security hardening.** Hash-pin or sign allowed tool definitions. Re-validate on every list refresh. Per-tool scopes/authorization. Audit every tool call as user–agent–tool triple. Redact secrets in tool outputs. Sandbox MCP server processes with least privilege.

12. **CVE patching.** Verify SDK versions above fix releases: Python SDK ≥1.27.2 (CVE-2026-52869, CVE-2026-52870), ≥1.28.1 (CVE-2026-59950), TypeScript SDK ≥1.26.0 (CVE-2026-25536), Go SDK ≥1.3.1 (CVE-2026-27896).

13. **Tool naming audit.** Verify all 84 tools use `snake_case` `verb_noun` pattern, ≤64 chars (ideally ≤32). No version numbers in names. Add `title` and tool annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`).

14. **Tool surface split.** Evaluate splitting 84 tools into 5-7 domain servers (e.g., `memory`, `workflow`, `policy`, `context`, `audit`, `admin`) each with its own auth boundary. One server = one domain = one auth boundary.

15. **Test with Inspector.** Run `npx @modelcontextprotocol/inspector` against all tools in CLI mode for CI. Verify `server/discover`, schema validity, error code compliance, dual-era negotiation.

16. **Client configs.** Provide ready-to-paste `mcp.json` for Cursor, Claude Code, VS Code, Cline, Windsurf. Support OAuth for remote users.

17. **Registry registration.** Publish to official `modelcontextprotocol/registry` and at least one directory (findmcp.dev / mcpfind.org).

18. **Update tech-stack.** Mark `tech-stack/mcp-1.md` as DEPRECATED. Reference `tech-stack/mcp-2.md` for new spec. Update `tech-stack/fastmcp-4.md` for FastMCP v4.

19. **Quality gate.** Run `ruff check .`, `mypy`, `aizee test --full`, `python eval/harness.py`. Run Inspector CLI against all 84 tools.

20. **Memory sync.** Update `Memory.md` with migration milestone. Update `CHANGELOG.md` `[Unreleased]` section.

## Rollback

If migration fails: revert to FastMCP v3 / MCP SDK v1.x. Restore `initialize` handshake. Restore `Mcp-Session-Id`. Document failed migration in `Memory.md` for retry.

## References

- `tech-stack/mcp-2.md` — MCP 2026-07-28 spec
- `tech-stack/fastmcp-4.md` — FastMCP v4.0.0
- https://modelcontextprotocol.io/specification/2026-07-28/
- https://gofastmcp.com/getting-started/upgrading/
- https://py.sdk.modelcontextprotocol.io/v2/migration
