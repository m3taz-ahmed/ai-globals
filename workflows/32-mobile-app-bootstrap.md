---
trigger: mobile bootstrap, mobile app setup, flutter app, expo app, react native app, mobile app, تطبيق موبايل, موبايل ابليكيشن
persona: MOBILE, DEV, ARCH, UX
skills: mobile-architect, flutter-architect, mobile-game-producer
---

# Workflow 32 — Mobile App Bootstrap

[OBJ] Bootstrap a production-grade cross-platform mobile app — Flutter or React Native/Expo — with architecture, state, persistence, networking, testing, CI/CD, security, and observability pre-wired.

[PHASES]

## Phase 1: Framework Selection

1. [REQ] Detect project type from user request:
   - "Flutter" / "Dart" -> Flutter path.
   - "React Native" / "Expo" / "RN" -> Expo path.
   - Ambiguous -> ask user: "Flutter (UI pixel-perfection, single codebase) or Expo/React Native (JS/TS team, faster MVP)?"
2. [REQ] Load tech-stack:
   - Flutter: read `pubspec.lock` (or `pubspec.yaml`) -> load `tech-stack/flutter.md`.
   - Expo: read `package-lock.json` (or `package.json`) -> load `tech-stack/expo-sdk-56.md`.
3. [REQ] Load skills: `mobile-architect` (lord) -> platform-specific (`flutter-architect` or `frontend-frameworks-lord`).
4. [REQ] Query Context7 for framework + key libraries before any code.

## Phase 2: Project Scaffolding

5. [CMD] Flutter: `flutter create --org com.example --platforms=ios,android,web --project-name my_app my_app`
6. [CMD] Expo: `npx create-expo-app@latest --template tabs my_app`
7. [REQ] Restructure to feature-first Clean Architecture:
   - Flutter: `lib/{core,config,routing,l10n,features/<feature>/{data,domain,presentation},shared/widgets}`
   - Expo: `app/` (routes) + `src/{common/components,features/<feature>/{components,services,hooks,stores,types,schemas,constants},providers,theme,i18n,utils/storage,services/api}`
8. [REQ] Create `AGENTS.md` with architectural vetos, banned patterns, state rules, backend isolation.
9. [REQ] Create `.cursorrules` with IDE-specific rules (adapt from rn-copilot pattern).

## Phase 3: Core Infrastructure

10. [REQ] **State management**:
    - Flutter: add `flutter_riverpod`, `riverpod_annotation`, `riverpod_generator`, `build_runner` to `pubspec.yaml`. Create `ProviderScope` in `main.dart`.
    - Expo: add `@tanstack/react-query`, `zustand`, `react-native-mmkv`, `@tanstack/query-sync-storage-persister`. Create `QueryProvider` with MMKV persistence + cache buster.
11. [REQ] **Routing**:
    - Flutter: add `go_router`, `go_router_builder`. Create `app_router.dart` with `TypedGoRoute` + `StatefulShellRoute.indexedStack` + `redirect` auth guard + `_RouterRefreshNotifier`.
    - Expo: configure Expo Router with typed routes. Create `(auth)/` and `(main)/` groups. `Stack.Protected` for auth.
12. [REQ] **Networking**:
    - Flutter: add `dio`, `freezed`, `json_serializable`. Create interceptors (auth, logging, error-mapping). Freezed Failure union type.
    - Expo: add `axios`. Create auth interceptors (auto-token, 401 auto-logout). TanStack Query for caching.
13. [REQ] **Persistence**:
    - Flutter: add `drift` (SQL) + `hive` (KV) + `flutter_secure_storage` (tokens).
    - Expo: add `react-native-mmkv` (KV) + `expo-secure-store` (tokens). Create MMKV wrapper with typed keys.
14. [REQ] **Styling**:
    - Flutter: `ColorScheme.fromSeed()` + `ThemeExtension` for tokens. Add `flex_color_scheme`.
    - Expo: add `react-native-unistyles`. Create `src/theme/` with light/dark tokens + responsive helpers. Custom entry point `index.ts`.
15. [REQ] **i18n**:
    - Flutter: add `flutter_localizations` + `intl` + ARB OR `slang`. Configure RTL.
    - Expo: add `i18next` + `react-i18next`. English + Arabic. `I18nManager.forceRTL()`. ESLint plugin for translation completeness.

## Phase 4: Auth & Security

16. [REQ] **Auth flow**: login/register/logout/reset. Auth state in Riverpod (Flutter) / Zustand (Expo). Tokens in secure storage.
17. [REQ] **Ordered logout cleanup** (both platforms): cancel queries -> reset analytics -> clear cache -> reset auth store -> sign out -> redirect.
18. [REQ] **Security**: input validation (Form+validators / Zod), HTTPS only, cert pinning for sensitive, no secrets in code (`--dart-define` / `EXPO_PUBLIC_*`), obfuscate release.
19. [REQ] **Anti-tamper**: Play Integrity (Android) / DeviceCheck (iOS). Jailbreak/root detection.

## Phase 5: Observability

20. [REQ] **Crash reporting**: Sentry (Flutter: `sentry_flutter`; Expo: `@sentry/react-native`). Upload debug symbols.
21. [REQ] **Analytics**: PostHog (Flutter: `posthog_flutter`; Expo: `posthog-react-native`). Screen tracking in router observer. User identify on login, reset on logout.
22. [REQ] **Feature flags**: PostHog feature flags or Firebase Remote Config.

## Phase 6: Testing & CI/CD

23. [REQ] **Testing setup**:
    - Flutter: `mocktail` + `integration_test` + `patrol` (E2E). FAST `flutter test <file>`; FULL `flutter test --coverage` + `integration_test/`.
    - Expo: `jest` + `jest-expo` + `@testing-library/react-native` + Maestro (E2E). FAST `jest <pattern>`; FULL `jest --coverage`.
24. [REQ] **CI/CD**:
    - Flutter: GitHub Actions + Codemagic + Fastlane. Pipeline: format -> analyze -> test -> build -> sign -> deploy.
    - Expo: EAS Workflows. `eas.json` with development/preview/production profiles. OTA updates. Fire-and-forget `--no-wait`.
25. [REQ] **Quality gate** (before done):
    - Flutter: `dart format --set-exit-if-changed` + `flutter analyze --fatal-infos` + `flutter test --coverage` + `flutter test integration_test/`.
    - Expo: `tsc --noEmit` + `eslint` + `jest --coverage` + `expo prebuild`.
26. [REQ] Test on physical devices (iOS + Android) before release.

[OUTPUT]
- Production-ready mobile app with: feature-first clean architecture, state management, routing with auth guards, networking with interceptors, offline-first persistence, design system with tokens, i18n with RTL, auth with ordered logout, Sentry + PostHog observability, two-tier testing, CI/CD pipeline, AGENTS.md + .cursorrules AI instructions.
- `AGENTS.md` with architectural vetos and banned patterns.
- Quality gates green.

[QUALITY_GATE]
- `[VER-01]`: versions pinned to lockfile.
- `[CODE-01..05]`: service-repo separation, strict typing, class <300 lines, enums over magic strings, SOLID/DRY.
- `[TEST-07]`: two-tier testing (FAST + FULL).
- `[SEC-01..10]`: zero-trust, no secrets, HTTPS, secure storage, obfuscation.
- `[GIT-05]`: pin action SHAs, OIDC keyless.
- `[GIT-06]`: no `git add .` / `git add -A`.
