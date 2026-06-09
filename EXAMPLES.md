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


---

## 8. Prompt Master Examples

### Template Example 1
**Example:**
```
Role: You are a senior technical writer.
Task: Write a one-paragraph description of what a REST API is.
Format: Plain prose, 3 sentences maximum, no jargon, suitable for a non-technical audience.
```

### Template Example 2
**Example:**
```
Context: I am a founder pitching a B2B SaaS tool that automates expense reporting for mid-size companies.
Objective: Write a cold email that gets a reply from a CFO.
Style: Direct and conversational, not salesy.
Tone: Confident but not pushy.
Audience: CFO at a 200-person company, busy, skeptical of vendor emails.
Response: 5 sentences max. Subject line included. No bullet points.
```

### Template Example 3
**Example:**
```
Role: You are a product manager with 10 years of experience in mobile apps.
Instructions: Write a product requirements document for a habit tracking feature.
Steps:
  1. Define the problem statement in one paragraph
  2. List user stories in the format "As a [user], I want [goal] so that [reason]"
  3. Define acceptance criteria for each story
  4. List out-of-scope items explicitly
End Goal: A PRD that an engineering team can begin sprint planning from immediately.
Narrowing: No technical implementation details. No wireframes. Under 600 words total.
```

### Template Example 4
**Example:**
```
Capacity: Expert copywriter specializing in SaaS product launches.
Role: Brand voice for a productivity tool aimed at developers.
Insight: Developers hate marketing speak and respond to honesty and specificity.
Statement: Write the hero headline and sub-headline for the landing page.
Personality: Sharp, dry, confident — no adjectives, no exclamation marks.
Experiment: Give 3 variants ranging from minimal to bold.
```

### Template Example 5
**Example:**
```
Reference image: [attached portrait photo]
What to keep exactly the same: face, hair, clothing, background, lighting
What to change: head angle — rotate from facing left to facing straight forward
How much to change: subtle, preserve all facial features exactly
Style consistency: maintain photorealistic style, same lighting direction
Negative prompt: no new elements, no style changes, no background changes
```
