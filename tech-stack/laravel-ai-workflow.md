[TECH] laravel-ai-workflow
[OBJ] AI-assisted Laravel + Filament development workflow using Boost + FilaCheck + Compass.
[RULES]
1. [REQ] Laravel Boost: `composer require laravel/boost --dev` → MCP server loads `.ai/` context files into Claude Code/Cursor. Run `php artisan boost:install` to scaffold `.ai/` directory with Laravel-specific knowledge.
2. [REQ] Filament Compass: `composer require aldesrahim/filament-compass --dev` → provides Filament v5 patterns/conventions/recipes as LLM-ready docs. Loaded into Boost via `.ai/` symlinks. Run `php artisan compass:install` to link.
3. [REQ] FilaCheck Validator: `composer require laraveldaily/filacheck --dev` → static analyzer validates AI-generated Filament code. Run `vendor/bin/filacheck` (scan all), `--dirty` (uncommitted only), `--fix` (auto-fix beta). Required after every AI-generated Filament code batch.
4. [REQ] Workflow: Boost loads Compass → AI generates Filament code → FilaCheck validates output → fix issues → repeat. Three-tool pipeline ensures AI code matches Filament conventions.
5. [REQ] Filament Blueprint (optional, $49): Official Boost extension for detailed implementation plans + security reports. Use for complex Filament features (>3 Resources). `composer require filament/blueprint`.
6. [REQ] Context Files: `.ai/` directory contains: `laravel.md` (framework conventions), `filament.md` (panel patterns), `project.md` (app-specific patterns). Boost auto-discovers and loads these into AI context.
7. [REQ] FilaCheck Rules: Catches deprecated methods (`->visible(fn()` vs `->hidden(fn()`), wrong namespaces (`Filament\Forms\` vs `Filament\Schemas\`), missing `->live()` on reactive fields, incorrect `configureUsing` usage. Run before every commit with Filament changes.
8. [PROHIBIT] NEVER commit AI-generated Filament code without running FilaCheck first. NEVER skip the Boost context loading step — AI without context produces non-idiomatic Filament code.
