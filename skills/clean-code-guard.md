---
name: clean-code-guard
description: Review generated or changed production code before it ships, using Clean Code, SOLID, DRY, KISS, YAGNI, and LLM-specific failure-mode checks.
---
# clean-code-guard

**Mode**: Run before presenting/committing code.

## 🔴 AI-Specific Guardrails (Highest Priority)
- **Swallowing Errors**: Never use empty catch-all blocks. Return explicitly or fail.
- **Impossible Cases**: Trust contracts; don't guard against types guaranteed by TS/PHP.
- **Mocking Reality**: Do not return hardcoded `{"status": "ok"}` instead of real logic.
- **Verify Imports**: Check packages/libraries exist before importing them.
- **Strip Dead Code**: Remove unused imports, variables, and branches.

## 📐 Clean Code Core
1. **Names**: Answer *why* and *what*. No `data`, `info`, `utils`, `helper`.
2. **Size**: Functions <= 20 lines, ONE level of abstraction.
3. **Args**: Max 4 arguments. Use a DTO/Struct at 5.
4. **CQS**: Functions return values OR have side-effects, never both.

## 🧱 SOLID & YAGNI
1. **SRP**: One actor/responsibility per module.
2. **OCP**: Extend via new code, not endless `if/else` tags.
3. **LSP**: Subclasses must not refuse parent contracts or throw `NotImplemented`.
4. **DRY/KISS**: Delete duplicated *knowledge*, not text. The wrong abstraction is worse than duplication.
5. **YAGNI**: No speculative features, toggles, or optional parameters without current usage.

**Checklist before delivery**:
- Are functions small? <= 4 args?
- Is there any hardcoded mock data in production code?
- Did you verify imports?
- Did you change observable behavior during a refactor? (If yes, it's a bug fix, split it).
