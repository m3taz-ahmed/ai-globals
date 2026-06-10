# AI OS Rules & Context Architecture

> [!IMPORTANT]
> **DO NOT READ THE `rules/`, `tech-stack/`, or `workflows/` DIRECTORIES DIRECTLY!** 
> This OS uses a compiled Shadow DOM pattern for extreme context token savings.

## The `min/` Shadow DOM
All human-readable rules in this repository are compiled into highly dense AI-shorthand (`.min` files) located in the `D:\server\.ai\min\` directory. 

Whenever you update any `.md` file in the source directories (`rules`, `tech-stack`, `workflows`, `skills`), you **must** run the compilation script to update the AI's context:
```powershell
D:\server\.ai\scripts\build-context.ps1
```

## Global AI OS Instructions (User Configuration)
To properly initialize this system in your IDE (Cursor, Windsurf, etc.), place the following highly compressed configuration into your IDE's Global Rules or system prompt:

```markdown
### 🌍 GLOBAL AI OS
- **Root:** `D:\server\.ai\`
- **Init:** Read `global-roles.md` & `./min/rules/`. NEVER read source `rules/` or `tech-stack/`.
- **Context:** Read project `spec.md`. Only load corresponding `.min` files from `./min/tech-stack/`.
- **Graphify:** If `graphify-out/graph.json` exists, NEVER raw grep. MUST use `query_graph` (MCP)/`graphify query` (CLI). Use `shortest_path`/`get_node` for relations/concepts. Navigate `wiki/index.md` if present. Use `GRAPH_REPORT.md` ONLY as last resort. Run `graphify update .` after edits.
```

## Directory Structure
- `rules/` : Core AI identities, anti-patterns, and baseline constraints.
- `tech-stack/` : Framework-specific rules (e.g., Laravel, React, Database). Loaded dynamically.
- `workflows/` : Process constraints (e.g., CI/CD, Git, Testing).
- `skills/` : Prompting behaviors and roleplay capabilities.
- `min/` : **The only directory the AI should read.** Contains the compiled output of all the above.
