---
name: docs-guard
description: Review documentation (README, API, docstrings, changelogs) for accuracy, code-drift, and filler.
---
# docs-guard

**Mode**: Run after docs generation/edits. Docs are claims; verify them.

## 🔴 Core Rules
1. **Verify everything**: Every referenced function, endpoint, flag, and file MUST exist in the actual source. Read it, don't hallucinate from memory.
2. **Working Samples**: Code samples must have correct signatures and resolve.
3. **Code = Truth**: Document actual behavior. If code and intended behavior disagree, the code is right. Flag it.
4. **No unverifiable claims**: "Fast", "Production-ready" require real benchmarks in the repo.
5. **Code change = Docs change**: If you change a function name, update all doc surfaces mentioning it.
6. **No Filler**: Delete docstrings that just paraphrase the signature (e.g., "Gets user by ID" for `get_user_by_id`).
7. **Failure paths**: Document error states, not just the happy path.

**Checklist before delivery**:
- Did you verify every symbol/endpoint against the actual source?
- Do code samples work?
- Is there marketing filler? (Delete it).
