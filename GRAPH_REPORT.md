# aiZee Knowledge Graph Report

*Generated: 2026-08-25 from `graphify-out/graph.json` (live graphify output)*

## Summary

- **Nodes:** 13124
- **Edges (links):** 27847
- **Communities:** 871
- **Source:** `graphify update .` (graphifyy 0.9.16)
- **Graph file:** `graphify-out/graph.json` (14.3 MB)

## What the graph contains

- Every Python module, skill, workflow, tech-stack doc, and markdown rule indexed as a node.
- Edges represent imports, references, skill→persona links, and workflow triggers derived from AST + markdown parsing.
- Communities are Louvain clusters; high community count (871) reflects the highly modular 85-runtime-module architecture.

## How to query (do NOT use raw grep)

```bash
# Build/update
graphify update .

# MCP tools (preferred in AI sessions)
aizee mcp graphify query --args '{"query":"policy evaluation"}'
aizee mcp graphify explain --args '{"path":"runtime/policy.py"}'
```

## Health

- Graph is present and fresh (verify with `python -c "import json;print(len(json.load(open('graphify-out/graph.json'))['nodes']))"`).
- Dashboard serves summary at `/api/graph/stats` (capped at 2 MB).
- If `graph.json` is missing, `aizee doctor` will flag `graphify-out/graph.json`.

## Previous report

The previous GRAPH_REPORT.md was a stale Global AI Coach placeholder (July 2026, all zeros). This report replaces it with the live graphify stats.
