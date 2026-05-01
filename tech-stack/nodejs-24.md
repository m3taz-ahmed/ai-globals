# Node.js 24 LTS Strict Standards

## 1. TYPESCRIPT NATIVE
- **Direct Execution:** Run TypeScript natively using `node --experimental-strip-types`. No need for `ts-node`, `tsx`, or `esbuild` for development.
- **Limitations:** Type-stripping only — no `enum`, `namespace`, or `const enum`. Use string union types as alternatives.
- **tsconfig:** Still required for editor support and strict type checking. Set `"target": "ES2024"`.

## 2. BUILT-IN SQLITE
- **Use Case:** Use the stable `node:sqlite` for fast, local data caching, test fixtures, or lightweight microservices instead of Redis when appropriate.
- **NOT For:** Do not use for production multi-user databases. SQLite is single-writer. Use MySQL/PostgreSQL for concurrent workloads.
- **WAL Mode:** Always enable WAL mode for concurrent read access: `db.pragma('journal_mode = WAL')`.

## 3. MODULE SYSTEM
- **100% ESM:** Zero tolerance for CommonJS (`require`). All new code must use `import/export`.
- **Package Defaults:** `"type": "module"` is expected. Dual-publishing (CJS + ESM) only for library authors.

## 4. SECURITY & PERMISSIONS
- **Permission Model (Stable):** Use `--permission` (no longer experimental) to restrict file system (`--allow-fs-read`, `--allow-fs-write`) and network access.
- **URLPattern:** Use the global `URLPattern` API for safe URL matching and routing instead of regex.

## 5. DIAGNOSTICS
- **Diagnostics Channel:** Use `node:diagnostics_channel` for lightweight, zero-overhead tracing and monitoring hooks.
- **Performance Hooks:** Leverage `node:perf_hooks` with `PerformanceObserver` for automated performance budgets.