# Laravel 12.x Strict Standards
- **Routing:** Prefer PHP Attributes for routing directly in Controllers (e.g., `#[Get('/api/resource')]`) to co-locate logic and routes.
- **Model Strictness:** `Model::shouldBeStrict()` MUST be enabled globally to crash on N+1 queries, silent discards, and lazy loading during development.
- **Architecture:** Enforce "Thin Controllers, Fat Services". Controllers should only handle input/output and delegation. All business logic belongs in `App\Services`.
- **Database:** Use Laravel 12's improved concurrency and task batching for long-running processes or bulk updates.
- **API Resources:** All external outputs MUST use Laravel API Resources to ensure a consistent, versioned JSON structure.
- **Websockets:** Default to Laravel Reverb for real-time features.