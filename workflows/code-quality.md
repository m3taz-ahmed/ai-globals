# Code Quality & Clean Architecture
> [!NOTE]
> Trigger: refactoring and feature implementation tasks.

## Naming Conventions & Structure `[CODE-01]`
- **Services:** `[Feature]Service` (e.g. `InvoiceService`) for business orchestration.
- **Actions:** `[Verb][Entity]Action` (e.g. `CreateInvoiceAction`) for single-purpose domain tasks.
- **DTOs:** `[Entity]Data` (e.g. `InvoiceData`) for strictly-typed data transfer.

## SOLID & Design Principles `[CODE-05]`
- **Single Responsibility:** One reason to change.
- **Open/Closed:** Open for extension, closed for modification.
- **Interface Segregation:** Client-specific interfaces.
- **DRY:** Extract duplicated logic in 3+ places to shared utility helper.

## Method & Class Limits `[CODE-03]`
- **Limits:** Methods < 30 lines (hard limit), classes < 300 lines. Max 3 arguments per method (use DTOs for more).

## Strict Typing & Safety `[CODE-02]`
- **Strict Types:** parameters and return types mandatory. ⛔ `mixed` or `any`.
- **Enums `[CODE-04]`:** Use Enums or constants for statuses. ⛔ magic strings.
- **Exceptions:** Extend domain-specific `AppException` rather than throwing raw `\Exception`.

## AI-Specific Guardrails (Clean Code Guard)
- **Names Reveal Intent:** Never use `data`, `data2`, `result`, `item`, `helper`. A name must answer *why it exists and what it does*.
- **No Boolean Flags:** Avoid boolean flag arguments; split into two functions instead. Max 4 arguments total.
- **Deduplicate Knowledge, Not Text:** Two functions that look alike but encode different business rules are NOT a DRY violation.
- **Re-inline Bad Abstractions:** If an abstraction has accumulated branches for special cases, re-inline it back into callers before re-abstracting.
- **Strip Dead Code Before Delivery:** Run static analysis and delete unused imports, dead branches, and "just in case" exports. Do not leave code for "someday".
- **Refactoring Discipline:** Preserve observable behavior strictly when refactoring. Never bundle bug fixes with refactoring.
