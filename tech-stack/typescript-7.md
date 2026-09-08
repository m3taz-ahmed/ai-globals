[TECH] TypeScript 7.0
[OBJ] TypeScript 7.0 (latest 7.0.2, Aug 2026). Native Go compiler port ("tsgo") delivering ~10x faster compilation via shared-memory parallelism. Same `typescript` package on npm. Native platform binaries. Last JS-based release was 6.0.
[RULES]
1. [REQ] Use `npm install typescript@latest` to get TS 7.0 — same package name, native Go compiler under the hood.
2. [REQ] All TS 6.0 deprecations are REMOVED in 7.0 — migrate all `ignoreDeprecations: "6.0"` options before upgrading. Run `tsc` on 6.0 first to find deprecated options.
3. [REQ] Use `with` syntax for import attributes: `import json from "./data.json" with { type: "json" }`. Import assertions (`assert { type: "json" }`) are hard errors in 7.0.
4. [REQ] Expect ~10x faster compilation — native Go compiler with shared-memory parallelism. No config change needed; `tsc` remains the entry binary.
5. [REQ] Use `satisfies` operator for type-safe object literals: `const config = {...} satisfies Config`.
6. [REQ] Use improved inference for contextually sensitive functions — TS 7.0 better infers generic parameters from contextual types.
7. [REQ] Use DOM type updates for Temporal APIs: `Temporal.PlainDate`, `Temporal.ZonedDateTime`, `Temporal.Duration`.
8. [REQ] Use subpath imports (Node.js `imports` field in `package.json`) for internal module aliasing: `"#utils/*": "./src/utils/*"`.
9. [REQ] `strict: true` is the default — all new projects get strict mode automatically.
10. [REQ] `rootDir` defaults to `.` (current directory) — adjust if your source is in a subdirectory.
11. [REQ] `types: []` is required to opt out of auto-included `@types/*` packages — list your globals explicitly (e.g., `["node", "jest"]`).
12. [PROHIBIT] Never use `import ... assert {...}` syntax — errors in 7.0. Use `with` syntax.
13. [PROHIBIT] Never use deprecated `ignoreDeprecations` options — removed in 7.0.
14. [PROHIBIT] Never assume JS-based compiler behavior — Go compiler may have subtle differences in error messages and edge cases.
[COMPAT]
- TypeScript 7.0.2 (released Jul 2026, GitHub tag Aug 2026).
- Native Go compiler ("tsgo") — ~10x faster compilation.
- Same `typescript` npm package — drop-in replacement.
- Native platform binaries (no Node.js required for compilation).
- TS 6.0 was the last JS-based release (bridge release).
[REFS]
- https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/
- https://github.com/microsoft/TypeScript/releases/tag/v7.0.2
- https://www.typescriptlang.org/docs/handbook/release-notes/typescript-7-0.html
