[TECH] Vite 8
[OBJ] Vite 8.x (released Mar 2026, latest 8.2.2 Aug 2026). Rolldown as unified Rust-based bundler (replaces ESBuild + Rollup), 10-30x faster builds, full plugin compatibility, browser console forwarding.
[RULES]
1. [REQ] Use Rolldown (unified Rust bundler) for both dev transform + prod bundling. Replaces ESBuild (dev) + Rollup (prod). Full Rollup plugin compatibility — existing plugins work unchanged.
2. [REQ] Expect 10-30x faster production builds vs Vite 7 (Rollup). Benchmark before/after migration: `vite build` time should drop significantly.
3. [REQ] Use browser console output forwarding: `console.log` / `console.error` / `console.warn` in browser auto-forward to dev server terminal with source mapping. No manual `vite-plugin-terminal` needed.
4. [REQ] Use `vite.config.ts` with `defineConfig` from `vite`. Plugins via `plugins: []` array — Rollup plugins compatible via `vite-plugin-rollup-compat` (auto-detected).
5. [REQ] Use `import.meta.env.VITE_*` for env variables (prefixed `VITE_`). Access via `import.meta.env.MODE`, `import.meta.env.DEV`, `import.meta.env.PROD`.
6. [REQ] Use `public/` for static assets (copied as-is). Use `src/assets/` for processed assets (imported, hashed).
7. [REQ] Use `vite dev` for dev server (HMR via native ESM + Rolldown). `vite build` for production. `vite preview` to preview production build.
8. [REQ] Use `vite-plugin-react` (@vitejs/plugin-react) for React projects with Fast Refresh. Use `vite-plugin-vue` for Vue 3.
9. [REQ] Use code splitting via dynamic `import()`. Rolldown handles chunking automatically; configure `build.rollupOptions.output.manualChunks` for custom splits.
10. [REQ] Use CSS modules (`.module.css`), CSS preprocessors (Sass, Less), PostCSS via `postcss.config.js`. Tailwind via `@tailwindcss/vite` plugin.
11. [REQ] Use `vite/ssr` / `vite/server` for SSR: `createServer({ server: { middlewareMode: true } })`. Integrate with Express/Fastify/Hono.
12. [REQ] Use environment API (`vite-environment`) for multi-environment builds (client, SSR, worker) in single config.
13. [REQ] Use `define` for global constants: `define: { __APP_VERSION__: JSON.stringify(version) }`.
14. [REQ] Use `resolve.alias` for path aliases: `resolve: { alias: { "@": "/src" } }`. Or use `tsconfig.json` `paths` with `vite-tsconfig-paths`.
15. [REQ] Use `build.target` for browser targets: `build: { target: "es2024" }`. Use `build.minify: "oxml"` (Oxc minifier, default) or `"esbuild"`.
16. [CMD] `npm create vite@latest` scaffold new project (React, Vue, Svelte, Vanilla, Lit templates).
17. [CMD] `vite build --mode production` explicit production build.
18. [CMD] `vite optimize` pre-bundle dependencies manually.
19. [PROHIBIT] Never use `require()` in Vite ESM code — use `import`.
20. [PROHIBIT] Never import from `devDependencies` in production code — tree-shaking may fail.
21. [PROHIBIT] Never disable HMR (`server.hmr: false`) in dev without reason — core DX feature.
22. [PROHIBIT] Never use Webpack-specific loaders (`style-loader`, `css-loader`) — use Vite native CSS handling.
[COMPAT]
- Vite 8.x (released Mar 2026, latest 8.2.2 Aug 2026).
- Rolldown 1.x (Rust bundler, replaces ESBuild + Rollup).
- Node.js 20.19+ / 22.12+ required.
- 41.6M weekly npm downloads.
- Plugin compat: Rollup plugins work via adapter; Vite 7 plugins mostly compatible.
- Frameworks: React 19, Vue 3.5+, Svelte 5, Solid, Lit.
[REFS]
- https://vite.dev/guide/
- https://vite.dev/blog/vite-8
- https://rolldown.rs/
- https://github.com/vitejs/vite
