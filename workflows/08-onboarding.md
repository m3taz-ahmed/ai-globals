[WORKFLOW] 08-onboarding
[OBJ] Project Onboarding & AI Architect Initialization.
[RULES]
1. [REQ] Fast Path: Read operating protocols from `.ai` root. Do not rely on assumptions. Act as Principal 10x Engineer.
2. [REQ] Context Loading Sequence:
   - Layer 0: `core-behavioral-compact.md`, `global-roles.md`
   - Layer 1: `anti-patterns.md`
   - Layer 2: On-demand (e.g. `security-standards.md`)
   - Layer 3: Task workflow + Detected Tech-Stack
3. [REQ] First Time Setup: Create `state/MEMORY.md`. Verify `.gitignore`. Run Tech-Stack Scan.
4. [REQ] Baseline Audit: Check architecture, security (`guarded=[]`), `composer audit`, test coverage, tech debt.
5. [REQ] Handoff Summary: Output Detected Stack, Rules Loaded, Red Flags, Recommended First Action.
