[TECH] Expo SDK 57 (latest 57.0.19, Sep 2026)
[OBJ] React Native framework — RN 0.87, React 19.2, optional non-breaking upgrade model, `expo prebuild` cleans by default, `expo-font` web reset, `@expo/ui` text-field change.
[RULES]
1. [REQ] React Native 0.87 + React 19.2 — ensure peer deps align; run `npx expo install expo@^57.0.0 --fix` to auto-fix versions.
2. [REQ] Use optional non-breaking upgrade model: `npx expo install expo@^57.0.0 --fix` upgrades without breaking existing code — review changelog for opt-in features.
3. [REQ] `expo prebuild` cleans by default — it removes existing native directories before regenerating. Use `--no-clean` to preserve manual native modifications (not recommended).
4. [REQ] `expo-font` web reset — font loading behavior changed on web; review `useFonts()` calls and CSS font-face injection.
5. [REQ] `@expo/ui` text-field change — `TextField` component API updated; migrate props (placeholder, value, onChangeText) to new signature.
6. [REQ] Use EAS Build / EAS Submit for cloud builds — `eas build --platform ios/android`, `eas submit`.
7. [REQ] Use `expo-router` for file-based navigation — `app/` directory with nested layouts.
8. [REQ] Use `expo-secure-store` for sensitive data — never use `AsyncStorage` for tokens/secrets.
9. [REQ] Use `expo-updates` for OTA updates — configure update channels in `eas.json`.
10. [REQ] Use `app.json` / `app.config.ts` for config; use dynamic config for environment-specific values.
11. [REQ] Use `npx expo install <pkg>` to install compatible versions — never `npm install` random versions.
12. [REQ] Use Expo Modules API for native modules — `create-expo-module` scaffold.
13. [PROHIBIT] Never use `AsyncStorage` for secrets — use `expo-secure-store`.
14. [PROHIBIT] Never manually modify `ios/` or `android/` directories without `prebuild` — changes are overwritten on clean.
15. [PROHIBIT] Never skip `--fix` when upgrading SDK — peer dep mismatches cause runtime crashes.
16. [PROHIBIT] Never use old `@expo/ui` TextField API — migrate to new props.
17. [CMD] `npx expo install expo@^57.0.0 --fix` — upgrade to SDK 57.
18. [CMD] `npx expo prebuild` — generate native projects (cleans by default).
19. [CMD] `eas build --platform all` — cloud build.
20. [CMD] `npx expo start` — dev server.
[COMPAT]
- RN 0.87, React 19.2.
- `expo prebuild` cleans by default (breaking).
- `expo-font` web reset (breaking for web font loading).
- `@expo/ui` TextField API change (breaking).
- Optional non-breaking upgrade model: `--fix` auto-aligns peer deps.
[REFS]
- https://docs.expo.dev/
- https://docs.expo.dev/versions/v57.0.0/
- https://docs.expo.dev/eas/
- https://docs.expo.dev/router/
