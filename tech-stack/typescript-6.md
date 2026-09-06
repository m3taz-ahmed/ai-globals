[TECH] TypeScript 6.0
[OBJ] Bridge release before TS 7.0 (native Go compiler). `ignoreDeprecations: "6.0"`, deprecated options flagged for TS 7.0 removal, `with` import syntax, improved inference, Temporal DOM types, subpath imports, `--goToJS` migration.
[RULES]
1. [REQ] Set `"ignoreDeprecations": "6.0"` in `tsconfig.json` to suppress deprecation warnings for options scheduled for TS 7.0 removal; plan migration before TS 7.0 GA.
2. [REQ] Use `with` syntax for import attributes: `import json from "./data.json" with { type: "json" }`. Import assertions (`assert { type: "json" }`) are deprecated — migrate all existing `assert` to `with`.
3. [REQ] Use improved inference for contextually sensitive functions: TS 6.0 better infers generic parameters from contextual types — remove manual type annotations where inference now suffices.
4. [REQ] Use DOM type updates for Temporal APIs: `Temporal.PlainDate`, `Temporal.ZonedDateTime`, `Temporal.Duration` are typed. Prefer Temporal over `Date` for date/time logic in browser-targeted code.
5. [REQ] Use subpath imports (Node.js `imports` field in `package.json`) for internal module aliasing: `"#utils/*": "./src/utils/*"`. TS 6.0 resolves these without `paths` config.
6. [REQ] Use `--goToJS` migration flag to generate JS output for incremental migration from TS to plain JS (for projects moving off TS).
7. [REQ] Use `satisfies` operator for type-safe object literals: `const config = {...} satisfies Config`. Preserves literal types while validating.
8. [REQ] Use `using` / `await using` for resource management (explicit resource management): `using handle = getResource()` — auto-dispose at scope end.
9. [REQ] Use `const` type parameters: `function first<T const>(arr: readonly T[])`. Prevents inference widening.
10. [REQ] Use `--moduleResolution: bundler` for modern bundler-based projects (Vite, Webpack, Turbopack). Use `node16` / `nodenext` for Node.js.
11. [REQ] Use `--module: nodenext` / `esnext` for ESM. `--target: es2024` minimum for modern features.
12. [REQ] Use `--strict: true` (enables all strict checks). Never disable `noImplicitAny` or `strictNullChecks`.
13. [REQ] Use `enum` sparingly — prefer `as const` objects + union types for tree-shakeability: `const Status = { Active: "active", ... } as const; type Status = typeof Status[keyof typeof Status]`.
14. [REQ] Use `interface` for extensible/object types, `type` for unions/intersections/mapped types. Never `type` for simple object shapes when `interface` suffices.
15. [REQ] Use `unknown` over `any` for untyped external data; narrow with type guards before use.
16. [CMD] `tsc --noEmit` type-check without emitting.
17. [CMD] `tsc --goToJS` generate JS from TS for migration.
18. [CMD] `npm install -D typescript@6` install TS 6.0.
19. [PROHIBIT] Never use `any` without explicit justification (`// eslint-disable` with reason).
20. [PROHIBIT] Never use `as` type assertions to silence errors — narrow properly or fix the type.
21. [PROHIBIT] Never use `// @ts-ignore` — use `// @ts-expect-error` with explanation (fails if error disappears).
22. [PROHIBIT] Never use import assertions (`assert {}`) — deprecated, use `with {}`.
[COMPAT]
- TypeScript 6.0 (released Mar 2026).
- TS 7.0 native preview available (Go compiler, not production-ready).
- Node.js 20+ for `with` import attribute runtime support.
- Bundlers: Vite 7+, Webpack 5+, Turbopack (Next 16) support `with` syntax.
- `tsconfig.json` `ignoreDeprecations: "6.0"` required to suppress migration warnings.
[REFS]
- https://www.typescriptlang.org/docs/handbook/release-notes/typescript-6-0.html
- https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/
- https://github.com/microsoft/typescript-go (TS 7.0 native preview)
