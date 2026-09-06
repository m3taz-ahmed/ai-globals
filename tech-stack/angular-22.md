[TECH] Angular 22 (latest 22.1.5, Aug 2026)
[OBJ] Enterprise TypeScript framework — Vitest default test runner, zoneless change detection default (zone.js removed), stable MCP server, signals-based standalone components.
[RULES]
1. [REQ] Zoneless change detection is the default — `zone.js` is no longer included. Use `provideZonelessChangeDetection()` (implicit in new projects); ensure all async uses signals, `async` pipe, or `ChangeDetectorRef.markForCheck()`.
2. [REQ] Use Vitest as the default test runner — `ng test` uses Vitest; configure `vitest.config.ts`. Karma/Jasmine removed from new project scaffolds.
3. [REQ] Use signals for all reactive state: `signal<T>()`, `computed()`, `effect()`. Never rely on Zone.js tick.
4. [REQ] Use `input()` / `output()` / `model()` signal functions — never `@Input()` / `@Output()` decorators.
5. [REQ] Standalone components are the only option — `NgModule` removed from new scaffolds. Use `provideRouter`, `provideHttpClient`, `provideZonelessChangeDetection` in `main.ts`.
6. [REQ] Use `inject()` function instead of constructor injection.
7. [REQ] Use functional guards/resolvers (`canMatch`, `canActivate`, `resolve`) with `inject()`.
8. [REQ] Use `provideHttpClient(withFetch())` + `withInterceptors()` for functional interceptors.
9. [REQ] Use `@defer` blocks for lazy-loading component subtrees.
10. [REQ] Use SSR with `provideServerRendering()` + `provideClientHydration()`; `afterNextRender()` for browser-only logic.
11. [REQ] Use `ChangeDetectionStrategy.OnPush` on all components.
12. [REQ] Use stable MCP server for AI tooling integration — expose Angular compiler metadata via MCP protocol.
13. [REQ] Use `resource()` / `httpResource()` for async data loading with signals.
14. [REQ] Use Angular CLI (`ng generate`, `ng build`) with esbuild/Vite builder; configure `budgets` in `angular.json`.
15. [PROHIBIT] Never use `NgModule`, `@Input()`/`@Output()` decorators, class-based guards/interceptors in new code.
16. [PROHIBIT] Never manually call `ChangeDetectorRef.detectChanges()` in zoneless apps — use signals.
17. [PROHIBIT] Never use `setTimeout`/`setInterval` for change detection triggers.
18. [PROHIBIT] Never assume Karma/Jasmine is available — Vitest is the default test runner.
19. [CMD] `ng new my-app` — scaffold (zoneless + Vitest defaults).
20. [CMD] `ng test` — runs Vitest.
[COMPAT]
- v22.0: Vitest default, zoneless default (zone.js removed), standalone-only.
- v22.1+: stable MCP server, performance/AI tooling improvements.
- Signals: `input()`, `output()`, `model()`, `resource()`, `httpResource()` stable.
- esbuild/Vite builder default.
[REFS]
- https://angular.dev/
- https://angular.dev/guide/signals
- https://angular.dev/guide/zoneless
- https://angular.dev/guide/testing
