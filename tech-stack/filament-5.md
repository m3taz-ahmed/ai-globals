[TECH] filament-5
[OBJ] Filament v5.x Architecture Rules.
[RULES]
1. [REQ] Islands: Livewire v4 independent renders. ⛔ waterfalls. Deferred filters for heavy queries.
2. [REQ] Async/Defer: `->deferLoading()`. Reverb/SSE for real-time. ⛔ client-side polling.
3. [REQ] Components: Scoped styles. v4 hooks (`@script`, `@assets`).
4. [REQ] State: PHP Enums for UI state. State < 50KB (Redis otherwise). Pass scalar IDs (⛔ full models).
5. [REQ] Static Props (Fatal Error Fix): Match exact union types when overriding static properties (e.g. `protected static string|BackedEnum|null $navigationIcon`). NO `?string`.
6. [REQ] JS-Only Actions in Notifications: When creating an Action inside a Notification that only executes JS (e.g. `window.navigator.clipboard`), do NOT embed HTML directly in the body (stripped by XSS sanitizer), and do NOT use `->url('#')` (triggers Livewire hashchange which clears password fields). Instead, use `->alpineClickHandler("JS_CODE_HERE")` on the `Action` object to ensure the JS is executed without mounting the action in Livewire (avoiding `MethodNotFoundException: mountAction` after serialization).
7. [REQ] `HasAvatar` + Strict Eloquent: In `getFilamentAvatarUrl()`, never access optional columns via `$this->avatar` when `Model::shouldBeStrict()` / `preventsAccessingMissingAttributes()` is active, or an un-reloaded model will throw `MissingAttributeException`. Use `data_get($this->getAttributes(), 'avatar')` (or a null-safe accessor) and pass the value to the URL helper.
8. [REQ] Livewire CSP-safe build: Filament v5 UI (e.g. `fi-theme-switcher`) uses Alpine `x-init` with arrow functions. The CSP-safe Alpine build (`LIVEWIRE_CSP_SAFE=true`) cannot parse these expressions and throws `CSP Parser Error: Unexpected token: PUNCTUATION ")"`, causing the page to mount nothing (blank). For local Filament development, set `LIVEWIRE_CSP_SAFE=false` in `.env`. Only enable `true` in production with a strict nonce-based CSP and verified CSP-compatible expressions.
