# Laravel 12.x Architectural Standards

## 1. NATIVE TYPE ENFORCEMENT
- **Dependency Injection:** Use native type-hints for all constructor and method injection. Avoid `resolve()` or `app()` where possible.
- **ReturnType:** Every Controller method, Service method, and Job `handle()` MUST have a native return type.

## 2. MODERN ROUTING & VALIDATION
- **FormRequests:** Every POST/PUT/PATCH request MUST use a dedicated `FormRequest` class.
- **Rule Objects:** Prefer custom `Rule` objects over complex regex or closure-based validation.

## 3. ASYNC & PERFORMANCE
- **Queue by Default:** Any operation exceeding 100ms (emails, external APIs) MUST be queued.
- **Batching:** Use `Bus::batch()` for complex, multi-stage background processes.
- **Caching:** Use `Cache::remember()` for expensive calculations or third-party API results.

## 4. UI & ASSETS
- **Vite:** Follow `vite-7.md` for asset bundling.
- **Livewire:** Follow `livewire-3.md` for reactive components.