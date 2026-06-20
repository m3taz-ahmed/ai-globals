[WORKFLOW] 09-discovery
[OBJ] AI Discovery Workflow for unknown tech stacks.
[RULES]
1. [REQ] Detection: Scan manifests. If tech/version lacks a rule file, pause and trigger discovery. NO ASSUMPTIONS.
2. [REQ] Research: Identify architectural standards, security rules, and performance native optimizations.
3. [REQ] Drafting: Generate `.md` file in `tech-stack/` using strict template. Include `[!TECH-DISCOVERY]`. Define Hard Constraints.
4. [REQ] Integration: Save file, log in `state/CHANGELOG.md`, persist in `state/MEMORY.md`, and validate system integrity.
