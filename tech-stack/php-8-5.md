# PHP 8.5 Architecture Standards
> [!SPECULATIVE] PHP 8.5 is not yet released. Rules are based on RFC proposals and preview documentation. Verify against official release notes before applying.

## 1. PATTERN MATCHING & ENUMS
- **Advanced Matching:** Maximize the use of advanced pattern matching with Enums for state machines and complex conditional logic.
- **Enum Methods:** Use backed Enums with methods for encapsulating domain logic (e.g., `Status::Active->label()`).

## 2. JIT OPTIMIZATION
- **Code Style:** Write code optimized for the improved Just-In-Time compiler. Avoid dynamic properties completely.
- **Hot Paths:** Ensure frequently executed code paths use typed properties and strict types for maximum JIT benefit.

## 3. TYPING
- **Absolute Strictness:** `declare(strict_types=1);` is non-negotiable in every file.
- **Native Types:** Use Intersection and Union types natively without PHPDoc fallbacks. Leverage `true`, `false`, `null` as standalone types.
- **Pipe Operator:** If the pipe operator (`|>`) lands, prefer it for functional data transformations over nested function calls.