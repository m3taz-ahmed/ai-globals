[WORKFLOW] code-quality
[OBJ] Code Quality & Clean Architecture.
[RULES]
1. [REQ] Naming `[CODE-01]`: `[Feature]Service`, `[Verb]Action`, `[Entity]Data` (DTOs). No `data`, `utils`, `helper`.
2. [REQ] SOLID `[CODE-05]`: Single Responsibility, Open/Closed, Interface Segregation. DRY (Extract 3+ duplicates).
3. [REQ] Limits `[CODE-03]`: Methods < 30 lines. Classes < 300 lines. Max 3 arguments per method.
4. [REQ] Safety `[CODE-02]`: Strict Types (`strict_types=1`). No `mixed` or boolean flags. Use Enums `[CODE-04]`. Base `AppException`.
5. [REQ] AI Guards: Deduplicate knowledge (not text). Strip dead code before delivery. Preserve behavior during refactor.
