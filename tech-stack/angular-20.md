[TECH] Angular 20
[OBJ] Enterprise TypeScript framework with signals, standalone components, zoneless change detection, hydration, and SSR.
[RULES]
1. [REQ] Use standalone components (`@Component({ standalone: true })` is default in v20); never use `NgModule` for new code — use `provideRouter`, `provideHttpClient`, `provideZonelessChangeDetection` in `main.ts`.
2. [REQ] Use signals for all reactive state: `signal<T>()` for writable state, `computed()` for derived values, `effect()` for side-effects.
3. [REQ] Use `input()` / `output()` signal functions instead of `@Input()` / `@Output()` decorators: `count = input(0)`, `clicked = output<void>()`.
4. [REQ] Use `model()` for two-way bindable signal inputs: `value = model<T>()` replaces `@Input()` + `@Output()` + `EventEmitter`.
5. [REQ] Enable zoneless change detection with `provideZonelessChangeDetection()` in providers; ensure all async operations use signals, `async` pipe, or `ChangeDetectorRef.markForCheck()` — never rely on Zone.js tick.
6. [REQ] Use `@Injectable({ providedIn: "root" })` for singleton services; use `providedIn: "any"` only for per-lazy-module instances.
7. [REQ] Use functional guards and resolvers (`canMatch`, `canActivate`, `resolve`) with `inject()` — never use class-based `CanActivate` / `Resolve` (deprecated).
8. [REQ] Use `provideHttpClient(withFetch())` for `HttpClient` (fetch backend is default in v20); use `withInterceptors()` for functional interceptors instead of class-based `HttpInterceptor`.
9. [REQ] Use `@defer` blocks for lazy-loading component subtrees: `@defer (when condition) { <HeavyComponent /> } @placeholder { ... } @loading { ... } @error { ... }`.
10. [REQ] Use SSR with `provideServerRendering()` and `provideClientHydration()`; use `afterNextRender()` for browser-only logic to avoid hydration mismatches.
11. [REQ] Use `inject()` function instead of constructor injection for new code: `private api = inject(ApiService)` — enables better tree-shaking and testability.
12. [REQ] Use Angular CLI (`ng generate`, `ng build`) with esbuild / Vite builder; configure `budgets` in `angular.json` to fail builds on bundle size regressions.
13. [REQ] Use `ChangeDetectionStrategy.OnPush` on all components; with zoneless, components are only checked when their signals change.
14. [PROHIBIT] Never use `NgModules`, `@Input()` / `@Output()` decorators, or class-based guards / resolvers / interceptors in new code — use the signal / functional equivalents.
15. [PROHIBIT] Never manually call `ChangeDetectorRef.detectChanges()` in zoneless apps — use signals to trigger updates. Never use `setTimeout` / `setInterval` for change detection triggers.
[COMPAT]
- v20.0: Signals stable, zoneless GA, standalone-only, `input()` / `output()` / `model()` stable, esbuild default, hydration GA.
- v20.1+: `resource()` / `httpResource()` for async data loading with signals, deferred loader support.
[REFS]
- https://angular.dev/
- https://angular.dev/guide/signals
- https://angular.dev/guide/zoneless
