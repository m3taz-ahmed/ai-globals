# AI Global OS — Repositories to Study

## Meta-prompt for the reviewing agent

You are an architecture research agent. Your task is to study each repository listed below, extract the most valuable ideas, patterns, and reusable code for AI Global OS, and produce a decision report.

### Workflow
1. Create a fresh `temp/repos-study/` directory under the AI Global OS root.
2. For every repository in the list below:
   - `git clone --depth 1 https://github.com/<repo>.git temp/repos-study/<safe-name>`
   - Read the README, top-level docs, and key source files (look at `src/`, `docs/`, `examples/`).
   - Identify:
     - Core architecture pattern (orchestrator, memory, policy, guardrails, etc.).
     - 3–5 concrete ideas or code patterns that AI Global OS can reuse.
     - License and maintenance status (last commit, stars, activity).
     - Integration effort (small / medium / large).
     - Risk or lock-in (needs external service, heavy dependencies, opinionated stack).
3. Write a full report to `.ai/repos-report.md` with the following table per repo:
   - **Repo** — full name.
   - **Category** — from the list below.
   - **Summary** — one-paragraph elevator pitch.
   - **Top takeaways** — bullet list of ideas/patterns to adopt.
   - **Adopt?** — `YES` / `HOLD` / `NO`.
   - **Why?** — how it improves AI Global OS or why it is not a fit.
   - **Effort** — small / medium / large.
   - **Target component** — `runtime/`, `memory/`, `aios_mcp/`, `dashboard/`, `rules/`, `CI/CD`, etc.
4. At the end, produce a ranked priority list: which repos to integrate first, which to watch, and which to skip.
5. Clean up `temp/repos-study/` when finished unless the user asks to keep it.

### Constraints
- Do not run tests of cloned repos unless explicitly approved.
- Do not install dependencies of cloned repos unless approved.
- Never commit secrets or personal tokens.
- Keep the report factual; mark speculative claims with `?`.
- Use code snippets sparingly; prefer describing the pattern and pointing to file paths.

---

## Repository list

### Agent operating systems / governance
- RightNow-AI/openfang
- shackleai/orchestrator
- Justin0504/Sovereign-OS
- microsoft/agent-governance-toolkit
- preloop/preloop
- mnemopay/praetor
- nanny-run/nanny
- ViktorWelbers/paddock

### MCP orchestration
- lastmile-ai/mcp-agent
- mrorigo/mcp-orchestrator
- musaceylan/OrchestrAI
- chrisnewell91/Meta-MCP-Server
- dufangshi/orchestration-mcp

### Policy / rule engines
- open-policy-agent/opa
- MAIF/arta
- poyao0705/guardian-angel
- JonSil89/gatehouse-policy-engine
- SemClone/ospac

### Coding guardrails
- fjb040911/ai-rules
- yunbow/ai-dev-os
- nizos/probity
- stawils/coding-guardrails
- xianzuyang9-blip/agent-guardrails

### Memory / RAG / knowledge graph
- neo4j-labs/agent-memory
- PlateerLab/synaptic-memory
- mtrnix/metronix-memory
- XMUDeepLIT/MemGraphRAG
- MemMachine/MemMachine

### Dashboard / UI design
- facebook/astryx
- VoltAgent/awesome-design-md

### Observability / SRE
- open-telemetry/opentelemetry-python
- prometheus/client_python
