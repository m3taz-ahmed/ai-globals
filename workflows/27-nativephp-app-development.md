[WORKFLOW] 27-nativephp-app-development
[OBJ] Full lifecycle for building native desktop/mobile apps with NativePHP (Laravel). Detect target (Desktop v2 / Mobile v4 SuperNative), scaffold, develop, test, publish.
[TRIGGER] /nativephp, /native-php, /native-app, /desktop-app, /mobile-app, /supernative, /electron-laravel, /blade-native
[RULES]
1. [REQ] Detect target: read `composer.lock` → grep `nativephp/desktop` (Desktop v2) or `nativephp/mobile` (Mobile v4). Load matching `tech-stack/nativephp-{desktop-2|mobile-4}.md` (`[VER-01]`). ⛔ NEVER assume target — both can coexist but APIs differ.
2. [REQ] Query Context7 MCP before implementation: `mcp_call_tool(context7, resolve-library-id, {libraryName: "nativephp/desktop"})` or `{libraryName: "nativephp/mobile"}` then `get-library-docs` with full question.
3. [REQ] Verify requirements: PHP 8.3+, Laravel 11+, Node 22+ (Desktop). Xcode 16+ (iOS), Android Studio (Android) for Mobile. macOS host for iOS builds.
4. [REQ] Install: `composer require nativephp/{desktop|mobile}` → `php artisan native:install` → `php artisan native:run`. Run in browser FIRST before `native:run` (Desktop).
5. [REQ] `config/nativephp.php`: set `app_id` (reverse-domain unique), `version` (semantic), `deeplink_scheme`, `provider` (NativeAppServiceProvider). Configure `cleanup_env_keys` + `cleanup_exclude_files` for production.
6. [REQ] `NativeAppServiceProvider::boot()`: configure windows (Desktop) / routes (Mobile), menus, hotkeys, notifications, tray (Desktop). ⛔ Bootstrap only — no business logic.
7. [REQ] Desktop: window management via `Window::open()`, menus via `Menu::make()`, tray via `SystemTray`, hotkeys via `Hotkey::register()`. Single instance via `Native::singleInstance()`.
8. [REQ] Mobile: routing via `Route::native('/path', ComponentClass::class)` in `routes/mobile.php`. Each screen = PHP component (Livewire-like). SuperNative is DEFAULT — no web view unless opt-out.
9. [REQ] Mobile components: `class XScreen extends NativeComponent` with `mount()`, `render()`, action methods. Public properties auto-reactive via shared memory. `<text-input wire:model="prop" />` two-way binds.
10. [REQ] Mobile EDGE components: use shipped 40+ (Button, List, Modal, Carousel, etc.). Compose via `<stack><row><column>`. Safe area: `<safe-area>`. ⛔ NEVER use HTML tags — EDGE only.
11. [REQ] SQLite ONLY. Auto-created in user appdata. Auto-migrate on version change. Dev: `php artisan native:migrate` / `native:migrate:fresh` (destructive) / `native:seed`.
12. [REQ] SQLite migration constraints: enable FK via `Schema::enableForeignKeyConstraints()`. No `enum` without cast. No `json` column — use `text` + cast. Test migrations on SQLite specifically before release.
13. [REQ] ⛔ NEVER store critical app-state in same DB as user data. Use file storage (JSON) for app-state. If DB corrupts, app won't start.
14. [REQ] File storage: `File::put/get/exists/delete` + `Native::userPath()` for appdata. ⛔ NEVER write system dirs without consent.
15. [REQ] Queues: `php artisan native:queue` inside app. Background sync, API polling, file processing. ⛔ NEVER block UI thread >100ms — use queue.
16. [REQ] Broadcasting: Laravel Reverb for real-time UI updates from queue jobs. WebSocket PHP↔Chromium (Desktop) / shared-memory (Mobile).
17. [REQ] Security: `Security::encrypt/decrypt` for app-level. Mobile: SecureStorage plugin for tokens/keys. Biometrics plugin for local auth. ⛔ NEVER store secrets in plain SQLite.
18. [REQ] Mobile plugins: `php artisan native:plugin <name>`. Core: Biometrics, Camera, Geolocation, Firebase, SecureStorage, Share, Scanner, Microphone, Network, Browser, Vibe. Declare permissions + dependencies in `plugin.json`.
19. [REQ] Mobile plugin permissions: iOS Info.plist usage strings + Android AndroidManifest permissions. ⛔ NEVER request without usage explanation — store rejection.
20. [REQ] Deep links: `NATIVEPHP_DEEPLINK_SCHEME` env → `myapp://path`. Register handler. ⛔ NEVER use common schemes (`http`, `mailto`).
21. [REQ] Push notifications (Mobile): Firebase plugin. Register device token → Laravel Notifications + FCM.
22. [REQ] Testing: Pest/PHPUnit for logic. `NativePHP\Testing\NativeTestClass` for interactions (tap, swipe, type), navigation flows, accessibility, native events, bridge mocking. Two-tier FAST/FULL (`[TEST-07]`).
23. [REQ] Testing commands: FAST `php artisan test --filter=Native` / FULL `php artisan test`. Test on simulator + real device before release (Mobile).
24. [REQ] Cross-platform testing (Desktop): test Win/macOS/Linux. Menu bar macOS-only. Tray behavior differs. File paths differ. Use `Native::userPath()` not hardcoded.
25. [REQ] Build: `php artisan native:build` → platform installer (Desktop: exe/dmg/deb) or AAB/IPA (Mobile). Bifrost cloud build for Mobile CI ($10/mo).
26. [REQ] Publishing Desktop: code-sign per platform. macOS Apple Developer ID + notarization. Windows code-signing cert. ⛔ NEVER ship unsigned — SmartScreen/Gatekeeper blocks.
27. [REQ] Publishing Android: AAB → Play Console. Target API per Play requirements. Sign with upload key. ⛔ NEVER debug-signed to Play.
28. [REQ] Publishing iOS: IPA → Transporter/altool. Apple Developer ID + provisioning profile + notarization. ⛔ NEVER without App Store profile.
29. [REQ] Updater (Desktop): `updater.enabled` in config. Providers: github/s3/spaces. Auto-check on start. Increment `version` per release. ⛔ NEVER expose updater token in client.
30. [REQ] Bundle size: Desktop <150MB (Electron base ~80-120MB). Mobile <50MB (single executable). Optimize assets. Strip unused plugins. Lazy-load screens.
31. [REQ] Performance: Desktop — no network latency (local PHP) but Chromium memory ~150-300MB. Profile DevTools. Mobile — native speed 240fps+, no web view. Minimize state changes for subtree reuse.
32. [REQ] Accessibility (Mobile): SwiftUI + Compose built-in a11y. Screen readers, dynamic type, contrast work out of box. ⛔ NEVER break with custom low-level rendering.
33. [REQ] Opt-out SuperNative (Mobile v1-3 compat): `Route::native('/home', WebViewScreen::class)` + `<webview php url="/" fullscreen />` + `NATIVEPHP_START_URL=/home`. Adopt native one screen at a time.
34. [REQ] Context7 MCP: query before ANY implementation. `resolve-library-id` then `get-library-docs` with full question. Live docs > LLM memory.
35. [REQ] aiZee integration: query `nativephp-{desktop-2|mobile-4}` tech-stack. Query `backend-frameworks-lord` skill for Laravel patterns. Query `laravel-testing` + `laravel-security` tech-stacks.
36. [REQ] Quality: run `pint`, `phpstan --level=8`, `php artisan test --filter=Native` (FAST) during iteration. Full suite before done. Query `laravel-testing` tech-stack.
37. [REQ] Security: query `laravel-security` tech-stack. FormRequest validation. RBAC. Parameterized queries. `$fillable` whitelist. ⛔ NEVER raw SQL, NEVER `$guarded=[]`.
38. [REQ] Version detection: `composer.lock` → `nativephp/desktop` version → `tech-stack/nativephp-desktop-2.md`. `nativephp/mobile` version → `tech-stack/nativephp-mobile-4.md`. ⛔ NEVER default — read lockfile.
39. [REQ] Frontend freedom (Desktop): React, Vue, Livewire, Inertia, Alpine, plain HTML/CSS. NativePHP is NOT a GUI framework. Mobile: EDGE components only (SuperNative) OR web view opt-out.
40. [REQ] Cleanup: delete temp/scratch files. `git add <file>` only modified files. ⛔ NEVER `git add .`/`git add -A` (`[GIT-06]`). No commit/push without approval.
