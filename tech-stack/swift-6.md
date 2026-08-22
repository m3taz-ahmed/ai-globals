[TECH] Swift 6
[OBJ] Type-safe compiled language with async/await, actors, Sendable conformance, macros, the Observation framework, SwiftData, and strict concurrency checking.
[RULES]
1. [REQ] Use `async/await` for asynchronous code; mark functions `async` and call with `await`; use `Task { }` to bridge from synchronous contexts and `Task.detached` for off-main-actor work.
2. [REQ] Use `actor` for shared mutable state isolation; actors serialize access to their properties; use `nonisolated` for pure/computed properties that don't access mutable state.
3. [REQ] Conform reference types to `Sendable` for safe concurrent passing; use `@Sendable` on closures crossing actor boundaries; value types are implicitly `Sendable` if all members are.
4. [REQ] Enable strict concurrency checking (`SwiftLanguageMode 6` or `StrictConcurrency=complete`); resolve all data-race warnings before shipping — they are errors in Swift 6 mode.
5. [REQ] Use `@MainActor` to isolate UI-related types and functions to the main thread; avoid calling `@MainActor` code from background tasks without `await`.
6. [REQ] Use the Observation framework (`@Observable` macro) instead of `ObservableObject`/`@Published` for SwiftUI state; `@Observable` enables granular view updates and is more performant.
7. [REQ] Use SwiftData (`@Model`, `@Query`, `ModelContainer`, `ModelContext`) for persistence with automatic CloudKit sync; define `@Model` classes with value-type properties where possible.
8. [REQ] Use `structured concurrency` (`async let`, `TaskGroup`) for parallel operations; use `withTaskGroup` for dynamic fan-out; cancel via `Task.cancel()` and check `Task.isCancelled`.
9. [REQ] Use Swift macros (`@Observable`, `@Model`, `#Predicate`) for compile-time code generation; use `freestanding` macros (`#macroName`) and `attached` macros (`@macroName`) appropriately.
10. [REQ] Use `Codable` with `JSONEncoder`/`JSONDecoder` for JSON serialization; use `@CodingKeys` for field mapping; use `KeyDecodingStrategy.convertFromSnakeCase` for API conventions.
11. [REQ] Use `Result<T, Error>` and typed throws (`func foo() throws(MyError)`) for explicit error types; define custom `Error` enums with `LocalizedError` for user-facing messages.
12. [REQ] Use `some` for opaque return types and `any` for existential types; in Swift 6, `any` is required explicitly for protocol existentials to avoid hidden dynamic dispatch costs.
13. [REQ] Use Swift Package Manager (SPM) for dependency management; define targets in `Package.swift`; use `.package(url:from:)` for versioned dependencies; run `swift test` in CI.
14. [PROHIBIT] Never use `DispatchQueue.async` for concurrency in new Swift 6 code; use `Task` and actors instead — GCD bypasses compile-time concurrency safety.
15. [PROHIBIT] Never use `@unchecked Sendable` without a documented thread-safety justification; it disables compile-time checking and shifts responsibility to the developer.
[COMPAT]
- v6.0: Strict concurrency (language mode 6), `Sendable` enforcement, typed throws (SE-0413), `@Observable` macro
- v6.0: SwiftData (iOS 17+/macOS 14+), Observation framework, Swift macros (freestanding + attached)
- v6.0: SPM, Xcode 16+, Swift Concurrency (actors, async/await, TaskGroups), Linux/Windows cross-platform
[REFS]
- https://www.swift.org/documentation/
- https://docs.swift.org/swift-book/
- https://developer.apple.com/documentation/swiftdata/
- https://developer.apple.com/documentation/observation/
- https://www.swift.org/migration/tips-migrating-to-swift-6/
- https://github.com/apple/swift-evolution/blob/main/proposals/0413-typed-throws
