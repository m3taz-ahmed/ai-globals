# Code Quality & Clean Architecture

## 1. NAMING CONVENTIONS
- **Services:** `[Feature]Service` (e.g., `InvoiceService`). Focused on business logic.
- **Actions:** `[Verb][Entity]Action` (e.g., `CreateInvoiceAction`). Single-purpose classes.
- **DTOs:** `[Entity]Data` (e.g., `InvoiceData`). Typed objects for data transfer.
- **Models:** Singular PascalCase (e.g., `User`).

## 2. SOLID PRINCIPLES
- **Single Responsibility:** A class should have one, and only one, reason to change.
- **Open/Closed:** Classes should be open for extension but closed for modification.
- **Interface Segregation:** Prefer many small, client-specific interfaces over one large, general-purpose interface.

## 3. FUNCTION DESIGN
- **Length:** Methods should not exceed 30 lines.
- **Arguments:** Limit to 3 arguments. Use DTOs for more complex signatures.
- **Strict Typing:** All methods MUST have parameter and return types defined.

## 4. PHPDOC & DOCUMENTATION
- **Clarity:** Use PHPDoc to explain *why*, not *what* (the code should explain the *what*).
- **API Documentation:** Ensure all public API endpoints are documented with parameters and response examples.
