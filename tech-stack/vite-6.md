[TECH] vite-6
[OBJ] Vite 6.x Build Standards.
[RULES]
1. [REQ] Config: `laravel-vite-plugin`. `import.meta.env` (prefix `VITE_`).
2. [REQ] Dev: HMR via `@vite` in layout. `npm run dev`.
3. [REQ] Prod: Code splitting (`import()`). Tree shaking (Rollup).
4. [PROHIBIT] Constraints: ⛔ NO Webpack/Laravel Mix. ⛔ NO external CDNs in dev (bundle all).
