[TECH] Flutter 3.47 / Dart 3.13 (latest 3.47.1, Aug 2026)
[OBJ] Flutter 3.47.x + Dart 3.13. Standalone `material_ui` + `cupertino_ui` 1.0 packages, Impeller default on desktop, Flutter Widget Previews stable, Xcode 27 / iOS 27 prep, minimum iOS 15 / macOS 12.
[RULES]
1. [REQ] Use standalone `material_ui` and `cupertino_ui` packages (1.0) — design systems decoupled from core SDK. Import from `package:material_ui/` instead of `package:flutter/material.dart`.
2. [REQ] Use Impeller renderer (default on macOS, Windows, Linux, Android) — smooth animations, reduced jank. Skia backend removed on Android 10+.
3. [REQ] Use Flutter Widget Previews (stable) — preview widgets in IDE without running app.
4. [REQ] Use Xcode 27 / iOS 27 / macOS 27 support — test against Apple betas now. Minimum: iOS 15, macOS 12.
5. [REQ] Use Dart 3.13 — latest language version with Flutter 3.47.
6. [REQ] Use `flutter_lints` package for lint rules — stricter than default.
7. [REQ] Use Riverpod / BLoC for state management — never `setState` for complex state.
8. [REQ] Use `go_router` for declarative routing — `GoRoute(path: '/', builder: ...)`.
9. [REQ] Use `freezed` for immutable data classes + `json_serializable` for JSON.
10. [REQ] Use `dio` for HTTP client — interceptors, cancellation, retry.
11. [REQ] Use `drift` for local SQLite database — type-safe queries, migrations.
12. [REQ] Use WebAssembly (Wasm) as default for web — native-quality performance.
13. [PROHIBIT] Never use Skia on Android 10+ — Impeller is the only renderer.
14. [PROHIBIT] Never target iOS < 15 or macOS < 12 — minimum bumped in Flutter 3.47.
[COMPAT]
- Flutter 3.47.1 (hotfix, Aug 19 2026).
- Flutter 3.47.0 (Aug 12 2026).
- Dart 3.13 (Aug 12 2026).
- CalVer: ~3 releases/year (Feb/May/Aug/Nov).
- Minimum: iOS 15, macOS 12, Android 7+ (compileSdk 36, targetSdk 36).
- Xcode 27 support.
[REFS]
- https://flutter.dev/blog/whats-new-in-flutter-3-47
- https://docs.flutter.dev/release/release-notes
- https://dart.dev/
