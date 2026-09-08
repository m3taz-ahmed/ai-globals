[TECH] Swift 6.4 (beta, WWDC 2026)
[OBJ] Swift 6.4 — simplified availability syntax with `anyAppleOS`, `@diagnose` attribute for warnings, async in `defer`, new iteration protocol for noncopyable types, Foundation 4x URL parsing, Swift Testing XCTest interop, Subprocess 1.0.
[RULES]
1. [REQ] Use simplified availability syntax: `@available(anyAppleOS, *)` — single attribute for all Apple platforms.
2. [REQ] Use `@diagnose` attribute for finer-grained warning control — suppress or elevate specific warnings.
3. [REQ] Use `async` in `defer` blocks — cleanup runs whether function returns or throws. `defer { await cleanup() }`.
4. [REQ] Use new iteration protocol for noncopyable types — `for x in span` works with `Span<T>`, `InlineArray<T>` without copying.
5. [REQ] Use Foundation performance gains — URL parsing up to 4x faster.
6. [REQ] Use Swift Testing with XCTest interop — XCTest assertion failures reported as test issues from Swift Testing.
7. [REQ] Use Subprocess 1.0 — modern APIs for launching subprocesses. Replaces `Process` API.
8. [REQ] Use Swift 6 language mode for strict concurrency — `Sendable` checking, actor isolation, data race safety.
9. [REQ] Use `async/await` + `Task` + `TaskGroup` for concurrency — never `DispatchQueue` for new async code.
10. [REQ] Use `actor` for shared mutable state — `Sendable` for value types crossing isolation boundaries.
11. [REQ] Use `Codable` for JSON serialization — `JSONEncoder` / `JSONDecoder`.
12. [REQ] Use module selector syntax (Swift 6.3+): `Rocket::SaturnV` to disambiguate same-named types from different modules.
13. [PROHIBIT] Never use `DispatchQueue` for new async code — use `async/await` + `Task`.
14. [PROHIBIT] Never assume Swift 7 features exist — Swift 6.4 is latest.
[COMPAT]
- Swift 6.4 (beta, WWDC 2026).
- Swift 6.3.3 is latest stable (Jun 30 2026).
- Ships with Xcode 27 (beta).
- First official Swift SDK for Android (6.3+).
- `@c` attribute for exposing Swift to C (6.3+).
[REFS]
- https://developer.apple.com/videos/play/wwdc2026/262/
- https://developer.apple.com/wwdc26/guides/swift/
- https://www.swift.org/
