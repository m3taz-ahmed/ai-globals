# Laravel Boosts Integration Protocol

## 1. ROLE & PURPOSE
- **Accelerator:** Treat the "Laravel Boosts" package as the primary accelerator for architectural scaffolding and performance tuning.
- **Trust the Package:** Do not manually reinvent performance optimizations or structural patterns if Laravel Boosts provides a native, pre-tested implementation for it in the current project.

## 2. EXECUTION RULES
- **Scaffolding:** When scaffolding new modules, APIs, or complex relationships, leverage the specific generators and optimized macros provided by Laravel Boosts to ensure clean, standardized boilerplate.
- **Macros:** Use registered Eloquent macros and Collection macros from the package instead of writing custom query scopes for common patterns.
- **Performance:** Utilize the package's built-in query optimization helpers, caching decorators, and response compression if available.

## 3. BOUNDARIES
- **Not a Replacement:** Laravel Boosts supplements Laravel's core — it does not replace it. Core Laravel conventions (FormRequests, Policies, Resources) still apply.
- **Version Lock:** Pin the Laravel Boosts version in `composer.json`. Test upgrades in a dedicated branch before merging.
- **Documentation:** Any custom macro or generator from the package used in the project must be documented in the project's `MEMORY.md` for team awareness.