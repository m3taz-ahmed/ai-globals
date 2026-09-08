[TECH] Kotlin 2.4.20 (latest, Sep 2026)
[OBJ] Kotlin 2.4.20 — coroutine stack trace recovery, Kotlin/Native Swift export improvements, incremental `klib` compilation, Kotlin/Wasm Wasmtime support, Kotlin/JS browser-testing DSL, Gradle 9.7.0 support.
[RULES]
1. [REQ] Use coroutine stack trace recovery (stdlib) — better debugging for async code. Automatic in 2.4.20+.
2. [REQ] Use Kotlin/Native Swift export (Alpha→improving) — native structured concurrency, `kotlinx.coroutines` flows to Swift.
3. [REQ] Use incremental `klib` compilation for Kotlin/Native — faster incremental builds.
4. [REQ] Use Kotlin/Wasm with Wasmtime — Gradle plugin support for WebAssembly runtime.
5. [REQ] Use Kotlin/JS browser-testing DSL — suspend-lambda exports, ES2015 features in JS inlining.
6. [REQ] Use Gradle 9.7.0 — full compatibility, no deprecation warnings.
7. [REQ] Use stable guard conditions in `when`: `when (x) { is Int if x > 0 -> ... }`.
8. [REQ] Use non-local break/continue in inline lambdas.
9. [REQ] Use multi-dollar string interpolation: `$$variable` for literal `$`.
10. [REQ] Use context parameters (replaces context receivers): `context(val ctx: MyContext) fun doThing()`.
11. [REQ] Use Swift Package import for Kotlin/Native iOS targets.
12. [REQ] Use Xcode 26.4 support for Kotlin/Native.
13. [REQ] Use `kotlinx.coroutines` for async — `suspend fun`, `Flow`, `Channel`.
14. [PROHIBIT] Never use context receivers — replaced by context parameters in 2.4.0.
[COMPAT]
- Kotlin 2.4.20 (released Sep 7 2026).
- Kotlin 2.4.0 (released Jun 3 2026).
- Java 26 support.
- Gradle 7.6.3 through 9.7.0.
- Xcode 26.4 for Kotlin/Native.
- Swift Package import support.
[REFS]
- https://blog.jetbrains.com/kotlin/2026/09/kotlin-2-4-20-released/
- https://kotlinlang.org/docs/whatsnew24.html
- https://kotlinlang.org/docs/releases.html
