[TECH] laravel-12
[OBJ] Laravel 12.x Architectural Standards.
[RULES]
1. [REQ] Types: Native type-hints (NO `resolve()`). Native return types for Controllers/Services/Jobs.
2. [REQ] Validation: Dedicated `FormRequest` for POST/PUT. Use custom `Rule` objects over complex regex.
3. [REQ] Async: Queue operations >100ms. Use `Bus::batch()`. Cache expensive results.
