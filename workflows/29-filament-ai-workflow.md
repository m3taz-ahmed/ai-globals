[WORKFLOW] 29-filament-ai-workflow
[TRIGGER] filament ai, ai filament, boost filament, filacheck, ai workflow filament, filament copilot, ai panel
[OBJ] AI-assisted Filament development using Boost + Compass + FilaCheck pipeline.
[ENGINE] None (declarative workflow)
[RULES]
1. [REQ] Detect: Trigger on "filament ai", "ai filament", "boost filament", "filacheck", "ai workflow filament".
2. [REQ] Prerequisites Check: Verify `laravel/boost` installed (`composer.json` dev deps). If missing, instruct: `composer require laravel/boost --dev`.
3. [REQ] Prerequisites Check: Verify `aldesrahim/filament-compass` installed. If missing, instruct: `composer require aldesrahim/filament-compass --dev`.
4. [REQ] Prerequisites Check: Verify `laraveldaily/filacheck` installed. If missing, instruct: `composer require laraveldaily/filacheck --dev`.
5. [REQ] Context Setup: Run `php artisan boost:install` if `.ai/` directory doesn't exist. Run `php artisan compass:install` to link Filament docs.
6. [REQ] Context7 MCP: Query Context7 for `filament` framework docs before generating any Filament code. Use `resolve-library-id` then `get-library-docs`.
7. [REQ] Code Generation: Generate Filament code (Resources, Pages, Widgets, Plugins) following `tech-stack/filament-4.md` or `tech-stack/filament-5.md` rules based on lockfile version `[VER-01]`.
8. [REQ] Validation: After generating code, run `vendor/bin/filacheck` to validate. If issues found, fix and re-run. NEVER skip this step.
9. [REQ] Validation: Run `vendor/bin/filacheck --dirty` to scan only uncommitted files for fast iteration.
10. [REQ] Auto-Fix: If FilaCheck reports fixable issues, run `vendor/bin/filacheck --fix` (beta). Review changes before committing.
11. [REQ] Testing: Run FAST tier `php artisan test --filter=<GeneratedResource>` for touched code. Then FULL tier before declaring done.
12. [REQ] Security: Verify generated code follows `[SEC-05]` RBAC (Filament Shield/policy gates), `[SEC-03]` $fillable whitelist, `[SEC-07]` DTO projections.
13. [REQ] Pattern Check: Verify generated code uses Schema Separation (Forms/Tables extracted to dedicated classes for complex Resources), EvaluatesClosures (closure-based config with DI), two-phase Plugin lifecycle (register→boot).
14. [REQ] Output: Report generated files, FilaCheck results, test results, and any security concerns.
15. [PROHIBIT] NEVER commit AI-generated Filament code without FilaCheck validation. NEVER skip Context7 MCP query. NEVER default to Filament v3 or v4 without reading lockfile `[VER-01]`.
