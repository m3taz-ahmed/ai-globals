[SKILL] graphify-windows
[OBJ] Extract and query codebase knowledge graph.
[RULES]
1. [REQ] Trigger: `/graphify` or codebase/architecture questions.
2. [REQ] Fast Path: If `graphify-out/graph.json` exists, SKIP rebuild. Run `graphify query "<question>"`.
3. [REQ] Extraction: `graphify detect .` -> `graphify extract` -> Generates `GRAPH_REPORT.md` and communities.
4. [REQ] Navigation: ALWAYS rely on `graph.json` for deep queries rather than raw file reads.
