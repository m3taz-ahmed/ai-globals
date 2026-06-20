[FILE] spec-cache
[OBJ] Manage AI tech stack context cache to prevent version hallucinations.
[RULES]
1. [REQ] Cache Read: Always read `spec.md` in project root at init. Adhere strictly to versions specified.
2. [REQ] Cache Generation: If `spec.md` missing, read `composer.json`/`package.json` to detect stack.
3. [REQ] Cache Format: Write dense, single-line format optimized for AI ONLY (e.g. `php:8.2|laravel:11|filament:5`). No prose.
4. [REQ] Cache Ignored: Immediately append `spec.md` to `.gitignore`. Never commit.
