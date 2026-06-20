[SKILL] clean-code-guard
[OBJ] Code review enforcing SOLID, DRY, KISS, and YAGNI.
[RULES]
1. [PROHIBIT] AI Guards: No empty catch blocks (swallowing errors). No guarding against guaranteed TS/PHP types. No mock `{"status":"ok"}` returns.
2. [REQ] AI Guards: Verify imports exist. Strip dead code.
3. [REQ] Clean Code: Descriptive names (no `data`/`utils`). Functions <= 20 lines, 1 abstraction level. Max 4 args (use DTO for 5+). Strict CQS (Command Query Separation).
4. [REQ] SOLID: Single Responsibility, Open/Closed, Liskov Substitution.
5. [PROHIBIT] YAGNI/DRY: No speculative features/toggles. Delete duplicated *knowledge*, not just text. Wrong abstraction > duplication.
6. [REQ] Checklist: Verify small functions, no mock data, verified imports, and no behavioral changes during refactor (split bug fixes).
