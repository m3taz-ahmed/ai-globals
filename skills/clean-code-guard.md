---
name: clean-code-guard
description: Enforce clean code, SOLID, and DRY principles.
---
[SKILL] clean-code-guard
[OBJ] Code review enforcing SOLID, DRY, KISS, and YAGNI.
[RULES]
1. [PROHIBIT] AI Guards: No empty catch blocks (swallowing errors). No guarding against guaranteed TS/PHP types. No mock `{"status":"ok"}` returns.
2. [REQ] AI Guards: Verify imports exist. Strip dead code.
3. [REQ] Clean Code: Descriptive names (no `data`/`utils`). Functions <= 20 lines, 1 abstraction level. Max 4 args (use DTO for 5+). Strict CQS (Command Query Separation).
4. [REQ] SOLID: Single Responsibility, Open/Closed, Liskov Substitution.
5. [REQ] Naming is the contract: names answer "what does it DO" for functions (verbs), "what IS it" for values (nouns), "what does it guarantee" for types. If the name needs a comment to be accurate, rename it.
6. [REQ] Complexity hygiene: cyclomatic <10 per function, nesting ≤3 (guard clauses early-return), no boolean-parameter mode flags (split the function), no flag arguments that change control flow invisibly.
7. [REQ] Boundary clarity: validate at the edges (parse, don't trust), keep the core pure of I/O where practical; error handling is a boundary concern — translate exceptions at layer seams, don't leak raw types upward.
8. [REQ] Comments for why, code for what: comment intent/invariants/non-obvious trade-offs; delete comments that narrate the code. A misleading comment is worse than none — prune ruthlessly.
9. [REQ] Dependencies inward: high-level modules don't import low-level details; inject collaborators through constructors/parameters; new abstractions must pay rent (testability or replaceability) or be deleted.
10. [PROHIBIT] YAGNI/DRY: No speculative features/toggles. Delete duplicated *knowledge*, not just text. Wrong abstraction > duplication.
11. [REQ] Checklist: Verify small functions, no mock data, verified imports, and no behavioral changes during refactor (split bug fixes).
