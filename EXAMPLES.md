# Examples: LLM Mistakes vs Correct Approaches
> Real-world code examples demonstrating global behavioral principles and anti-pattern resolutions.

| Section | Domain | Stakes |
|---|---|---|
| [1. Think Before Coding](#1-think-before-coding) | Laravel / Export | High — PII leak risk |
| [2. Simplicity First](#2-simplicity-first) | PHP / Logic | Medium — over-engineering |
| [3. Surgical Changes](#3-surgical-changes) | PHP / JS | Medium — scope creep |
| [4. Goal-Driven](#4-goal-driven-execution) | Laravel | High — verification |
| [5. Laravel 12 Security](#5-laravel-12-security) | Laravel 12 | 🔴 Critical |
| [6. React Security](#6-react-component-security) | React | 🔴 Critical |
| [7. SQL Injection](#7-sql-injection-prevention) | PHP / Laravel | 🔴 Critical |

---

## 1. Think Before Coding

### Ex 1: Hidden Assumptions
- **Request:** "Add feature to export client data"
- **❌:**
  ```php
  class ClientExportService {
      public function export(string $format = 'csv') {
          $clients = Client::all(); // N+1/Memory leak!
          $data = $clients->map(fn($c) => [
              'id' => $c->id, 'name' => $c->name,
              'email' => $c->email, 'phone' => $c->phone, // PII leak!
          ]);
          return match ($format) { 'csv' => $this->toCsv($data), 'xlsx' => $this->toExcel($data) }; // Excel unrequested
      }
  }
  ```
- **✅:** Stop & ask:
  1. **Scope:** Filtered subset or all? (100k+ rows risk).
  2. **PII:** Exclude sensitive fields (phone, national_id)?
  3. **Format:** CSV, JSON API, or queue/SSE?

### Ex 2: Multiple Interpretations
- **Request:** "Make the booking search faster"
- **❌:** Silently decides to add Scout, full-text engine, Redis caching, etc.
- **✅:** Present options:
  1. Database index tuning (EXPLAIN analysis) [30 min]
  2. Cache integration / connection pooling [2 hours]
  3. UI debounced search perception improvements [1 hour]

---

## 2. Simplicity First

### Ex 1: Over-Abstraction
- **Request:** "Calculate service discount"
- **❌:** Strategy pattern with `DiscountStrategy`, `PercentageDiscount`, `FixedDiscount`, `DiscountCalculator`.
- **✅:**
  ```php
  function calculateDiscount(float $amount, float $percent): float { return $amount * ($percent / 100); }
  ```

### Ex 2: Speculative Features
- **Request:** "Save user notification preferences"
- **❌:** Adds `CacheManager`, `PreferenceValidator`, `AuditLogger`, `PreferencesUpdated` event, `merge` parameters.
- **✅:**
  ```php
  class NotificationPreferenceService {
      public function save(User $user, array $preferences): void { $user->update(['notification_preferences' => $preferences]); }
  }
  ```

---

## 3. Surgical Changes

### Ex 1: Drive-by Refactoring
- **Request:** "Fix validator crash on empty email"
- **❌:** Adds types, docblocks, trims fields, and validates dates which were not requested.
- **✅:** Only touch the crash line:
  ```diff
  - if (!$data['email']) {
  + if (empty($data['email'] ?? '')) {
  ```

### Ex 2: Style Drift in JS
- **Request:** "Add loading state to fetch"
- **❌:** Converts ES5 `.then` chain to ES6 `async/await` arrow functions, typescript types, double quotes.
- **✅:** Maintain existing `.then()` syntax, single quotes, and spacing:
  ```javascript
  function fetchBookings() {
  +   setLoading(true)
      fetch('/api/bookings').then(res => res.json()).then(data => { renderTable(data); setLoading(false) })
  }
  ```

---

## 4. Goal-Driven Execution

### Ex 1: Vague vs Verifiable
- **Request:** "Fix booking system slot overlaps"
- **❌:** "I will review bookings, find issues, make changes, and test."
- **✅:**
  1. Write failing test: Two bookings in same slot → expect second to fail.
  2. Add database unique key constraint on (facility_id, slot_time).
  3. Add model/service validation. Verify integration tests pass.

---

## 5. Laravel 12 Security

### Ex 1: Mass Assignment
- **❌:** `protected $guarded = [];` (IDOR/Privilege escalation risk).
- **✅:** Whitelist: `protected $fillable = ['name', 'email', 'password'];`

### Ex 2: N+1 Database Queries
- **❌:** `Order::all()` → Blade `@foreach` accessing `$order->customer->name` (500 orders = 501 queries).
- **✅:** `Order::with('customer')->get()` (2 queries total).

---

## 6. React Component Security

### Ex 1: XSS via dangerouslySetInnerHTML
- **❌:** `<div dangerouslySetInnerHTML={{ __html: bio }} />` (User input executes raw scripts).
- **✅:** Use `DOMPurify` to whitelist tags or render as text `<p>{bio}</p>` (auto-escaped).

### Ex 2: Client-Side Data Leakage
- **❌:** Server component passing full database model (e.g. including passwordHash, raw session keys) to client component.
- **✅:** Select explicit fields only: `select: { id: true, name: true, avatarUrl: true }`.

---

## 7. SQL Injection Prevention

### Ex 1: Raw Query String Interpolation
- **❌:** `DB::select("SELECT * FROM bookings WHERE client_name = '$name'")` (attacer input wipes table).
- **✅:** Use query builder `Booking::where('client_name', $name)->paginate()` or bindings `['%' . $name . '%']`.

### Ex 2: Validation-less Writes
- **❌:** `auth()->user()->update($request->all());`
- **✅:** Use FormRequest validation: `auth()->user()->update($request->validated());`
