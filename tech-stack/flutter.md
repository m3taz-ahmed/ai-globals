# Flutter 3.47 / Dart 3.13 — Tech Stack Rules

> **Version:** Flutter 3.47.0 (stable, 11 Aug 2026) + Dart 3.13 (12 Aug 2026).
> **Load rule `[VER-01]`:** Read `pubspec.lock` -> grep `flutter:` SDK version + `dart:` version -> load `tech-stack/flutter-<major>.md` (this file for 3.x). If lockfile absent, use `pubspec.yaml` `environment: sdk:` constraints. NEVER assume version.
> **Skills:** `flutter-architect` (full-stack) -> `flutter-design` + `flutter-developer`. Persona: MOBILE + UX.
> **Context7 IDs:** Flutter `/flutter/website`; API `/websites/api_flutter_dev`; Packages `/flutter/packages`; Dart `/dart-lang/site-www`; Riverpod `/riverpod/riverpod`; BLoC `/felangel/bloc`; Freezed `/rrousselGit/freezed`; Drift `/simolus3/drift`; Dio `/cfug/dio`; go_router via `/flutter/packages`.

## SDK & Language

- **Flutter 3.47** (CalVer, ~3 releases/year: Feb/May/Aug/Nov). Stable channel only for production.
- **Dart 3.13** — primary constructors (lang version >= 3.1), records, patterns, sealed classes, exhaustive switch. Set `environment: sdk: '>=3.13.0 <4.0.0'` in `pubspec.yaml`.
- **Impeller** is the default renderer on iOS (since 3.10) and Android (since 3.16). Verify via `flutter doctor` + platform config. Impeller removes most shader-compile jank; no manual SkSL warmup needed.
- **Material 3** is default ON since Flutter 3.16. `useMaterial3: true` is implicit — do NOT set `false` without justification.

## Project Anatomy (feature-first + clean)

```
lib/
  main.dart              # < 30 lines: entry + runApp(ProviderScope)
  core/                  # shared: error, network, theme, constants, utils
  config/                # env, router, di
  routing/               # go_router config + typed route args
  l10n/                  # ARB files + AppLocalizations gen
  features/<feature>/
    data/                # models (freezed+json), datasources, repo impl
    domain/              # entities, repo interfaces, usecases
    presentation/        # widgets, pages, controllers (Notifier/Bloc)
test/                    # mirrors lib/ structure
integration_test/        # device/emulator E2E
```

## State Management

| Scenario | Choice |
|---|---|
| Widget-local ephemeral | `setState` / `ValueNotifier` |
| Scoped shared, reactive | **Riverpod** — `Notifier`/`AsyncNotifier` + `@riverpod` code-gen (`riverpod_generator`) + `ref.watch`/`ref.read`/`ref.listen` + `AsyncValue` |
| Event-driven, large teams | **BLoC** — `Bloc`/`Cubit` + freezed events/states |
| Legacy | `Provider` (avoid for new projects) |

- NEVER `setState` for app-wide state. NEVER `InheritedWidget` manual.
- Riverpod: prefer code-gen `@riverpod` for type-safety + auto-dispose; use `AsyncValue.guard` for async; `ProviderScope` at root.
- BLoC: `BlocBuilder`/`BlocSelector` scoped to smallest subtree; `BlocListener` for side-effects.

## Immutability & Models

- `freezed` + `json_serializable` for all domain/data models. `@freezed` + `@JsonSerializable` + `fromJson` + `copyWith`.
- Dart 3 `sealed` + pattern matching for exhaustive state: `switch (state) { case Loading(): ...; case Data(:final data): ...; case Error(:final failure): ... }`.
- Dart 3.13 primary constructors for concise immutable data classes.
- `const` constructors everywhere possible.

## Routing

- **`go_router`** (declarative). `GoRoute` + `ShellRoute`/`StatefulShellRoute.indexedStack` (bottom-nav with state preservation); typed `extra` args (define arg classes — never raw `Map`); `redirect` for auth guards.
- `PopScope` (NOT deprecated `WillPopScope`) for Android 14+ predictive back.
- Never `Navigator.push` for complex apps.

## Theming & Design System (see `flutter-design`)

- `ColorScheme.fromSeed(seedColor:)` + `TextTheme`; light + dark + `ThemeMode.system`.
- Access via `Theme.of(context)` ONLY — no hardcoded `Color(0x...)` / `TextStyle(fontSize:)`.
- Spacing/radius/elevation tokens as constants or `ThemeExtension`.
- M3 components: `NavigationBar`, `SearchBar`, `SegmentedButton`, `FilledButton`/`OutlinedButton`/`TextButton`.

## Networking

- **`dio`** (interceptors: auth, logging, retry, error-mapping) for non-trivial; `http` for trivial.
- Deserialize via `freezed` + `json_serializable`; repository pattern wraps datasources.
- Typed `Result<T>` / `Either<Failure, T>` / `AsyncValue.guard`; never swallow exceptions.
- `CancelToken` for in-flight cancel; debounce search. HTTPS only + cert pinning for sensitive.

## Persistence

| Need | Choice |
|---|---|
| Relational (SQL) | **`drift`** (typed SQLite, migrations, `Stream<List<T>>`) |
| KV / object | **`hive`** (binary) or **`isar`** (queryable, fast) |
| Primitives | `shared_preferences` ONLY |
| Sensitive | **`flutter_secure_storage`** (Keychain/Keystore) |

- Offline-first: local DB as source of truth; sync queue + conflict resolution (LWW/server-wins/CRDT) on reconnect; `connectivity_plus` + `workmanager`.

## Performance (60 FPS / 16.6 ms)

- Profile with **Flutter DevTools** (Performance timeline, jank, CPU profiler, Memory).
- `const` widgets; scope `Consumer`/`BlocSelector` to smallest subtree; `RepaintBoundary` around animations.
- `ListView.builder`/`SliverList.builder` + `itemExtent`/`prototypeItem` (never `ListView(children:)` for > 20 items).
- Images: `cached_network_image` + `cacheWidth`/`cacheHeight` + `precacheImage`.
- Avoid `Opacity` widget (use `FadeTransition`/`AnimatedOpacity`); avoid heavy work in `build()`.
- CPU-heavy: `Isolate.run` / `compute()`.

## Accessibility (WCAG AA)

- `Semantics` on custom gesture widgets; `MediaQuery.textScaler` (never fixed font sizes); tap targets >= 48 dp (M3) / 44 (iOS).
- Test TalkBack (Android) + VoiceOver (iOS) + text-scale 200%. `SemanticsService.announce` for dynamic changes.

## Testing `[TEST-07]`

| Tier | Command | Scope |
|---|---|---|
| FAST | `flutter test test/path/touched_test.dart` | Touched only, ~5s |
| FULL | `flutter test --coverage` + `flutter test integration_test/` | All + coverage >= 80% logic / 70% total |

- Unit: `test()` + `mocktail` (`when(() => mock.x()).thenReturn()`; `registerFallbackValue` for non-nullable).
- Widget: `testWidgets()` + `WidgetTester` + `ProviderScope`/`BlocProvider` wrapper; assert behavior via `find.*`.
- Golden: `matchesGoldenFile` (regen `--update-goldens`).
- Slow tests: `@Tags(['slow'])` + `--exclude-tags=slow` for fast tier.

## CI/CD

- Pipeline: `dart format --set-exit-if-changed lib/ test/` -> `flutter analyze --fatal-infos` -> `flutter test` -> `flutter build` -> sign -> deploy.
- Android: `flutter build appbundle` (AAB) + Play App Signing + `fastlane supply`; target latest Play API.
- iOS: `flutter build ipa` + App Store Connect API key + `fastlane pilot` (TestFlight) / `deliver`.
- Release: `--obfuscate --split-debug-info=build/symbols` (keep symbols; upload to Sentry/Crashlytics).
- Pin action SHAs `[GIT-05]`; OIDC keyless; SBOM + Cosign.

## Security `[SEC-01..10]`

- Input: `Form` + validators; DTOs for API; zero-trust.
- Secrets: `.env` + `flutter_dotenv` / `--dart-define-from-file`; NEVER commit `[SEC-04]`.
- Transport: HTTPS + cert pinning (`dio_certificate_pinning`).
- Storage: `flutter_secure_storage`; encrypt DB (SQLCipher / isar encryption).
- Release: obfuscate + `flutter_jailbreak_detection` + Play Integrity / DeviceCheck.
- No PII in logs/analytics `[SEC-04]`.

## L10n & RTL

- `flutter_localizations` + `intl` + ARB; `gen-l10n` for typed `AppLocalizations`; never hardcode user-facing strings.
- RTL: `EdgeInsetsDirectional` / `AlignmentDirectional` (start/end not left/right); test `Directionality(textDirection: TextDirection.rtl)`; mirror directional icons.

## Key Packages (verify pub points >= 80 + maintained before adding)

| Purpose | Package |
|---|---|
| State | `flutter_riverpod`, `riverpod_generator`, `flutter_bloc` |
| Models | `freezed`, `json_serializable`, `build_runner` |
| Routing | `go_router` |
| HTTP | `dio` |
| DB | `drift`, `isar`, `hive` |
| Secure storage | `flutter_secure_storage` |
| Images | `cached_network_image`, `flutter_svg` |
| Animations | `rive`, `lottie`, `flutter_animate` |
| Notifications | `firebase_messaging`, `flutter_local_notifications` |
| Background | `workmanager`, `flutter_background_service` |
| Connectivity | `connectivity_plus` |
| Platform channels | `pigeon` (type-safe codegen) |
| IAP | `in_app_purchase` |
| Observability | `sentry_flutter`, `firebase_crashlytics` |
| Testing | `mocktail`, `integration_test`, `golden_toolkit` |

## Quality Gate (before done)

```
dart format --set-exit-if-changed lib/ test/
flutter analyze --fatal-infos
flutter test --coverage          # FULL tier
flutter test integration_test/   # on device/emulator
```

- No `git add .` / `git add -A` `[GIT-06]`.
- No `TODO`/`FIXME` without ticket tag.
- Test on physical devices (iOS + Android) before release.
