[TECH] nativephp-mobile-4
[OBJ] NativePHP Mobile v4.x (SuperNative) — Build real native iOS/Android apps from Laravel + Blade. No web view. Blade → binary → SwiftUI/Jetpack Compose. 240fps+ native speed.
[RULES]
1. [REQ] Requirements: PHP 8.3+, Laravel 11+, Xcode 16+ (iOS), Android Studio (Android). macOS host for iOS builds. Verify via `composer.lock` (`[VER-01]`).
2. [REQ] Install: `composer require nativephp/mobile` → `php artisan native:install` → `php artisan native:run`. Launches on connected device/simulator.
3. [REQ] SuperNative = DEFAULT. New apps render native screens from first route — zero config. Web view is opt-out, not opt-in.
4. [REQ] Architecture: Swift/Kotlin shell + embedded PHP. NO web view (by default). Blade components → custom Blade engine → fixed-length byte array → native-side interpreter → SwiftUI (iOS) / Jetpack Compose (Android) UI tree.
5. [REQ] Three pillars of SuperNative: (1) Shared memory with PHP — no network round-trip, no serialization, no web-view bridge. State flows PHP↔native instantly. (2) Livewire-like components — PHP class holds state + behavior. (3) Blade EDGE components for DX.
6. [REQ] ⛔ SuperNative is NOT a transpiler. NOT HTML-to-native converter. NOT a custom VM. It is a binary protocol: PHP objects conforming to known interface → fixed-length byte array → explicit native interpreter.
7. [REQ] ⛔ SuperNative is NOT pixel-perfect cross-platform. It EMBRACES platform differences, smooths them with single EDGE syntax. SwiftUI + Compose render natively per platform.
8. [REQ] Routing: `Route::native('/path', ComponentClass::class)` in `routes/mobile.php`. Each route = one screen driven by PHP component. ⛔ NEVER use `Route::get()` for native screens — use `Route::native()`.
9. [REQ] Component class: `class HomeScreen extends NativeComponent { public string $title; public function mount() {...} public function render() { return view('home-screen'); } public function someAction() {...} }`. Livewire-like lifecycle.
10. [REQ] State reactivity: public properties auto-sync to native UI via shared memory. `$this->title = 'New'` → UI updates instantly. ⛔ NEVER mutate state outside component methods — no re-render trigger.
11. [REQ] Data binding: `<text-input :value="$title" wire:model="title" />` two-way binds. EDGE components accept PHP props directly.
12. [REQ] EDGE components (40+ shipped): Button, Text, Text Input, Toggle, Checkbox, Radio Group, Select, Slider, List, Virtual List, Lazy Grid, Scroll View, Stack, Row, Column, Modal, Bottom Sheet, Carousel, Tab Row, Bottom Navigation, Side Navigation, Top Bar, FAB, Icon, Image, Badge, Chip, Divider, Spacer, Progress Bar, Activity Indicator, Accordion, Canvas, Gesture Area, Pressable, Refreshable, Shapes, Web View (optional).
13. [REQ] Layout: `<stack>`, `<row>`, `<column>` for flexbox-like. `<scroll-view>` for scrollable. Safe area: `<safe-area>` wraps content to respect notches/home indicator.
14. [REQ] Nested components: compose EDGE components inside Blade. `<stack><text>Hello</text><button>Tap</button></stack>`. Max nesting depth enforced by renderer.
15. [REQ] Events: `wire:click`, `wire:press`, `wire:change`, `wire:focus`. Call component methods. `public function onClick() { $this->count++; }`.
16. [REQ] Gestures & animation: `<gesture-area>`, native animation APIs. Use platform gesture recognizers. ⛔ NEVER JS-based animation — use native.
17. [REQ] Theming: `Theme::light()` / `Theme::dark()` / `Theme::system()`. Custom colors via `Theme::colors(['primary' => '#...'])`. Platform-native theming (Material 3 on Android, SwiftUI tint on iOS).
18. [REQ] App icons: `php artisan native:icon` generates all required sizes from source. Splash screens: `php artisan native:splash`. ⛔ NEVER commit raw icons — generate from source.
19. [REQ] Assets: `public/` dir bundled. Reference via `asset('path')`. Large assets increase bundle — optimize/compress.
20. [REQ] SQLite ONLY. Same constraints as Desktop v2 (rule 16-20 of `nativephp-desktop-2`). Auto-migrate on version change. `php artisan native:migrate` in dev.
21. [REQ] Lifecycle hooks: `mount()`, `hydrate()`, `dehydrate()`, `updating()`, `updated()`, `render()`. Same as Livewire. Use for data loading + side effects.
22. [REQ] Queues: `php artisan native:queue` runs inside app. Background sync, API polling. ⛔ NEVER block UI thread — use queue for >100ms work.
23. [REQ] WebSockets: Laravel Reverb works locally inside app. Real-time updates from queue jobs to UI. Use for live data refresh.
24. [REQ] Deep links: `NATIVEPHP_DEEPLINK_SCHEME` env → `myapp://path`. Register in `routes/mobile.php`. Handle via component `mount()` reading URL params.
25. [REQ] Push notifications: Firebase Cloud Messaging (FCM) plugin. `php artisan native:plugin firebase`. Register device token → send via Laravel Notifications + FCM.
26. [REQ] Authentication: Sanctum tokens for API auth. SecureStorage plugin for token persistence. Biometrics plugin for local auth (Face ID / fingerprint).
27. [REQ] Security: `Security::encrypt()` / `Security::decrypt()`. SecureStorage plugin for secrets (tokens, keys). ⛔ NEVER store tokens in plain SQLite — use SecureStorage.
28. [REQ] Native functions: `Device::info()`, `File::read()/write()`, `System::openUrl()`, `Dialog::alert()/confirm()`, `Share::text()/file()`, `Geolocation::current()`, `Camera::capture()`, `Microphone::record()`, `Scanner::scan()`, `Network::online()`, `Browser::open()`, `Biometrics::authenticate()`, `Flashlight::on()/off()`, `Haptic::feedback()`.
29. [REQ] Plugins system: `php artisan native:plugin <name>`. Core plugins: Biometrics, Browser, Camera, Firebase, Geolocation, Microphone, Network, Scanner, SecureStorage, Share, Vibe (haptics). Premium plugins via NativePHP Ultra.
30. [REQ] Plugin structure: `Plugin::register()` + `Plugin::boot()` two-phase (Filament pattern). Bridge functions: Swift/Kotlin ↔ PHP via typed bridge. UI component plugins: ship EDGE components.
31. [REQ] Plugin permissions: declare in `plugin.json` `permissions` + `dependencies`. iOS: Info.plist usage strings. Android: AndroidManifest permissions. ⛔ NEVER request permission without usage explanation — App Store/Play reject.
32. [REQ] Plugin testing: `NativePHP\Testing\PluginTestCase`. Mock bridge functions. Test lifecycle (register→boot). Test permission denial flow.
33. [REQ] Testing: `NativePHP\Testing\NativeTestClass` for interactions (tap, swipe, type). Navigation flows. Accessibility assertions. Native events + bridge mocking. Two-tier FAST/FULL (`[TEST-07]`).
34. [REQ] Testing commands: FAST `php artisan test --filter=Native` / FULL `php artisan test`. Test on simulator + real device before release.
35. [REQ] Opt-out of SuperNative (web view mode): `Route::native('/home', WebViewScreen::class)` + `<webview php url="/" fullscreen />` + `NATIVEPHP_START_URL=/home`. Adopt native one screen at a time.
36. [REQ] Jump preview tool: test on real devices without Xcode/Android Studio. Test premium plugins. Free. Use for rapid iteration before full build.
37. [REQ] Bifrost cloud build: `bifrost build` → cloud builds iOS + Android. No local Xcode/Android Studio needed for CI. Plans from $10/mo. Use for release builds.
38. [REQ] Publishing Android: `php artisan native:build android` → AAB. Upload to Play Console. Target API level per Play requirements. Sign with upload key. ⛔ NEVER ship debug-signed to Play.
39. [REQ] Publishing iOS: `php artisan native:build ios` → IPA. Upload via Transporter or `xcrun altool`. Sign with Apple Developer ID + provisioning profile. Notarization required. ⛔ NEVER ship without App Store profile.
40. [REQ] Bundle size: mobile apps <50MB target. Ships as single executable. Optimize assets. Lazy-load heavy screens. Strip unused plugins.
41. [REQ] Performance: native views render at platform speed (240fps+ headroom). No web view startup cost. No DOM. No JS bridge. Scrolling/transitions/gestures = native feel.
42. [REQ] Accessibility: SwiftUI + Jetpack Compose built-in a11y. Screen readers, dynamic type, contrast, assistive controls work out of box. ⛔ NEVER break a11y with custom low-level rendering.
43. [REQ] Cross-platform: single Blade → SwiftUI (iOS) + Compose (Android). No separate syntax per platform. EDGE smooths differences.
44. [REQ] Composer packages: (almost) any package works. ⛔ Avoid server-only extensions. Test in `native:run` before relying.
45. [REQ] Threading model: PHP on main thread for UI state. Background work via queue. Shared memory boundary — no locks needed for state reads. ⛔ NEVER spawn threads from PHP — use queue.
46. [REQ] Subtree reuse: renderer reuses unchanged subtrees. Minimize state changes for perf. Key lists with stable IDs for diff efficiency.
47. [REQ] Embedded PHP: statically-compiled PHP binary inside app. Custom PHP extension for native bridges. Subset of extensions — verify availability.
48. [REQ] Context7 MCP: query `nativephp/mobile` docs before implementation. `mcp_call_tool(context7, resolve-library-id, {libraryName: "nativephp/mobile"})` then `get-library-docs`.
49. [REQ] Version compat: Mobile v4 = SuperNative (breaking from v1-3 web-view default). v1-3 apps: use `WebViewScreen` opt-out for backward compat. ⛔ NEVER mix v4 EDGE APIs with v1-3 patterns.
50. [REQ] aiZee workflow: query `workflows/27-nativephp-app-development.md` for full dev lifecycle. Query `nativephp-desktop-2` tech-stack if desktop target. Detect target from `composer.lock` (`nativephp/mobile` vs `nativephp/desktop`).
