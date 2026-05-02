# Laravel 11 Architecture Standards

## 1. STRUCTURE & BOOTSTRAPPING
- Laravel 11 features a streamlined directory structure. `App\Http\Kernel` and `App\Console\Kernel` are gone. Configuration is heavily centralized in `bootstrap/app.php`.
- Do not create legacy files if they are not needed in Laravel 11.

## 2. BUSINESS LOGIC (THIN CONTROLLERS)
- **Rule:** Controllers must only handle HTTP parsing, calling Services/Actions, and returning Responses.
- **Service Pattern:** Place heavy business logic in `App\Services\`.
- **Validation:** Always use `FormRequest` classes. Never validate inline within the controller.

## 3. ELOQUENT & DATABASE PERFORMANCE
- **Strict Mode:** Assume `Model::shouldBeStrict()` is enabled.
- **N+1 Prevention:** ALWAYS use Eager Loading (`with()`) when iterating over relationships.
- **Chunking:** Use `chunk()` or `lazy()` for processing large datasets to prevent RAM exhaustion.

## 4. API DESIGN
- Return standardized API Resource classes (`JsonResource`).
- Keep responses consistent (status code, message, data payload).