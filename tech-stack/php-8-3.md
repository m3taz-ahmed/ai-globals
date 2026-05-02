# PHP 8.3 Architecture Standards

## 1. TYPE SYSTEM ENHANCEMENTS
- **Typed Class Constants:** Enforce Typed Class Constants (`public const string STATUS = 'active';`). No untyped constants in new code.
- **Dynamic Class Constants:** Use `ClassName::{$name}` for dynamic constant access. Avoid `constant()` where possible.
- **Readonly Amendments:** Readonly properties can now be reinitialized during cloning via `__clone()`. Use this for immutable value objects that need controlled copies.

## 2. JSON HANDLING
- **Validation:** Always use `json_validate()` instead of `json_decode()` for checking JSON validity. It's faster and doesn't allocate memory for the decoded structure.
- **Error Handling:** When decoding, use `json_decode($str, true, 512, JSON_THROW_ON_ERROR)` to get exceptions instead of silent `null` returns.

## 3. OVERRIDE SAFETY
- **`#[\Override]` Attribute:** MANDATORY for all overridden parent methods. This ensures compile-time safety â€” if the parent method signature changes or is removed, you get an immediate error instead of a silent bug.

## 4. RANDOMIZER & CRYPTOGRAPHY
- **Randomizer Class:** Use `Random\Randomizer` for all random value generation. Supports `getBytesFromString()`, `getFloat()`, and `nextFloat()`.
- **Entropy Source:** Use `Random\Engine\Secure` (default) for cryptographic operations. Use `Mt19937` only for reproducible testing.

## 5. DEPRECATION AWARENESS
- **Dynamic Properties:** Dynamic properties are deprecated. Use `#[AllowDynamicProperties]` only as a temporary migration aid, never in new code.
- **Deprecation Notices:** Treat all deprecation notices as errors in CI. Fix before they become fatal in PHP 9.x.