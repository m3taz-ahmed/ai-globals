[TECH] Kotlin 2.4 (latest 2.4.10, Jul 2026)
[OBJ] Kotlin programming language — stable guard conditions, non-local break/continue, multi-dollar interpolation, context parameters, Xcode 26 support. 2.x source-compatible.
[RULES]
1. [REQ] Use stable guard conditions in `when` expressions: `when (x) { is Int if x > 0 -> ... }` — no longer experimental.
2. [REQ] Use non-local break/continue in lambdas within inline functions — `break`/`continue` can exit enclosing loop from inside inline lambda.
3. [REQ] Use multi-dollar string interpolation: `$$variable` for literal `$`, `$${expr}` for nested — enables complex template strings.
4. [REQ] Use context parameters (replaces context receivers): `context(val ctx: MyContext) fun doThing()` — explicit, type-safe.
5. [REQ] Kotlin 2.x is source-compatible — existing 2.x code compiles on 2.4 without changes.
6. [REQ] Use Xcode 26 support for Kotlin/Native iOS targets — update toolchain in build config.
7. [REQ] Use Kotlin coroutines (`kotlinx.coroutines`) for async — `suspend fun`, `Flow`, `Channel`.
8. [REQ] Use `data class` for DTOs — auto-generates `equals`, `hashCode`, `toString`, `copy`, `componentN`.
9. [REQ] Use `sealed class` / `sealed interface` for restricted hierarchies — exhaustive `when`.
10. [REQ] Use `val` for immutable references; `var` only when mutation is required.
11. [REQ] Use `?.let {}` / `?:` / `?: return` for null-safety — never `!!` in production code.
12. [REQ] Use K2 compiler (default since 2.0) — faster, better inference.
13. [PROHIBIT] Never use `!!` (force unwrap) in production — use safe calls.
14. [PROHIBIT] Never use context receivers (deprecated) — use context parameters.
15. [PROHIBIT] Never use `var` for properties that should be immutable.
16. [PROHIBIT] Never use platform types without explicit nullability annotations for interop.
17. [CMD] `kotlinc` — compile.
18. [CMD] `./gradlew build` — Gradle build.
19. [CMD] `./gradlew test` — run tests.
20. [CMD] `kotlin main.kt` — run script.
[COMPAT]
- Kotlin 2.4.10: latest (Jul 2026).
- 2.x source-compatible.
- K2 compiler default.
- Xcode 26 support (Kotlin/Native).
- Guard conditions: stable.
- Non-local break/continue: stable.
- Context parameters: stable (replaces context receivers).
[REFS]
- https://kotlinlang.org/docs/home.html
- https://kotlinlang.org/docs/whatsnew24.html
- https://kotlinlang.org/docs/coroutines-overview.html
