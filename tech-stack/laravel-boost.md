# Laravel Boosts Integration Protocol
- **Role:** Treat the "Laravel Boosts" technical package as the primary accelerator for architectural scaffolding and performance tuning.
- **Execution:** When scaffolding new modules, APIs, or complex relationships, leverage the specific generators and optimized macros provided by Laravel Boosts to ensure clean, standardized boilerplate.
- **Rule:** Do not manually reinvent performance optimizations or structural patterns if Laravel Boosts provides a native, pre-tested implementation for it in the current project.
# Laravel 12.x Strict Standards
- **Routing:** Prefer PHP Attributes for routing directly in Controllers (e.g., `#[Get('/api/resource')]`) to co-locate logic and routes.
- **Model Strictness:** `Model::shouldBeStrict()` MUST be enabled globally to crash on N+1 queries, silent discards, and lazy loading.
- **Websockets:** Default to Laravel Reverb for real-time features.