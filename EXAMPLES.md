# Examples: LLM Mistakes vs Correct Approaches

Real-world code examples demonstrating the four behavioral principles. Each shows what LLMs commonly do wrong and the correct approach.

---

## 1. Think Before Coding

### Example 1: Hidden Assumptions

**User Request:** "Add a feature to export client data"

**❌ What LLMs Do (Wrong Assumptions)**

```php
class ClientExportService
{
    public function export(string $format = 'csv'): string
    {
        $clients = Client::all(); // Assumes ALL clients
        
        $data = $clients->map(fn ($c) => [
            'id' => $c->id,
            'name' => $c->name,
            'email' => $c->email,
            'phone' => $c->phone,      // PII — should this be exported?
            'national_id' => $c->national_id, // Sensitive!
        ]);

        return match ($format) {
            'csv' => $this->toCsv($data),
            'json' => $data->toJson(),
            'xlsx' => $this->toExcel($data), // Nobody asked for Excel
        };
    }
}
```

**Problems:**
- Used `Client::all()` — no pagination, will crash on large datasets
- Included sensitive fields (`phone`, `national_id`) without asking
- Added Excel support nobody requested
- Assumed file export — maybe the user wanted an API endpoint?

**✅ What Should Happen (Surface Assumptions)**

```
Before implementing, I need to clarify:

1. **Scope**: Export all clients or filtered subset? (could be 100K+ rows)
2. **Fields**: Which fields? Some are sensitive (phone, national_id)
3. **Format**: CSV? JSON API response? Downloadable file?
4. **Delivery**: Direct download, or queue + email notification?

Simplest approach: Paginated API endpoint returning JSON.
For file export on large datasets, I'd recommend a queued job.

Which approach do you prefer?
```

### Example 2: Multiple Interpretations

**User Request:** "Make the booking search faster"

**❌ What LLMs Do (Pick Silently)**

```php
// Adds Redis caching, full-text search, and async processing
// without asking WHICH "faster" matters
class BookingSearchService
{
    public function search(string $query): LengthAwarePaginator
    {
        return Cache::tags(['bookings'])
            ->remember("search:{$query}", 3600, function () use ($query) {
                return Booking::search($query) // Scout full-text — overkill?
                    ->query(fn ($q) => $q->with(['client', 'facility']))
                    ->paginate(20);
            });
    }
}
```

**✅ What Should Happen**

```
"Make the search faster" could mean:

1. **Faster response time** — Add database indexes, optimize query
   → Run EXPLAIN on current query, add missing indexes
   → Effort: 30 minutes

2. **Handle more concurrent searches** — Connection pooling, query optimization
   → Effort: 2 hours

3. **Faster perceived speed** — Show results as you type (debounced AJAX)
   → Effort: 1 hour

Current search takes ~800ms. Let me run EXPLAIN first to find the bottleneck.
Which aspect matters most?
```

---

## 2. Simplicity First

### Example 1: Over-Abstraction

**User Request:** "Add a function to calculate the service discount"

**❌ What LLMs Do (Overengineered)**

```php
interface DiscountStrategy
{
    public function calculate(float $amount): float;
}

class PercentageDiscount implements DiscountStrategy
{
    public function __construct(private float $percentage) {}

    public function calculate(float $amount): float
    {
        return $amount * ($this->percentage / 100);
    }
}

class FixedDiscount implements DiscountStrategy
{
    public function __construct(private float $fixedAmount) {}

    public function calculate(float $amount): float
    {
        return min($this->fixedAmount, $amount);
    }
}

class TieredDiscount implements DiscountStrategy
{
    public function __construct(private array $tiers) {}

    public function calculate(float $amount): float
    {
        // 30 more lines for a feature nobody asked for...
    }
}

class DiscountCalculator
{
    public function __construct(
        private DiscountStrategy $strategy,
        private float $minPurchase = 0,
        private float $maxDiscount = PHP_FLOAT_MAX,
    ) {}

    public function apply(float $amount): float
    {
        if ($amount < $this->minPurchase) return 0;
        return min($this->strategy->calculate($amount), $this->maxDiscount);
    }
}

// Usage requires understanding 4 classes for a simple calculation
```

**✅ What Should Happen (Simple)**

```php
function calculateDiscount(float $amount, float $percent): float
{
    return $amount * ($percent / 100);
}

// Usage
$discount = calculateDiscount(500.00, 10); // 50.00
```

**When to add complexity:** Only when you actually need multiple discount types. If the requirement comes later, refactor then.

### Example 2: Speculative Features

**User Request:** "Save user notification preferences"

**❌ What LLMs Do (Unnecessary Features)**

```php
class NotificationPreferenceService
{
    public function __construct(
        private NotificationPreferenceRepository $repo,
        private CacheManager $cache,
        private PreferenceValidator $validator,
        private AuditLogger $auditLogger,
    ) {}

    public function save(
        int $userId,
        array $preferences,
        bool $merge = true,
        bool $validate = true,
        bool $notify = false,
    ): void {
        if ($validate) {
            $this->validator->validate($preferences);
        }

        $existing = $merge ? $this->repo->get($userId) : [];
        $merged = array_merge($existing, $preferences);

        $this->repo->save($userId, $merged);
        $this->cache->tags(['preferences'])->forget("user:{$userId}");
        $this->auditLogger->log('preferences.updated', $userId, $merged);

        if ($notify) {
            event(new PreferencesUpdated($userId, $merged));
        }
    }
}
```

**✅ What Should Happen (Just What Was Asked)**

```php
class NotificationPreferenceService
{
    public function save(User $user, array $preferences): void
    {
        $user->update(['notification_preferences' => $preferences]);
    }
}
```

**Add later if needed:** Caching (when performance matters), validation (when bad data appears), audit logging (when compliance requires it).

---

## 3. Surgical Changes

### Example 1: Drive-by Refactoring

**User Request:** "Fix the bug where empty emails crash the booking validator"

**❌ What LLMs Do (Too Much)**

```diff
  class BookingValidator
  {
-     public function validate($data)
+     public function validate(array $data): bool
      {
-         // Check email
-         if (!$data['email']) {
+         /** Validate booking data. */
+         $email = trim($data['email'] ?? '');
+
+         // Validate email format
+         if (empty($email)) {
              throw new ValidationException('Email required');
          }
-
-         if (!filter_var($data['email'], FILTER_VALIDATE_EMAIL)) {
+         if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
              throw new ValidationException('Invalid email');
          }

-         // Check date
-         if (!$data['date']) {
+         // Validate booking date
+         $date = $data['date'] ?? null;
+         if (empty($date)) {
              throw new ValidationException('Date required');
          }
+         if (Carbon::parse($date)->isPast()) {
+             throw new ValidationException('Date must be in the future');
+         }

          return true;
      }
  }
```

**Problems:**
- Added return type hint nobody asked for
- Added docblock
- Changed comment text
- Added `trim()` on email (not the bug)
- Added past-date validation (new feature!)
- Refactored date handling

**✅ What Should Happen (Surgical)**

```diff
  class BookingValidator
  {
      public function validate($data)
      {
          // Check email
-         if (!$data['email']) {
+         if (empty($data['email'] ?? '')) {
              throw new ValidationException('Email required');
          }

          if (!filter_var($data['email'], FILTER_VALIDATE_EMAIL)) {
              throw new ValidationException('Invalid email');
          }

          // Check date
          if (!$data['date']) {
              throw new ValidationException('Date required');
          }

          return true;
      }
  }
```

**Only changed:** The specific line that crashes on empty/missing email. Nothing else.

### Example 2: Style Drift in JavaScript

**User Request:** "Add loading state to the fetch call"

**❌ What LLMs Do (Reformat Everything)**

```diff
- function fetchBookings() {
-     fetch('/api/bookings')
-         .then(res => res.json())
-         .then(data => {
-             renderTable(data)
-         })
-         .catch(err => {
-             console.log('Error:', err)
-         })
+ const fetchBookings = async (): Promise<void> => {
+     setLoading(true);
+     try {
+         const response = await fetch("/api/bookings");
+         const data: Booking[] = await response.json();
+         renderTable(data);
+     } catch (error: unknown) {
+         console.error("Error fetching bookings:", error);
+     } finally {
+         setLoading(false);
+     }
  }
```

**Problems:**
- Converted to `async/await` (style change, not requested)
- Changed to arrow function
- Added TypeScript types
- Changed `console.log` to `console.error`
- Changed quote style (single → double)
- Changed variable names

**✅ What Should Happen (Match Existing Style)**

```diff
  function fetchBookings() {
+     setLoading(true)
      fetch('/api/bookings')
          .then(res => res.json())
          .then(data => {
              renderTable(data)
+             setLoading(false)
          })
          .catch(err => {
              console.log('Error:', err)
+             setLoading(false)
          })
  }
```

**Matched:** Function declaration style, single quotes, existing error handling, `.then()` chain.

---

## 4. Goal-Driven Execution

### Example 1: Vague vs. Verifiable

**User Request:** "Fix the booking system"

**❌ What LLMs Do (Vague Approach)**

```
I'll fix the booking system by:
1. Reviewing the code
2. Identifying issues
3. Making improvements
4. Testing the changes
```

*Proceeds to make changes without clear success criteria*

**✅ What Should Happen (Verifiable Goals)**

```
"Fix the booking system" is too broad. What specific issue?

If the issue is "double bookings are possible for the same time slot":

Plan:
1. Write test: Create two bookings for same slot → expect second to fail
   → verify: Test fails (reproduces bug)

2. Add unique constraint on (facility_id, date, time_slot) in migration
   → verify: Test passes

3. Add validation in BookingService::create() to check slot availability
   → verify: Integration test passes

4. Check edge cases: concurrent requests, timezone issues
   → verify: Additional tests pass

5. Run full test suite
   → verify: All green, no regressions

What's the specific booking issue you're seeing?
```

### Example 2: Multi-Step with Verification

**User Request:** "Add rate limiting to the API"

**❌ What LLMs Do (All at Once)**

```php
// 300-line commit with Redis rate limiter, custom middleware,
// per-endpoint configuration, dashboard UI, and monitoring
// — no clear verification steps
```

**✅ What Should Happen (Incremental with Verification)**

```
Plan for rate limiting:

1. Apply Laravel's built-in ThrottleRequests middleware to API routes
   → verify: Hit /api/bookings 61 times → get 429 on 61st

2. Configure per-route limits in RouteServiceProvider
   → verify: /api/search allows 30/min, /api/bookings allows 60/min

3. Add custom response format for 429 errors
   → verify: Response includes Retry-After header and JSON error body

4. Add rate limit headers to successful responses
   → verify: X-RateLimit-Remaining shows in response headers

Each step is independently testable and deployable.
Start with step 1?
```

---

## Anti-Patterns Summary

| Principle | Anti-Pattern | Fix |
|---|---|---|
| Think Before Coding | Silently assumes scope, fields, format | List assumptions, ask for clarification |
| Simplicity First | Strategy Pattern for a single calculation | One function until complexity is actually needed |
| Surgical Changes | Reformats quotes, adds types while fixing a bug | Only change lines that fix the reported issue |
| Goal-Driven | "I'll review and improve the code" | "Write test for bug X → make it pass → verify no regressions" |

## Key Insight

> The "overcomplicated" examples aren't obviously wrong — they follow design patterns and best practices. The problem is **timing**: they add complexity before it's needed, which makes code harder to understand, introduces more bugs, takes longer to implement, and is harder to test.
>
> **Simple code that works > Complex code that "might be needed later."**
