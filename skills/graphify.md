---
name: graphify-windows
description: "Turn folder of files into queryable knowledge graph. Use for codebase/architecture questions."
trigger: /graphify
---
# /graphify

**Mode**: Extracts knowledge graphs from codebases (`graphify-out/graph.json`).

## 🔴 Workflow
1. **Check existence**: If `graphify-out/graph.json` exists AND user asks a question, skip rebuild and run `graphify query "<question>"`.
2. **Detect**: `graphify detect .` to count files/tokens.
3. **Extract**: `graphify extract` (AST + LLM semantic). Parallel processing via subagents for text/docs.
4. **Analyze & Cluster**: Generates communities, cohesion scores, and `GRAPH_REPORT.md`.
5. **Explore**: Answer user questions by querying the graph structure.

*Always rely on the `graph.json` to navigate deep codebase queries rather than reading raw files individually.*
