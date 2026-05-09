# PHP 8.3 Architecture Standards

## 1. TYPE SYSTEM ENHANCEMENTS
- **Typed Class Constants:** Enforce Typed Class Constants (`public const string STATUS = 'active';`). No untyped constants in new code.
- **Dynamic Class Constants:** Use `ClassName::{$name}` for dynamic constant access. Avoid `constant()` where possible.
- **Readonly Amendments:** Readonly properties can now be reinitialized during cloning via `__clone()`. Use this for immutable value objects that need controlled copies.
- **Anonymous Readonly Classes:** Support for `readonly` anonymous classes. Use for transient, immutable data structures within Actions or Services.

## 2. JSON HANDLING
- **Validation:** Use `json_validate()` ONLY for pass-through validation where the payload is NOT consumed locally (e.g., proxies, request-level sanity checks).
- **Parsing:** If the data is consumed locally, skip `json_validate()` and use `json_decode($str, true, 512, JSON_THROW_ON_ERROR)` to avoid double-parsing overhead.

## 3. BILINGUAL STRING INTEGRITY
- **Multibyte Padding:** Use `mb_str_pad()` instead of `str_pad()` for all UI-bound string manipulation. This is MANDATORY to maintain visual alignment in Arabic/English bilingual interfaces (ref: `bilingual-mastery.md`).

## 4. OVERRIDE SAFETY
- **`#[\Override]` Attribute:** MANDATORY for all overridden parent methods. 
- **Enforcement:** Static analysis (PHPStan/Psalm) MUST be configured to enforce this attribute at the CI level to prevent silent inheritance breakages.

## 5. RANDOMIZER & CRYPTOGRAPHY
- **Randomizer Class:** Use `Random\Randomizer` for all random value generation. 
- **Mocking:** Interface-based injection or mocking is preferred for tests requiring reproducible sequences.

## 6. DEPRECATION AWARENESS
- **Dynamic Properties:** Dynamic properties are deprecated. Use `#[AllowDynamicProperties]` only as a temporary migration aid, never in new code.
- **Deprecation Notices:** Treat all deprecation notices as errors in CI. Fix before they become fatal in PHP 9.x.
