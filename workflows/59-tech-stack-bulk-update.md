# Workflow 59 — Tech-Stack Bulk Update

[TRIGGER] tech stack update, tech stack bulk, version update, stack refresh, تحديث التقنيات
[PERSONA] ARCH, DEV, DEVX, DOC
[TECH] mcp-2

## Objective

Perform bulk update of tech-stack reference files when new framework/language versions are released. Ensure all references are current, accurate, and follow the compressed telegraphic format.

## Steps

1. **Audit current state.** List all files in `tech-stack/`. For each file, note the version it targets. Compare against current stable versions from official sources (not search results alone).

2. **Verify versions via Context7.** For each framework/library, use Context7 MCP to fetch current documentation and verify the latest stable version. `resolve-library-id` then `query-docs`. Never trust web search alone for version claims.

3. **Identify stale references.** Flag files where the targeted version is more than one major version behind current stable. Flag files where the targeted version is EOL or in maintenance-only.

4. **Identify missing references.** Flag major versions that have been released but have no corresponding tech-stack file. Prioritize by: criticality (language/runtime > framework > library), adoption rate, breaking changes.

5. **Create new files.** For each missing reference, create `tech-stack/<name>-<version>.md` following the compressed telegraphic format: `[TECH]`, `[OBJ]`, `[RULES]`, `[COMPAT]`, `[REFS]`. 15-25 rules per file. Use `[REQ]`, `[PROHIBIT]`, `[CMD]` prefixes.

6. **Update existing files.** For stale references, either:
   - **Update in-place** if the version is still supported (add new features, breaking changes).
   - **Mark as DEPRECATED** if the version is EOL (add `[DEPRECATED]` header pointing to the new file).
   - **Create new file** if a new major version exists (keep old file for backward reference).

7. **Distinguish stable from preview.** Clearly mark:
   - **Stable** — production-ready, no prefix needed.
   - **Preview/Beta** — mark with `[PREVIEW]` or `[BETA]` in `[OBJ]`.
   - **Speculative** — mark with `[PLANNED]` and note expected release date.
   - Never present preview features as stable.

8. **EOL tracking.** For each file, note EOL date in `[COMPAT]` section. Flag files where EOL is within 6 months — plan migration.

9. **Breaking changes.** For each new version, document breaking changes in `[COMPAT]` section. Include migration notes where applicable.

10. **Cross-reference updates.** When a tech-stack file references another (e.g., `nextjs-16.md` references `react-19.md`), verify the cross-reference is accurate and the referenced file exists.

11. **Update useful-repos.md.** Add new tools, frameworks, and repositories that have emerged. Remove dead/archived projects (note acquisition/archival status).

12. **Update personas.yaml.** If new tech-stack files introduce new triggers or keywords, add them to the relevant persona in `runtime/personas.yaml`.

13. **Update manifest.json.** If new tech-stack files introduce new routing keywords, add them to `manifest.json` routes.

14. **Update skills.** If new tech-stack files introduce new patterns that skills should reference, update the relevant `skills/*/SKILL.md` `tech_stack` field.

15. **Quality gate.** Run `ruff check .`, `mypy`, `aizee test --full`, `python eval/harness.py`. Run `aizee memory ingest` to refresh indexes.

16. **Memory sync.** Update `Memory.md` with tech-stack bulk update milestone. Update `CHANGELOG.md` `[Unreleased]` section. Update counts in `spec.md` if total file count changed.

## References

- `tech-stack/mcp-2.md` — MCP 2026-07-28 (reference for format)
- `workflows/17-memory-sync.md` — Memory sync workflow
- Context7 MCP — for version verification
