[TECH] Pest PHP 5 (latest 5.1.3, Aug 2026)
[OBJ] Pest v5.x — TIA (Test Impact Analysis) engine, Agent plugin for AI-generated code verification, Evals plugin for LLM output scoring, first-party PHPStan plugin, Rector rules, Playwright browser testing. Requires PHP 8.4+ / PHPUnit 13+.
[RULES]
1. [REQ] Use TIA (Test Impact Analysis) engine — re-runs only changed tests + replays cached coverage. `pest --tia` to enable. Massive speedup for large test suites.
2. [REQ] Use Agent plugin (`--agent`) to verify AI-generated changes end-to-end — validates AI code modifications with full test coverage.
3. [REQ] Use Evals plugin for LLM output scoring — test and score LLM-generated content quality.
4. [REQ] Use first-party PHPStan plugin for static analysis integration — `pest --phpstan` runs both.
5. [REQ] Use Rector rules for Pest assertions — auto-upgrade deprecated assertion patterns.
6. [REQ] Use new expectations for emails, ULIDs, IPs — `expect($email)->toBeEmail()`, `expect($id)->toBeUlid()`, `expect($ip)->toBeIp()`.
7. [REQ] Use Playwright for browser testing — `pest --browser` runs E2E tests via Playwright.
8. [REQ] Requires PHP 8.4+ and PHPUnit 13+ — upgrade PHP and PHPUnit before upgrading Pest.
9. [REQ] All Pest plugins must bump to `^5.0` — check `composer.json` for plugin compatibility.
10. [REQ] Use `pest:install` to scaffold test structure — creates `tests/Pest.php` with base expectations.
11. [REQ] Use datasets for parameterized tests: `it('can add', fn($a, $b, $expected) => ...)->with([[1, 2, 3], [4, 5, 9]])`.
12. [PROHIBIT] Never use Pest 4 with PHP 8.4 — upgrade to Pest 5 first.
13. [PROHIBIT] Never skip the TIA engine for large suites — it's the primary performance benefit.
[COMPAT]
- Pest 5.1.3 (released Aug 25 2026).
- v5.0.0 released Jul 28 2026 (Laracon US 2026).
- Requires PHP 8.4+, PHPUnit 13+.
- All plugins must be ^5.0 compatible.
- Laravel 12+ recommended for integration.
[REFS]
- https://pestphp.com/docs/pest5-now-available
- https://github.com/pestphp/pest/releases/tag/v5.0.0
- https://laravel-news.com/pest-5
