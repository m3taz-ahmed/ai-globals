[TECH] laravel-13
[OBJ] Laravel 13.x Strict Standards (Stable Mar 2026).
[RULES]
1. [REQ] Types: PHP 8.4 asymmetric visibility (`public private(set)`). Native Attributes. `strict_types=1`.
2. [REQ] Context API: Inject trace/tenant IDs into `Context`. Auto-propagate to logs/queues.
3. [REQ] Engine: Bind infra in `bootstrap/app.php`. ⛔ dead service providers.
4. [REQ] AI/Features: Use native `whereVectorSimilarTo()`. Stream LLM via `->stream()`. JSON:API native structures.
5. [OPS] Environment file precedence: Laravel's `LoadEnvironmentVariables` auto-selects `.env.{APP_ENV}` when `APP_ENV` is set and that file exists. Do NOT commit `.env.staging`/`.env.production` to the repo; use `.env.staging.example` templates and add `.env.*` to `.gitignore`.
