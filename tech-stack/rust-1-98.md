[TECH] Rust 1.98 (latest 1.98.1, Sep 2026)
[OBJ] Rust programming language — algebraic float methods, buffered integer `format_into`, `&mut` lifetime unsize coercion, new lints, `{core,std}::derive` stabilized, more Tier 2/3 targets.
[RULES]
1. [REQ] Use algebraic float methods: `f.ln()`, `f.exp()`, `f.powi()` etc. as methods on `f32`/`f64` (replaced free-function `f64::ln(x)` style for new code).
2. [REQ] Use buffered integer `format_into` for efficient integer-to-string formatting — avoids allocation for known buffer sizes.
3. [REQ] Use `&mut` lifetime unsize coercion for coercing `&mut [T; N]` to `&mut [T]` across lifetimes without explicit reborrow.
4. [REQ] Use `{core,std}::derive` stabilized macros for custom derive in `no_std` contexts — `#[derive(core::fmt::Debug)]` etc.
5. [REQ] Address new lints: `invalid_runtime_symbol_definitions` (invalid `#[link_name]` / symbol attrs), `c_void_returns` (returning `c_void` from extern functions).
6. [REQ] Some lints/imports turned into hard errors — run `cargo fix --edition` to auto-migrate; review warnings as errors.
7. [REQ] Use `cargo clippy` with latest lints — fix all `invalid_runtime_symbol_definitions` and `c_void_returns` warnings.
8. [REQ] Use `cargo fmt` before commits — enforce formatting.
9. [REQ] Use `Result<T, E>` for all fallible operations; never `unwrap()` / `expect()` in production paths.
10. [REQ] Use `Cargo.lock` checked in for binaries; do not check in for libraries.
11. [REQ] Use `cargo audit` for vulnerability scanning — integrate in CI.
12. [REQ] Use edition 2024 (or latest stable) in `Cargo.toml` `edition = "2024"`.
13. [REQ] Use `#[derive(Debug, Clone)]` via `{core,std}::derive` for `no_std` crates.
14. [PROHIBIT] Never use `unwrap()` / `expect()` in production code — use `?` or explicit match.
15. [PROHIBIT] Never ignore compiler warnings — treat as errors with `RUSTFLAGS="-D warnings"`.
16. [PROHIBIT] Never use deprecated free-function float math — use method syntax.
17. [PROHIBIT] Never return `c_void` from extern functions — use proper return types.
18. [CMD] `cargo build` — compile.
19. [CMD] `cargo clippy -- -D warnings` — lint with warnings as errors.
20. [CMD] `cargo fix --edition` — auto-migrate for edition + hard-error changes.
[COMPAT]
- 1.98.1: latest stable patch (Sep 2026).
- New Tier 2/3 targets added.
- Some lints/imports promoted to hard errors — run `cargo fix`.
- `{core,std}::derive` stabilized for `no_std`.
- Edition 2024 recommended.
[REFS]
- https://doc.rust-lang.org/std/
- https://blog.rust-lang.org/
- https://doc.rust-lang.org/cargo/
- https://github.com/rust-lang/rust-clippy
