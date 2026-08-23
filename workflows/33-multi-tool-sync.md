---
name: 33-multi-tool-sync
trigger: multi-tool sync, rules materialize, tool sync, cross-tool, مزامنة الأدوات
engine: runtime/rules_materializer.py
---

# Workflow 33 — Multi-Tool Rules Sync

[OBJ] Materialize aiZee's single source of truth into every AI coding tool's native format. Eliminate cross-tool rule drift.

## Problem

Claude Code reads `CLAUDE.md`. Cursor splits rules by glob in `.cursor/rules/`. Copilot truncates. Cline concatenates `.clinerules/`. Windsurf reads `.windsurfrules`. Aider reads `CONVENTIONS.md` via `--read`. Two of three silently drop a rule the third enforces. Same English sentence behaves differently in each tool.

## Phases

### Phase 1 — Collect source rules
1. Read `global-roles.md`, `global-workflow.md`, `AGENTS.md`.
2. Read `rules/*.md` (core-behavioral-compact, vocabulary, anti-patterns).
3. Read project-specific rules from `.ai/rules/` if present.
4. Tag each rule with scope: ORG / PROJECT / NAMESPACE / REPO / TEAM / USER.

### Phase 2 — Resolve by precedence
1. Load rules into `RulesMaterializer.resolve()`.
2. Higher scope overrides lower scope (same key).
3. Deduplicate by key.
4. Output: ordered list of `RuleEntry`.

### Phase 3 — Materialize to all targets
1. `RulesMaterializer.materialize(resolved, targets=None)` → all 7 tools.
2. Files written:
   - `CLAUDE.md` (Claude Code)
   - `.cursor/rules/aizee.mdc` (Cursor, with frontmatter)
   - `.clinerules/aizee.md` (Cline)
   - `.windsurfrules` (Windsurf)
   - `.github/copilot-instructions.md` (GitHub Copilot)
   - `CONVENTIONS.md` (Aider)
   - `.devin/rules/aizee.md` (Devin)
3. Each file is idempotent — re-running overwrites stale content.

### Phase 4 — Drift detection
1. `RulesMaterializer.detect_drift(rule_sets)` → per-target missing keys.
2. If any target has missing keys → alert + re-materialize.
3. Commit materialized files to version control (single source → many files).

### Phase 5 — Verify
1. Confirm each file exists + contains all resolved rule keys.
2. Run `aizee check materialize --args '{"targets":["claude","cursor","cline","windsurf","copilot","aider","devin"]}'`.
3. Log to audit trail.

## Commands (PowerShell)

```powershell
# Materialize to all tools
python -c "from runtime.rules_materializer import RulesMaterializer, RuleEntry, ScopeLevel; m = RulesMaterializer(Path('.')); m.materialize_all({ScopeLevel.REPO: [...]})"

# Detect drift
python -c "from runtime.rules_materializer import RulesMaterializer, ScopeLevel; m = RulesMaterializer(Path('.')); print(m.detect_drift({ScopeLevel.REPO: [...]}))"
```

## Quality Gate

- All 7 target files written.
- Zero drift (all targets have all rule keys).
- `ruff check runtime/rules_materializer.py` PASS.
- `pytest tests/test_rules_materializer.py -q` PASS.
