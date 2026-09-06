[TECH] Node.js 26
[OBJ] Node.js 26.x (Current, latest 26.8.1 Aug 2026). Temporal API enabled by default, V8 14.6, Undici 8.0, `--allow-net` permission model, Web Storage, ErrorEvent global, JSPI for WASM.
[RULES]
1. [REQ] Use Temporal API (enabled by default, no flag): `Temporal.Now.instant()`, `Temporal.PlainDate.from()`, `Temporal.ZonedDateTime`. Prefer over `Date` for all date/time logic — immutable, timezone-aware.
2. [REQ] Use `--allow-net` permission model for network restrictions: `node --allow-net=example.com script.js`. Combine with `--allow-fs`, `--allow-env`, `--allow-child-process` for least-privilege.
3. [REQ] Use Web Storage API (enabled by default): `localStorage`, `sessionStorage` available in Node.js for persistent + session key-value storage (backed by file system).
4. [REQ] Use `ErrorEvent` global (Web-compatible error events): `new ErrorEvent("error", { error, message })`. Aligns with browser error handling.
5. [REQ] Use Undici 8.0 (bundled) for HTTP clients: `fetch()`, `WebSocket`, `Agent`, `ProxyAgent`. Prefer over `http`/`https` modules for new code.
6. [REQ] Use JSPI (JavaScript Promise Integration) for WASM: async imports in WebAssembly modules via `WebAssembly.promising()`. Enables async WASM without trampolines.
7. [REQ] Use portable compile cache: `NODE_COMPILE_CACHE=~/.cache/node` persists V8 compile cache across machines/versions for faster cold starts.
8. [REQ] Use `node:test` (built-in test runner) for unit tests: `node --test`. No external test framework needed for simple cases.
9. [REQ] Use `node:fs/promises` for async filesystem operations — never `fs` sync APIs in hot paths.
10. [REQ] Use ESM (`import`/`export`) for all new modules. CommonJS (`require`) only for legacy compat.
11. [REQ] Use `node:url` `fileURLToPath` / `pathToFileURL` for ESM path handling. `__dirname` / `__filename` not available in ESM.
12. [REQ] Use `AbortController` / `AbortSignal` for cancellation in fetch, timers, streams. `setTimeout(fn, ms, {}, signal)`.
13. [REQ] Use `node:stream` `ReadableStream` / `WritableStream` (Web Streams) — interop with `stream.Readable` via `.fromWeb()`.
14. [REQ] Use `Bun` or `Deno` only when benchmark justifies; Node 26 + Undici closes most perf gaps.
15. [REQ] Use `SlowBuffer` removed — use `Buffer.allocUnsafeSlow()` if truly needed (rare).
16. [CMD] `node --allow-net=api.example.com --allow-env server.js` run with restricted network + env access.
17. [CMD] `NODE_COMPILE_CACHE=~/.cache/node node server.js` enable portable compile cache.
18. [CMD] `node --test` run built-in test runner.
19. [PROHIBIT] Never use `require()` in ESM modules — use dynamic `import()`.
20. [PROHIBIT] Never use `process.on("uncaughtException")` to suppress errors — use `process.on("uncaughtException", ...)` only for logging + graceful shutdown.
21. [PROHIBIT] Never use `fs.readFileSync` in request handlers (blocks event loop).
22. [PROHIBIT] Never use `new Buffer()` (removed) — use `Buffer.alloc()`, `Buffer.from()`, `Buffer.allocUnsafe()`.
[COMPAT]
- Node.js 26.x Current (latest 26.8.1 Aug 2026).
- V8 14.6 engine.
- Undici 8.0 bundled.
- LTS lines: Node 24.20.0 (Active LTS), Node 22.23.2 (Maintenance LTS).
- Temporal API: enabled by default (no `--experimental-temporal` flag needed).
- Web Storage: enabled by default.
[REFS]
- https://nodejs.org/docs/latest-v26.x/api/
- https://github.com/nodejs/node/blob/main/doc/changelogs/CHANGELOG_V26.md
- https://nodejs.org/api/permissions.html
- https://tc39.es/proposal-temporal/
