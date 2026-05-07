# Phase 8: Project Onboarding & AI Architect Initialization

> [!IMPORTANT]
> **Trigger:** When starting work on a new project or re-initializing the AI agent.
> This protocol ensures the agent correctly loads all global rules, discovers the project's tech stack, and establishes a baseline.

## 1. Initialization Prompt
To onboard an AI agent to a new project using these globals, use:
> "Start immediately by reading the operating protocols from your .ai directory root. Do not rely on any prior assumptions. Operate as the Principal 10x Engineer & Chief Architect."

## 2. Context Loading Sequence
Follow `global-workflow.md` Step 1 (Layered Context Loading):
1. **Layer 0 (Always):** Read `rules/core-behavioral-compact.md` and `global-roles.md`.
2. **Layer 1 (Always):** Read `rules/anti-patterns.md` and `rules/llm-behavioral-guidelines.md`.
3. **Layer 2 (On-Demand):** Load domain rules relevant to the project type.
4. **Layer 3 (Workflow + Tech-Stack):** Detect stack from `composer.json`/`package.json` and load matching tech-stack files.

## 3. Repository Setup
- **Memory:** Create a `MEMORY.md` file in the project root if it doesn't exist. This tracks project-specific decisions and audit history.
- **Git:** Ensure `.gitignore` and `.editorconfig` are present and consistent with global standards (see `rules/git-standards.md` and `.editorconfig`).
- **Tech Stack:** Run a tech-stack scan (`global-workflow.md` Step 1 Layer 3) to align the agent with the project's specific versions.
- **Auto-Discovery:** If a tech version is detected but its rule file is missing from `.ai/tech-stack/`, generate it immediately per `global-roles.md` §3 and log to `CHANGELOG.md`.

## 4. Baseline Audit
Perform a "Mini Deep-Scan" to establish the current state of the codebase:
1. **Architecture Check:** Verify the project follows the established patterns (thin controllers, service layer, proper model scoping).
2. **Security Quick-Scan:** Check for `$guarded = []`, raw SQL, missing auth middleware, and exposed debug mode.
3. **Dependency Health:** Run `composer audit` and `npm audit` to identify known vulnerabilities.
4. **Test Coverage:** Assess current test coverage and identify critical untested paths.
5. **Tech Debt Inventory:** Document immediate architectural red flags in the project's `MEMORY.md`.

## 5. Handoff Summary
After onboarding, report:
- **Stack Detected:** List all frameworks/libraries with versions.
- **Rules Loaded:** Confirm which global rule files were read.
- **Red Flags Found:** Number and severity of baseline audit issues.
- **Recommended Next Steps:** Prioritized action items (critical first).
