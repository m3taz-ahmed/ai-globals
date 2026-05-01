# Code Quality & Clean Code Standards

## 1. NAMING CONVENTIONS
- **PHP (PSR-12):** Classes in `PascalCase`, methods/variables in `camelCase`, constants in `UPPER_SNAKE_CASE`.
- **JavaScript/TypeScript:** Variables/functions in `camelCase`, classes in `PascalCase`, constants in `UPPER_SNAKE_CASE`, files in `kebab-case`.
- **Database:** Tables in `snake_case` (plural: `bookings`), columns in `snake_case`, pivot tables alphabetical (`booking_service`).
- **Descriptive Names:** Names must reveal intent. `$bookingTotalAmount` not `$bta`. `calculateInvoiceTotal()` not `calc()`.

## 2. FUNCTION & METHOD DESIGN
- **Single Responsibility:** Each function/method does ONE thing. If you can't describe it without "and", split it.
- **Length Limit:** Prefer functions under 30 lines. If a function exceeds 50 lines, it MUST be refactored.
- **Cyclomatic Complexity:** Maximum complexity of 10 per function. Use early returns and guard clauses to reduce nesting.
- **Parameter Count:** Maximum 4 parameters. Beyond that, use a DTO/Value Object/Config object.

## 3. CODE ORGANIZATION
- **File Length:** If a class exceeds 300 lines, evaluate splitting into collaborators or extracting concerns into traits/mixins.
- **Import Order:** Group imports: 1) Framework/vendor, 2) Application, 3) Relative. Alphabetize within groups.
- **Dead Code:** Zero tolerance for commented-out code, unused imports, unreachable branches, or orphaned methods. Delete, don't comment.

## 4. COMMENTS & DOCUMENTATION
- **Comment the "Why":** Explain design decisions, trade-offs, and non-obvious business rules. Never comment the "what" — the code itself should be clear.
- **PHPDoc:** Required for all public methods with `@param`, `@return`, and `@throws` tags. Not needed if native types fully describe the signature.
- **TODO/FIXME:** Allowed only with a linked ticket/issue number: `// TODO(FS-42): Refactor when Daftra API v3 lands`.

## 5. PRINCIPLES ENFORCEMENT
- **SOLID:** Every class and module must adhere to Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion.
- **DRY:** If code is duplicated 3+ times, extract it into a shared service, helper, or base class.
- **KISS:** Choose the simplest solution that meets requirements. Over-engineering is a code smell.
- **YAGNI:** Do not build features or abstractions "just in case". Build for current requirements, design for extension.
