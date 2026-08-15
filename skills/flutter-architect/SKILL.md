---
name: flutter-architect
description: Principal Flutter Architect — full-stack design + develop. Dart 3.13, Flutter 3.47, Material 3, Riverpod/BLoC, go_router, 60 FPS, cross-platform (iOS/Android/web/desktop), CI/CD, testing.
---
[SKILL] flutter-architect
[OBJ] Architect, design, build, profile, and ship production-grade Flutter apps across iOS, Android, web, and desktop from a single Dart codebase — owning both the visual layer (design system, theming, motion, accessibility) and the engineering layer (state, architecture, networking, persistence, testing, CI/CD).
[PERSONAS] MOBILE (primary), UX (primary), ARCH (secondary), DEV (secondary).
[SUB-SKILLS] `flutter-design` (UX/visual layer), `flutter-developer` (engineering layer).

[RULES]
1. [CMD] Context7 IDs: Flutter `/flutter/website`; Flutter API `/websites/api_flutter_dev`; Flutter Packages `/flutter/packages`; Dart `/dart-lang/site-www`; Riverpod `/riverpod/riverpod`; go_router `/flutter/packages` (go_router subpath); BLoC `/felangel/bloc`; Freezed `/rrousselGit/freezed`; Drift `/simolus3/drift`.
2. [REQ] `[VER-01]` Pin to lockfile exact versions. Read `pubspec.lock` -> grep `flutter:` `sdk:` `dart:` -> load `tech-stack/flutter-<ver>.md`. NEVER assume Flutter version; default reference is Flutter 3.47 / Dart 3.13 (Aug 2026). Material 3 is default ON since Flutter 3.16 — never set `useMaterial3: false` without justification.
3. [REQ] Project anatomy (feature-first): `lib/{core,features,config,l10n,routing}`; one feature = one folder with `data/` (models, datasources, repos), `domain/` (entities, repo interfaces, usecases), `presentation/` (widgets, pages, controllers). Keep `main.dart` < 30 lines; app entry only.
4. [REQ] Architecture: clean-ish layering (presentation -> domain -> data). Dependency rule: presentation depends on domain, data depends on domain, domain depends on nothing. No `BuildContext` in domain/data. No business logic in `build()`.
5. [REQ] State management decision tree: local ephemeral UI state -> `setState`/`ValueNotifier`; scoped shared state -> Riverpod (prefer `Notifier`/`AsyncNotifier` + `ref.watch`/`ref.read`, avoid legacy `StateProvider` for complex state); event-driven / strict separation / large teams -> BLoC (Cubit for simple). NEVER use InheritedWidget manually for app state. NEVER mix `setState` with a global store.
6. [REQ] Immutability: models via `freezed` + `json_serializable`; `const` constructors everywhere possible; `@immutable` on widgets holding mutable fields flagged. Use Dart 3.13 primary constructors for concise immutable data classes when language version >= 3.1.
7. [REQ] Routing: `go_router` for all non-trivial apps. Declarative routes with typed `GoRoute` + `ShellRoute` for nested nav; `redirect` for auth guards; `extra` for typed args (define route-arg classes, never raw `Map`). Use `PopScope` (NOT deprecated `WillPopScope`) for Android predictive back (Android 14+).
8. [REQ] Theming & design system: single `ThemeData` via `ColorScheme.fromSeed()` + `TextTheme` (GoogleFonts or bundled fonts); expose via `Theme.of(context)` ONLY — no hardcoded `Color(0x...)` in widgets. Support light + dark + system. Define spacing/radius/elevation tokens as constants or `ThemeExtension`. See `flutter-design` for full design-system rules.
9. [REQ] Networking: `dio` (interceptors: auth, logging, retry) or `http` for simple; deserialize via `freezed` + `json_serializable`; repository pattern wraps datasources; never call HTTP from widgets. Handle loading/error/empty states explicitly in every async view.
10. [REQ] Persistence: `drift` (typed SQLite), `hive`/`isar` for KV, `shared_preferences` for primitives only. Local-first with conflict resolution for offline apps; encrypt sensitive stores (`flutter_secure_storage`).
11. [REQ] Performance budget: 60 FPS (16.6 ms/frame); profile with Flutter DevTools (Performance + CPU/Memory tabs). Use `const` widgets, `RepaintBoundary` around animations, `ListView.builder` (never `ListView(children:)` for >20 items), `itemExtent` when known, `AutomaticKeepAliveClientMixin` sparingly. Avoid rebuilds: scope `Consumer`/`Selector` to the smallest subtree; prefer `ref.watch` in leaf widgets.
12. [REQ] Accessibility: `Semantics` on custom gesture widgets; respect `MediaQuery.textScaler` (never fixed font sizes); large-tap-targets >= 48x48 dp; test with TalkBack + VoiceOver; `ExcludeSemantics` only when overriding. WCAG AA contrast via `ColorScheme`.
13. [REQ] Testing two-tier `[TEST-07]`: FAST -> `flutter test test/path/to/touched_test.dart` (~5s); FULL -> `flutter test --coverage` (target >= 80% logic, >= 70% total) + `flutter test integration_test/`. Widget tests via `testWidgets` + `WidgetTester`; mock with `mocktail` (Dart-friendly, no annotation boilerplate). One behavior per test (AAA). No hardcoded IDs/dates — use factories.
14. [REQ] CI/CD: GitHub Actions / Codemagic / Fastlane. Lanes: `analyze` (`flutter analyze --fatal-infos`), `format` (`dart format --set-exit-if-changed`), `test`, `build` (per platform), `deploy`. Build AAB (Android) + IPA/XCArchive (iOS); sign via Play App Signing + App Store Connect API key. Pin action SHAs `[GIT-05]`; OIDC keyless where supported.
15. [REQ] L10n: `flutter_localizations` + `intl` + ARB files; `gen-l10n` for typed `AppLocalizations`; never hardcode user-facing strings; RTL-aware layouts (test `Directionality(textDirection: TextDirection.rtl)`).
16. [REQ] Security `[SEC-01..10]`: zero-trust input validation (Form + validators); no secrets in code (use `.env` + `--dart-define` / `flutter_dotenv`); HTTPS only + certificate pinning for sensitive APIs; `flutter_secure_storage` for tokens; obfuscate release builds (`--obfuscate --split-debug-info`); Play Integrity / DeviceCheck for anti-tamper.
17. [REQ] Code quality `[CODE-01..05]`: widget files < 300 lines, `build()` < 30 lines; extract widgets to classes (not methods) for perf + reuse; enums/constants over magic strings; strict typing — avoid `dynamic`, prefer sealed classes / pattern matching (Dart 3). No `TODO`/`FIXME` without ticket tag.
18. [REQ] Cross-platform: feature-detect with `Platform.isIOS`/`Platform.isAndroid`/`kIsWeb`; `MediaQuery.padding`/`SafeArea` for notches; adaptive widgets (`Platform.isIOS ? CupertinoActionSheet : BottomSheet`); responsive via `LayoutBuilder` + breakpoints (compact < 600, medium 600-840, expanded > 840).
19. [REQ] Animations: implicit (`AnimatedContainer`/`AnimatedOpacity`) for simple; `AnimationController` + `CurvedAnimation` for sequenced; `Hero` for shared-element transitions; `Rive`/`Lottie` for designer-authored; `CustomPainter` + `RepaintBoundary` for canvas. Dispose controllers.
20. [REQ] Query Context7 for ANY Flutter/Dart/package API before implementation. Test on physical devices (iOS + Android) before declaring done. Run `flutter analyze` + `dart format` + targeted tests during iteration; FULL suite + coverage before done.

[PROHIBIT]
- `useMaterial3: false` without explicit justification.
- `WillPopScope` (deprecated — use `PopScope`).
- `setState` for app-wide/shared state.
- `InheritedWidget` manual for app state (use Riverpod/BLoC).
- `ListView(children:)` for > 20 items.
- Hardcoded `Color(0x...)` / `TextStyle(fontSize:)` in widgets (use `Theme.of`).
- `dynamic` in public APIs.
- Business logic inside `build()`.
- Secrets committed to repo / hardcoded API keys.
- `git add .` / `git add -A` `[GIT-06]`.
