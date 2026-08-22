[TECH] Rust 1.80
[OBJ] Systems programming language with zero-cost abstractions, ownership-based memory safety, async/await, traits, and a rich macro system.
[RULES]
1. [REQ] Follow ownership rules: each value has one owner, borrowed by `&T` (shared) or `&mut T` (exclusive); data must outlive all references to it.
2. [REQ] Use lifetimes explicitly only when the compiler cannot infer them; name lifetimes with `'a`, `'b` in function signatures where multiple references interact.
3. [REQ] Use `Result<T, E>` for recoverable errors and `?` operator for propagation; use `Option<T>` for nullable values; never use `unwrap()`/`expect()` in production code except in tests.
4. [REQ] Define traits for shared behavior (`trait Foo { fn bar(&self); }`); use trait bounds (`fn foo<T: Foo>(v: T)`) or `impl Trait` for generic abstractions.
5. [REQ] Use `async/await` with a runtime (tokio, async-std); mark functions `async fn` and `.await` futures; never block (`std::thread::sleep`) inside async contexts.
6. [REQ] Use `Arc<Mutex<T>>` for shared mutable state across async tasks; use `Arc<RwLock<T>>` for read-heavy workloads; prefer message passing (`mpsc` channels) over shared state.
7. [REQ] Use `serde` with `#[derive(Serialize, Deserialize)]` for (de)serialization; use `#[serde(rename_all = "snake_case")]` and `#[serde(skip_serializing_if)]` for API conventions.
8. [REQ] Use `Cargo.toml` for dependency management; pin versions with `^` (default) or `=` for exact; run `cargo audit` in CI for vulnerability scanning.
9. [REQ] Use `thiserror` for library error types (derives `Error`) and `anyhow` for application-level error handling; never use `Box<dyn Error>` in public APIs.
10. [REQ] Use `#[derive(Debug, Clone)]` on public types; implement `Display` and `Error` for custom error types; use `#[non_exhaustive]` on public enums/structs for forward compatibility.
11. [REQ] Use `cargo fmt`, `cargo clippy -- -D warnings`, and `cargo test` in CI; run `cargo tarpaulin` or `cargo llvm-cov` for coverage.
12. [REQ] Use declarative macros (`macro_rules!`) for repetitive code patterns; use procedural macros (`#[derive]`) for code generation; avoid `unsafe` unless FFI or performance-critical.
13. [REQ] Use `tokio::spawn` for detached async tasks with proper error handling; use `tokio::select!` for concurrent operation cancellation; always handle `JoinError` from spawned tasks.
14. [PROHIBIT] Never use `unsafe` without a safety comment documenting invariants; `unsafe` blocks must justify why the operation is sound.
15. [PROHIBIT] Never use `.unwrap()` or `.expect()` on `Result`/`Option` in production paths; use `?`, `match`, or `if let` for safe extraction.
[COMPAT]
- v1.80: Edition 2021, async/await, GATs (generic associated types), `let-else`, `let-chains` (stabilized in 1.88)
- v1.80: Cargo workspaces, `cargo fmt`, `cargo clippy`, `cargo audit`, `cargo tarpaulin`
- v1.80: Tokio 1.x, serde 1.x, thiserror 1.x, anyhow 1.x, clap 4.x
[REFS]
- https://doc.rust-lang.org/
- https://doc.rust-lang.org/book/
- https://doc.rust-lang.org/reference/
- https://doc.rust-lang.org/cargo/
- https://serde.rs/
- https://tokio.rs/
