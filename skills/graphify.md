---
name: graphify
description: "Graphify knowledge graph integration for Windows."
---
[SKILL] graphify-windows
[OBJ] Extract and query codebase knowledge graph.
[RULES]
1. [REQ] Trigger: `/graphify` or codebase/architecture questions.
2. [REQ] Fast Path: If `graphify-out/graph.json` exists, SKIP rebuild. Run `graphify query "<question>"`.
3. [REQ] Extraction: `graphify detect .` -> `graphify extract` -> Generates `GRAPH_REPORT.md` and communities.
4. [REQ] Navigation: ALWAYS rely on `graph.json` for deep queries rather than raw file reads.
5. [REQ] Query toolbox: `graphify query "<question>"` for architecture/where-does-X-live, `graphify path "<A>" "<B>"` for dependency chains between modules, `graphify explain "<concept>"` for related-node context. Query BEFORE grepping; grep only to verify the graph's answer in real code.
6. [REQ] Freshness: run `graphify update .` after structural code edits (new modules, moved files, signature changes) — stale graphs mislead worse than no graph; timestamps in `graph.json` are the freshness signal.
7. [REQ] Navigation order: `graphify-out/wiki/index.md` (if present) for wiki-style overview → `graphify query/path/explain` for specifics → `GRAPH_REPORT.md` as the fallback dump when queries miss.
8. [REQ] Cross-check critical answers: the graph maps structure, not truth — confirm findings by reading the actual file before making changes or reporting conclusions to the user.
9. [PROHIBIT] Rebuilding the graph when `graph.json` exists (wasted minutes), raw-grepping a codebase the graph already indexes, or citing graph findings as fact without a code-level spot check.
