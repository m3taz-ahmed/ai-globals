[TECH] laravel-11
[OBJ] Laravel 11 Architecture Standards.
[RULES]
1. [REQ] Structure: Config centralized in `bootstrap/app.php`. No HTTP/Console Kernels.
2. [REQ] Logic: Thin controllers. Logic in `App\Services\`. Validate via `FormRequest`.
3. [REQ] Eloquent: Eager load `with()`. Use `chunk()`/`lazy()`. Strict mode enabled.
4. [REQ] API: Standardized `JsonResource`.
