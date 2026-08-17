[WORKFLOW] testing-tiers
[OBJ] Per-stack fast/full test commands — quick reference for ANY project under aiZee.
[TRIGGER] testing-tiers
[RULES]
## Two-Tier Testing Protocol

Every project under aiZee follows two tiers:

| Tier | When | What | Max time |
|------|------|------|----------|
| FAST | During iteration, after each change | Targeted tests for touched code only | ~5s |
| FULL | Before declaring done, before commit | Complete suite + coverage | No limit |

---

## PHP / Laravel / Pest

```bash
# FAST — targeted (after editing UserService)
php artisan test --filter=UserServiceTest
php artisan test --filter='test_can_create_user'

# FULL — before done
php artisan test
php artisan test --coverage --min=80
```

Slow test marking:
```php
it('syncs with external API', function () {
    // ...
})->group('slow');  // skip with: --exclude-group=slow
```

---

## JavaScript / TypeScript / Vitest

```bash
# FAST — targeted (after editing useAuth.ts)
npx vitest run src/composables/useAuth.test.ts
npx vitest run -t "can login"

# FULL — before done
npx vitest run --coverage
npx vitest run --coverage --coverage.thresholds.lines=80
```

Slow test marking:
```ts
it('loads full dataset', () => { ... }, 30000) // timeout = slow marker
// or
describe.skipIf(process.env.FAST_TEST)('slow suite', () => { ... })
```

---

## Python / pytest

```bash
# FAST — targeted (after editing auth.py)
pytest tests/test_auth.py -q --no-cov --tb=short
pytest tests/test_auth.py::test_login -q --no-cov

# FULL — before done
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
pytest -q  # if coverage is in pyproject.toml addopts
```

Slow test marking:
```python
@pytest.mark.slow
def test_full_dataset_load(): ...
# skip with: pytest -m "not slow"
```

---

## Go

```bash
# FAST — targeted (after editing auth package)
go test ./internal/auth/... -short

# FULL — before done
go test ./... -race -cover -coverprofile=coverage.out
go tool cover -func=coverage.out  # check >= 80%
```

Slow test marking:
```go
func TestFullIntegration(t *testing.T) {
    if testing.Short() { t.Skip("skipping in short mode") }
    // ...
}
```

---

## React / Next.js / Testing Library

```bash
# FAST — targeted (after editing LoginForm.tsx)
npx vitest run src/components/LoginForm.test.tsx

# FULL — before done
npx vitest run --coverage
npx playwright test  # E2E suite
```

---

## Node.js / Express / Jest

```bash
# FAST — targeted
npx jest tests/auth.test.ts --testPathPattern=auth

# FULL — before done
npx jest --coverage --coverageThreshold='{"global":{"lines":80}}'
```

---

## General Rules (all stacks)

1. **FAST tier = targeted only.** Run only the test file(s) for the code you touched. Never the full suite.
2. **FULL tier = mandatory before done.** No exceptions. If it fails, fix it — don't skip.
3. **Coverage is FULL-tier only.** Never run coverage during fast iteration.
4. **Slow tests must be marked.** Use the framework's group/skip/标记 mechanism so fast tier stays under 5s.
5. **If no test framework exists** in the project, write the first test for the touched code before declaring done.
6. **E2E tests are always FULL tier.** Never run Playwright/Cypress during fast iteration.
