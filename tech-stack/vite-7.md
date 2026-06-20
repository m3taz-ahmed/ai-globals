[TECH] vite-7
[OBJ] Vite v7.x Standards.
[RULES]
1. [REQ] Bundling: `type: "module"`. Tailwind CSS 4 (PostCSS optional).
2. [REQ] Perf: Dynamic imports. `esbuild` for minification. `build.assetsInlineLimit` for small assets.
3. [REQ] Laravel: `laravel-vite-plugin` ^2.0. `refresh: true`. `@` alias.
4. [REQ] Env: `VITE_` prefix. Source maps in dev ONLY.
