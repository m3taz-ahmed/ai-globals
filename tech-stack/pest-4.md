# Pest v4.x Testing Standards
> [!NOTE]
> Pest 4 focuses on speed, architecture testing, and native PHP 8.4 support.

## 1. ARCHITECTURE TESTING
- Use `arch()` expectations to enforce architectural rules (e.g., "Controllers should not use Models directly").
- `pest()->extend(Tests\TestCase::class)->use(Illuminate\Foundation\Testing\RefreshDatabase::class);`

## 2. SUITE ORGANIZATION
- **Feature Tests:** One test file per Controller/Service.
- **Unit Tests:** Pure logic tests without database access.
- **Datasets:** Use `with()` for parameterized testing to cover multiple edge cases with one test.

## 3. CLEAN EXPECTATIONS
- Use the `expect()` API exclusively. Avoid PHPUnit-style assertions.
- `expect($user)->toBeInstanceOf(User::class)->and($user->email)->toBe('test@example.com');`

## 4. PERFORMANCE
- Use `--parallel` for CI/CD pipelines.
- Use `RefreshDatabase` trait for integration tests, but prefer `DatabaseTransactions` if the database state doesn't need a full reset.
