[TECH] laravel-horizon
[OBJ] Laravel Horizon Queue Architecture.
[RULES]
1. [REQ] Architecture: Segregate queues (high/default/low/webhooks). Use Horizon auto-scaling based on pressure.
2. [REQ] Patterns: Batch large jobs. Rate limit 3rd-party APIs (`Redis::funnel`). Define retry/fallback strategies.
3. [REQ] Context: Append trace/tenant IDs via `Context::add()`.
4. [PROHIBIT] Constraints: NEVER run long sync code in web request. Jobs MUST be idempotent. NO global state.
