# Expo SDK 56 / React Native 0.86 — Tech Stack Rules

> **Version:** Expo SDK 56 (2026) + React Native 0.86 + React 19.2 + TypeScript 6.0.
> **Load rule `[VER-01]`:** Read `package-lock.json` (or `yarn.lock` / `pnpm-lock.yaml`) -> grep `expo`, `react-native`, `react` versions -> load `tech-stack/expo-sdk-<major>.md`. If lockfile absent, use `package.json` dependencies. NEVER assume version.
> **Skills:** `mobile-architect` (full-stack) -> `flutter-architect` (cross-ref) + `frontend-frameworks-lord`. Persona: MOBILE + DEV.
> **Context7 IDs:** Expo `/expo/expo`; React Native `/facebook/react-native`; TanStack Query `/tanstack/query`; Zustand `/pmndrs/zustand`; Zod `/colinhacks/zod`; React Hook Form `/react-hook-form/react-hook-form`; Unistyles `/jpudysz/react-native-unistyles`; MMKV `/mrousavy/react-native-mmkv`; Sentry `/getsentry/sentry-react-native`; PostHog `/PostHog/posthog-js`.

## SDK & Language

- **Expo SDK 56** (managed workflow recommended; bare workflow for custom native). `npx create-expo-app@latest`.
- **React Native 0.86** with New Architecture (Fabric + JSI + TurboModules) stable — no bridge, synchronous native calls.
- **React 19.2** — React Compiler enabled (`react-compiler-runtime`) for automatic memoization.
- **TypeScript 6.0** — strict mode (`"strict": true`); `exactOptionalPropertyTypes`; `noUncheckedIndexedAccess`.
- **Expo Router** (file-based routing on React Navigation v7) — typed routes enabled (`experiments.typedRoutes`).

## Project Anatomy (feature-first)

```
app/                      # Expo Router (file-based routing)
  _layout.tsx             # Root layout: providers nesting
  (auth)/                 # Auth group
    login.tsx
    register.tsx
  (main)/                 # Main app group
    (tabs)/               # Bottom tabs
      index.tsx
      profile.tsx
    _layout.tsx
src/
  common/components/      # Shared UI components (33+ pattern)
  features/<feature>/     # Feature modules (self-contained)
    components/
    services/
    hooks/
    stores/
    types/
    schemas/              # Zod schemas
    constants/
  providers/              # QueryProvider, auth store, theme
  theme/                  # Unistyles config, design tokens
  i18n/                   # Translations (en, ar)
  utils/
    storage/              # MMKV wrapper
  services/
    api/                  # Axios client + interceptors
index.ts                  # Custom entry: init Unistyles before Expo Router
```

## Custom Entry Point (Unistyles race condition fix)

```typescript
// index.ts — MUST exist before expo-router/entry
import '@/theme/unistyles';  // Initialize Unistyles BEFORE route scan
import 'expo-router/entry';
```

## State Management

| Scenario | Choice |
|---|---|
| Server state (API data) | **TanStack Query v5** + MMKV persistence (`@tanstack/query-sync-storage-persister`) |
| Client state (UI/auth) | **Zustand v5** + MMKV persistence (`skipHydration: true`, explicit hydrate after MMKV init) |
| Forms | **React Hook Form v7** + **Zod v4** (schema validation, i18n error messages) |

- **Query cache buster**: `user:${userId}` key to prevent cross-user cache leaks on shared devices.
- **Centralized error handling**: `QueryCache` + `MutationCache` with global error toast.
- **DevTools**: `@dev-plugins/react-query` for Flipper/React DevTools integration.
- NEVER use React Context for auth state — use Zustand store.
- NEVER AsyncStorage for tokens — use `expo-secure-store` (iOS Keychain / Android Keystore).

## Styling & Design System

| Need | Choice |
|---|---|
| Primary styling | **react-native-unistyles v3** (semantic tokens, compiled stylesheets, TypeScript-first) |
| Alternative | NativeWind v4 (Tailwind CSS for RN) |
| Cross-platform RN+Web | Tamagui (optimizing compiler, SSR-first) |
| Material Design 3 | React Native Paper v6 |

- **Design tokens**: `src/theme/` with light/dark themes; semantic color naming (`theme.colors.primary` not `#4F46E5`).
- **Responsive helpers**: `rf()` (responsive font), `hs()` (horizontal scale), `vs()` (vertical scale).
- **Theme callback form**: `StyleSheet.create((theme) => ({ ... }))` — access theme in styles.
- **No inline styles, no color literals** — all via tokens.
- **WCAG AA contrast** + tap targets >= 44x44pt.
- **Dark mode**: `theme.colors.mode` with persisted `system` / `light` / `dark` preference.

## Navigation

- **Expo Router** (file-based, typed routes). `Stack.Protected` for auth guards.
- Groups: `(auth)/` for unauthenticated, `(main)/` for authenticated, `(tabs)/` for bottom nav.
- **Typed routes**: `experiments.typedRoutes: true` in `app.json` — autocomplete + compile-time safety.
- Deep linking via `app.json` `scheme` + `expo-linking`.

## Networking

- **Axios** with auth interceptors (auto-token attachment, 401 auto-logout, error normalization).
- **TanStack Query** for caching, retry, optimistic updates, background refetch.
- **react-query-kit** for typed query hooks (`const useUser = createQuery({...})`).
- Repository pattern: `services/api/` wraps Axios; features call hooks, not Axios directly.
- HTTPS only; certificate pinning for sensitive APIs.

## Authentication

- **Supabase** (email OTP / OAuth) or custom JWT backend.
- **expo-secure-store** for tokens (iOS Keychain / Android Keystore) — NEVER AsyncStorage.
- **Ordered logout cleanup** (atomic, prevents data leaks):
  1. Set auth state to LOGGING_OUT
  2. `queryClient.cancelQueries()`
  3. `posthog.reset()`
  4. `sentry.setUser(null)`
  5. `queryClient.clear()`
  6. `authStore.reset()`
  7. `supabase.auth.signOut()`
  8. `router.replace('/login')`
- **OTP timer**: timestamp-based (not countdown) — resilient to app backgrounding.

## Storage

| Need | Choice |
|---|---|
| KV (fast, encrypted) | **react-native-mmkv v4** (AES-encrypted, synchronous) |
| Auth tokens | **expo-secure-store** (Keychain/Keystore only) |
| Relational | **WatermelonDB** (SQLite + reactive queries, large datasets) |
| Object DB | **Realm** (built-in sync option) |

- MMKV wrapper: `src/utils/storage/` with typed keys.
- `skipHydration: true` on Zustand stores — hydrate explicitly after MMKV init.

## i18n & RTL

- **react-i18next** + **react-i18next** for translations.
- English + Arabic (minimum); `I18nManager.forceRTL(isArabic)` in root layout.
- Validation messages use i18n keys, not raw text.
- **ESLint plugin** for i18n JSON validation (check translation completeness).
- `I18n.t('errors.required')` not `'This field is required'`.

## Testing `[TEST-07]`

| Tier | Command | Scope |
|---|---|---|
| FAST | `jest <pattern>` (~5s) | Touched only |
| FULL | `jest --coverage` | All + coverage >= 50% (target 80% logic) |

- **Jest** + `jest-expo` preset.
- **React Native Testing Library** (RNTL) — `getByRole`, `getByLabelText` (accessibility-first).
- **testID convention**: `{feature}-{element}-{action}`.
- Mock MMKV, Reanimated, Expo Router in `jest.setup.ts`.
- **E2E**: **Maestro** (YAML, black-box, <1% flake, all platforms) — preferred over Detox.
- Coverage collection from `src/**/*.{ts,tsx}`.

## CI/CD

- **EAS Build/Workflows** (Expo managed cloud): `eas.json` with development/preview/production profiles.
- Build profiles: `development` (simulator), `preview` (internal distribution), `production` (store).
- **OTA updates**: `eas update` for JS-only changes (no store review needed).
- **Fire-and-forget**: `eas-cli build --no-wait` + webhooks for completion (saves macOS runner cost).
- **Environment-specific scripts**: `start:development`, `android:staging`, `ios:production`.
- Auto-increment version for production builds.
- Pin action SHAs `[GIT-05]`; OIDC keyless where supported.

## Observability

- **Sentry** (`@sentry/react-native`) — crash reporting + stack traces + session replay.
- **PostHog** (`posthog-react-native`) — product analytics + feature flags + A/B testing + session replay.
- Screen tracking: PostHog `screen()` calls in router observer.
- User identify: `posthog.identify(userId)` on login; `posthog.reset()` on logout.
- Sentry user-context: `sentry.setUser({ id, email })` on login; `sentry.setUser(null)` on logout.

## Security `[SEC-01..10]`

- Input: Zod schemas for all API inputs; React Hook Form validators.
- Secrets: `EXPO_PUBLIC_*` env vars (public) + `expo-secure-store` (private); NEVER commit.
- Transport: HTTPS only; certificate pinning for sensitive.
- Storage: `expo-secure-store` for tokens; MMKV AES encryption for sensitive KV.
- No PII in logs/analytics `[SEC-04]`.
- App attestation: DeviceCheck (iOS) / Play Integrity (Android) for anti-tamper.

## Key Dependencies (verify versions in lockfile)

| Purpose | Package |
|---|---|
| Framework | `expo`, `react-native`, `react` |
| Routing | `expo-router` |
| Server state | `@tanstack/react-query`, `@tanstack/query-sync-storage-persister` |
| Client state | `zustand` |
| Forms | `react-hook-form`, `zod` |
| Styling | `react-native-unistyles` |
| Storage | `react-native-mmkv`, `expo-secure-store` |
| HTTP | `axios` |
| i18n | `i18next`, `react-i18next` |
| Icons | `lucide-react-native` |
| Crash | `@sentry/react-native` |
| Analytics | `posthog-react-native` |
| DevTools | `@dev-plugins/react-query` |
| Testing | `jest`, `jest-expo`, `@testing-library/react-native` |

## Quality Gate (before done)

```bash
npx tsc --noEmit                    # Type check
npx eslint src/ app/                # Lint
jest --coverage                     # FULL tier
npx expo prebuild                   # Verify native config
# E2E: maestro test .maestro/       # On device/emulator
```

- No `git add .` / `git add -A` `[GIT-06]`.
- No `TODO`/`FIXME` without ticket tag.
- Test on physical devices (iOS + Android) before release.
