# UNIVERSAL EXECUTION WORKFLOW

Strictly follow this operational rhythm for EVERY user request:

## STEP 1: ROUTE & READ (CONTEXT GATHERING)
Before executing any task, you MUST silently read your foundational knowledge in this exact order:
1. **Base Context:** Read `D:\server\.ai\rules\environment-windows.md`, `D:\server\.ai\rules\security-standards.md`, and `D:\server\.ai\rules\principal-architect.md`.
2. **Workflow Route:** Identify the task type and read the corresponding protocol:
   - Planning/Architecture -> Read `D:\server\.ai\workflows\01-planning.md`.
   - Writing/Modifying Code -> Read `D:\server\.ai\workflows\02-execution.md`.
   - Debugging/Errors -> Read `D:\server\.ai\workflows\03-debugging.md`.

## STEP 2: THINK (THE SCRATCHPAD)
You MUST open a `<scratchpad>` block. Inside it:
1. Analyze the exact requirement.
2. Check for security (OWASP), N+1 queries, and performance bottlenecks.
3. Plan your surgical code edits.
Only after closing `</scratchpad>` can you provide the final response.

## STEP 3: THE GOLDEN RULE (ASK FIRST)
Do NOT generate massive blocks of code blindly. If requirements are ambiguous, or if multiple architectural paths exist, ask clarifying questions first.

## STEP 4: STATE MANAGEMENT
Upon completing a major milestone or fixing a critical bug, automatically update the local project's `MEMORY.md` with a concise summary of accomplishments and architectural decisions.