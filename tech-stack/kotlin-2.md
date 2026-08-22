[TECH] Kotlin 2
[OBJ] Cross-platform statically typed language with coroutines, data classes, sealed classes, KMP, and the K2 compiler with Compose Multiplatform support.
[RULES]
1. [REQ] Use `suspend` functions for async work; launch coroutines in a `CoroutineScope` with `Dispatchers.IO` for I/O and `Dispatchers.Default` for CPU; never use `GlobalScope` in application code.
2. [REQ] Use structured concurrency: cancel parent scopes to cancel children; use `supervisorScope` for independent child coroutines where one failure should not cancel siblings.
3. [REQ] Use `data class` for DTOs and value objects; it auto-generates `equals`, `hashCode`, `toString`, `copy`, and `componentN` functions; limit to primary constructor properties.
4. [REQ] Use `sealed class`/`sealed interface` for restricted hierarchies (state, results, algebraic data types); exhaustive `when` expressions are enforced by the compiler.
5. [REQ] Use `when` as an expression (not statement) for exhaustive matching; compiler enforces exhaustiveness on sealed types and enums.
6. [REQ] Use extension functions (`fun String.myExt(): String`) for adding functionality without inheritance; keep extensions in a dedicated file or package to avoid namespace pollution.
7. [REQ] Use DSL builders with `@DslMarker` to prevent implicit receiver scope leakage; use `apply`, `run`, `let`, `also`, `with` scope functions idiomatically.
8. [REQ] Use Kotlin Multiplatform (KMP) for shared business logic across iOS/Android/Web/Backend; define `expect`/`actual` declarations for platform-specific APIs; use `commonMain` for shared code.
9. [REQ] Use Compose Multiplatform for shared UI (Android, iOS, Desktop, Web); keep state in `remember`/`mutableStateOf`; use `@Composable` functions and `LaunchedEffect` for side effects.
10. [REQ] Use the K2 compiler (default in Kotlin 2.x) for faster compilation; verify all dependencies are K2-compatible; use `-Xskip-prerelease-check` only for testing.
11. [REQ] Use `Flow`/`StateFlow`/`SharedFlow` for reactive streams; use `collectAsState()` or `collectAsStateWithLifecycle()` in Compose; use `stateIn()` to convert cold flows to hot.
12. [REQ] Use `kotlinx.serialization` with `@Serializable` for JSON (de)serialization; use `@SerialName` and `@SerialName` for field mapping; avoid reflection-based libraries.
13. [REQ] Use `Result<T>` for operations that may fail; use `getOrThrow()`, `getOrElse()`, `fold()` for handling; prefer `Result` over try-catch for API boundaries.
14. [PROHIBIT] Never use `runBlocking` in production code (especially Android main thread or server request handlers); it blocks the thread and can cause deadlocks.
15. [PROHIBIT] Never use `!!` (non-null assertion) in production code; use safe calls (`?.`), `let`, or `requireNotNull()` with descriptive messages.
[COMPAT]
- v2.x: K2 compiler, Kotlin Multiplatform (KMP), Compose Multiplatform 1.6+, Coroutines 1.8+, Serialization 1.7+
- v2.x: Gradle 8.x, Kotlin Gradle Plugin (KGP), Kotlin/Native (iOS), Kotlin/Wasm (experimental)
- v2.x: Targets: JVM 17+, Android, iOS (Native), JS/Wasm, Desktop (JVM)
[REFS]
- https://kotlinlang.org/docs/home.html
- https://kotlinlang.org/docs/coroutines-overview.html
- https://kotlinlang.org/docs/multiplatform.html
- https://www.jetbrains.com/compose-multiplatform/
- https://kotlinlang.org/docs/k2-compiler-migration-guide.html
- https://kotlinlang.org/api/kotlinx.coroutines/
