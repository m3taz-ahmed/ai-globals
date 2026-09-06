[TECH] Swift 6.3 (latest 6.3.1, Apr 2026)
[OBJ] Swift programming language — shipped with Xcode 26.4. No Swift 7 yet.
[RULES]
1. [REQ] Swift 6.3 ships with Xcode 26.4 — use Xcode 26.4+ for compilation; older Xcode versions cannot build 6.3 code.
2. [REQ] No Swift 7 yet — Swift 6.3 is the latest major. Do not assume Swift 7 features exist.
3. [REQ] Use Swift 6 language mode for strict concurrency — `Sendable` checking, actor isolation, data race safety.
4. [REQ] Use `async/await` + `Task` + `TaskGroup` for concurrency — never use `DispatchQueue` for new async code.
5. [REQ] Use `actor` for shared mutable state — `Sendable` for value types crossing isolation boundaries.
6. [REQ] Use `struct` for value types; `class` for reference types with identity; `enum` for sum types.
7. [REQ] Use `Codable` for JSON serialization — `JSONEncoder` / `JSONDecoder` with `DateEncodingStrategy`.
8. [REQ] Use `let` for immutable bindings; `var` only when mutation required.
9. [REQ] Use `guard let` / `if let` for optional unwrapping — never force-unwrap `!` in production.
10. [REQ] Use Swift Package Manager (`Package.swift`) for dependency management — avoid CocoaPods for new projects.
11. [REQ] Use `@MainActor` for UI-bound code (SwiftUI / UIKit main thread).
12. [REQ] Use result builders / `some View` / `@State` / `@Binding` / `@Environment` for SwiftUI.
13. [PROHIBIT] Never force-unwrap `!` in production — use `guard let` / `if let` / `??`.
14. [PROHIBIT] Never use `DispatchQueue` for new async code — use `async/await` + `Task`.
15. [PROHIBIT] Never use CocoaPods for new projects — use SPM.
16. [PROHIBIT] Never assume Swift 7 features — 6.3 is latest.
17. [CMD] `swift build` — compile SPM project.
18. [CMD] `swift test` — run tests.
19. [CMD] `swift run` — run executable target.
20. [CMD] `xcodebuild -scheme MyScheme -destination 'platform=iOS Simulator,name=iPhone 16'` — Xcode build.
[COMPAT]
- Swift 6.3.1: latest (Apr 2026).
- Xcode 26.4 required.
- Swift 6 language mode: strict concurrency.
- No Swift 7 yet.
- SPM default dependency manager.
[REFS]
- https://www.swift.org/
- https://docs.swift.org/swift-book/
- https://developer.apple.com/xcode/
- https://www.swift.org/documentation/package-manager/
