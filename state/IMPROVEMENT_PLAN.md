[FILE] IMPROVEMENT_PLAN
[OBJ] Strategic enhancement and maintenance tracking for v4.20.0+.
[RULES]
1. [REQ] Issue 1: Version consistency. (Fixed v4.20.0: 4.20.0 unified across README/CHANGELOG/scripts).
2. [REQ] Issue 2: min/ shadow DOM debt. (Fixed v4.20.0: build-context.ps1 deleted, rules/README.md corrected).
3. [REQ] Issue 3: vocabulary location. (Fixed v4.20.0: skills/vocabulary.md -> rules/vocabulary.md).
4. [REQ] Issue 4: Validator H1 false-positives. (Fixed v4.20.0: title-check accepts [FILE]/[TECH]/[WORKFLOW]/[SKILL]).
5. [REQ] Issue 5: Validator scope. (Fixed v4.20.0: skills/ added to scan dirs, ps1 is thin wrapper).
6. [REQ] Issue 6: CI missing. (Fixed v4.20.0: .github/workflows/validate.yml added).
7. [REQ] Issue 7: Routing manifest missing. (Fixed v4.20.0: manifest.json added).
8. [REQ] Maintenance: Run monthly audit (dependencies, code smells, N+1, dead code).
9. [REQ] Evolution: Continuous rule alignment with framework updates. Document decisions in state/MEMORY.md.
