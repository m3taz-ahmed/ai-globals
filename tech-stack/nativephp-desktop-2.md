[TECH] nativephp-desktop-2
[OBJ] NativePHP Desktop v2.x — Build cross-platform desktop apps with Laravel + Electron + static PHP binary. No server, no network required on user device.
[RULES]
1. [REQ] Requirements: PHP 8.3+, Laravel 11+, Node 22+, Win10+/macOS12+/Linux. Verify via `composer.lock` + `node --version` before install (`[VER-01]`).
2. [REQ] Install: `composer require nativephp/desktop` → `php artisan native:install` → `php artisan native:run`. Installer publishes `NativeAppServiceProvider` + `config/nativephp.php` + registers `post-update-cmd`.
3. [REQ] Run in browser FIRST before `native:run`. Exceptions harder to spot in Electron context. Fix web-mode errors first.
4. [REQ] Architecture: Electron shell + statically-compiled PHP binary bundled inside app. PHP runtime + Laravel routes run on user device via authenticated HTTP bridge to Chromium window. No external server.
5. [REQ] `config/nativephp.php` keys: `version` (increment per release), `app_id` (reverse-domain `com.vendor.app`), `deeplink_scheme`, `author`, `copyright`, `description`, `website`, `provider` (NativeAppServiceProvider), `cleanup_env_keys`, `cleanup_exclude_files`, `updater`.
6. [REQ] `app_id` MUST be unique reverse-domain. Set via `NATIVEPHP_APP_ID` env. ⛔ NEVER reuse another app's ID — OS conflicts on install/update.
7. [REQ] `NativeAppServiceProvider::boot()` configures windows, menus, global hotkeys, notifications, system tray. ⛔ NEVER put business logic in provider — bootstrap only.
8. [REQ] Window management: `Native::window()` / `Window::open()->width()->height()->minWidth()->resizable()->focusable()`. Single main window by default. Multi-window via `Window::open()` per feature.
9. [REQ] Menu management: `Menu::make()` + `MenuItem::label()->shortcut()->onClick()`. Application menu (macOS), window menu (Win/Linux). `Menu::app()` for app-level. `Menu::bar()` for menu bar.
10. [REQ] System tray: `SystemTray::icon()->tooltip()->menu()`. Use for background apps. ⛔ NEVER leave tray icon without exit menu item.
11. [REQ] Global hotkeys: `Hotkey::register('CommandOrControl+Shift+X', fn() => ...)`. Register in provider `boot()`. Unregister on `Window` close. ⛔ NEVER conflict with OS reserved shortcuts.
12. [REQ] Notifications: `Notification::title()->body()->image()->show()`. Native OS notifications. Requires permission on macOS. ⛔ NEVER spam — rate-limit.
13. [REQ] Clipboard: `Clipboard::text()` read / `Clipboard::text($value)` write. Plain text only. ⛔ NEVER write secrets to clipboard.
14. [REQ] Dialogs: `Dialog::open()->filter()->multiple()` / `Dialog::save()` / `Dialog::message()->title()->body()`. Native file pickers + message boxes. Await async result.
15. [REQ] Settings persistence: `Settings::set('key', $value)` / `Settings::get('key', $default)`. Stored in user appdata. Use for app preferences (theme, window position, last-opened).
16. [REQ] SQLite ONLY out of the box. NativePHP auto-creates DB in user `appdata` dir. Auto-runs migrations on version change. ⛔ NEVER bundle MySQL/PostgreSQL — footprint too large.
17. [REQ] Dev DB: `nativephp.sqlite` in build dir. NativePHP forces this DB inside Electron to avoid clobbering other SQLite files. Migrate manually: `php artisan native:migrate`.
18. [REQ] Migrations: test on SQLite specifically. Enable foreign keys: `Schema::enableForeignKeyConstraints()` or `PRAGMA foreign_keys=ON`. ⛔ NEVER assume MySQL-only column types work (no `enum` without cast, no `json` — use `text` + cast).
19. [REQ] Refresh dev DB: `php artisan native:migrate:fresh` — DESTRUCTIVE, deletes all data. Seed: `php artisan native:seed`.
20. [REQ] ⛔ NEVER store critical app-state metadata in same DB as user data. If DB corrupts, app won't start. Use file storage (JSON/CSV) for app-state. User data in DB.
21. [REQ] File storage: `File::put()`, `File::get()`, `File::exists()`, `File::delete()`. User appdata dir via `Native::userPath()`. ⛔ NEVER write to system dirs without explicit user consent.
22. [REQ] Child processes: `Process::run(['command', 'arg'])` / `Process::start()` for async. Capture stdout/stderr. ⛔ NEVER run untrusted user input as command — injection risk.
23. [REQ] Power monitor: `PowerMonitor::on('suspend', fn)` / `on('resume', fn)` / `on('lock-screen', fn)`. Save state on suspend. Sync on resume.
24. [REQ] Screens: `Screen::all()` for multi-monitor. `Screen::primary()`. Window positioning per screen. ⛔ NEVER hardcode coordinates — use screen-relative.
25. [REQ] Shell: `Shell::openExternal($url)` for OS default browser. `Shell::showItemInFolder($path)`. ⛔ NEVER `Shell::openExternal` with untrusted URL — validate scheme (https only).
26. [REQ] Environment files: `.env` loaded normally in dev. On production build, `cleanup_env_keys` strips secrets (AWS_*, GITHUB_*, *_SECRET, etc.). ⛔ NEVER commit `.env` with production secrets.
27. [REQ] `cleanup_exclude_files` removes `storage/app/framework/{sessions,testing,cache}`, `storage/logs/laravel.log`, `content` from production bundle. Extend for project-specific scratch dirs.
28. [REQ] Queue worker: `php artisan native:queue` runs inside Electron. Use for background jobs (sync, API polling, file processing). ⛔ NEVER long-running blocking jobs on main thread — freeze UI.
29. [REQ] Broadcasting: Laravel Reverb/Pusher works locally. WebSocket between PHP runtime + Chromium. Use for real-time UI updates from background jobs.
30. [REQ] Security: `Security::encrypt($value)` / `Security::decrypt($value)`. App-level encryption key per install. ⛔ NEVER hardcode encryption key — use generated key in appdata.
31. [REQ] PHP binaries: `php artisan native:php` commands. Custom PHP extensions via `config/nativephp.php` `php_extensions`. ⛔ NEVER assume all extensions available — static-compiled subset only.
32. [REQ] Build: `php artisan native:build` produces platform installer (Win `.exe`/`.msi`, macOS `.dmg`, Linux `.deb`/`.AppImage`). Requires Electron builder config.
33. [REQ] Publishing: code-sign per platform. macOS: Apple Developer ID + notarization. Windows: code-signing cert. Linux: optional. ⛔ NEVER ship unsigned in production — SmartScreen/Gatekeeper blocks.
34. [REQ] Updater: `updater.enabled` in config. Providers: `github` (GitHub Releases), `s3`, `spaces` (DigitalOcean). Auto-check on app start. `NATIVEPHP_UPDATER_ENABLED=true` in prod.
35. [REQ] Updater GitHub config: `repo`, `owner`, `token`, `vPrefixedTagName`, `private`, `channel` (latest/beta), `releaseType` (draft/published). ⛔ NEVER expose token in client — use CI-injected env.
36. [REQ] Versioning: increment `version` in `config/nativephp.php` per release. Updater compares versions. Semantic versioning (`MAJOR.MINOR.PATCH`).
37. [REQ] Debugging: `php artisan native:serve` runs PHP + Electron separately for dev. DevTools: `Ctrl+Shift+I` (Win/Linux) / `Cmd+Option+I` (macOS). Log to `storage/logs/laravel.log`.
38. [REQ] Testing: Pest/PHPUnit for Laravel logic. `NativePHP\Testing\NativeTestClass` for window/menu/hotkey assertions. Test migrations on SQLite specifically. Two-tier FAST/FULL (`[TEST-07]`).
39. [REQ] Testing commands: FAST `php artisan test --filter=Native` / FULL `php artisan test`. Test `native:migrate` runs without error. Test `NativeAppServiceProvider::boot()` no exceptions.
40. [REQ] Frontend freedom: use any JS framework (React, Vue, Livewire, Inertia, Alpine, plain HTML/CSS). NativePHP is NOT a GUI framework. ⛔ NEVER let NativePHP dictate frontend choice.
41. [REQ] Composer packages: (almost) any package works. ⛔ Avoid packages requiring server-only PHP extensions (e.g., `imagick` if not in static build). Test in `native:run` before relying.
42. [REQ] Deep links: `deeplink_scheme` in config → `myapp://path` opens app. Register handler in provider. ⛔ NEVER use common schemes (`http`, `mailto`) — OS conflict.
43. [REQ] App lifecycle: `Native::on('window-opened')`, `on('window-closed')`, `on('app-ready')`, `on('before-quit')`. Save state on `before-quit`. Cleanup on `window-closed`.
44. [REQ] Single instance: `Native::singleInstance()` prevents multiple app instances. Redirect args to existing instance via `second-instance` event. ⛔ NEVER allow multi-instance unless explicitly designed.
45. [REQ] Auto-launch: `Native::autoLaunch()->enable()/disable()`. OS login item. Ask user permission first. ⛔ NEVER enable without consent.
46. [REQ] Bundle size: Electron ~80-120MB base. Minimize via `cleanup_exclude_files`. Strip `node_modules` devDeps. Tree-shake frontend. Target <150MB total.
47. [REQ] Performance: PHP runs locally — no network latency. But Electron Chromium memory ~150-300MB. Profile with DevTools. Lazy-load heavy views. ⛔ NEVER load all routes eagerly in SPA.
48. [REQ] Context7 MCP: query `nativephp/desktop` docs before implementation. `mcp_call_tool(context7, resolve-library-id, {libraryName: "nativephp/desktop"})` then `get-library-docs`.
49. [REQ] Cross-platform testing: test on all 3 OS (Win/macOS/Linux). Menu bar macOS-only. Tray behavior differs. File paths differ (`\` vs `/`). Use `Native::userPath()` not hardcoded.
50. [REQ] aiZee workflow: query `workflows/27-nativephp-app-development.md` for full dev lifecycle. Query `nativephp-mobile-4` tech-stack if mobile target. ⛔ NEVER mix Desktop + Mobile APIs without checking version compat.
