# MEMORY SYNCHRONIZATION WORKFLOW
> [!IMPORTANT]
> **Trigger:** Run this workflow at the end of a session or task (STEP 6 of global-workflow.md).
> **Purpose:** Compress session learnings and maintain continuous context across sessions without bloating the context window.

## STEP 1: READ ACTIVE CONTEXT
- Check if `./.ai/active-context.md` exists in the local project workspace.
- If it does not exist, create it.

## STEP 2: COMPRESS & SUMMARIZE
Analyze the current session's work and compress the following into concise bullet points:
1. **Goal/Task Completed:** What was the primary objective of this session?
2. **Key Decisions & Architecture:** Why did we choose a specific pattern, package, or approach?
3. **Open Issues/Next Steps:** What was left unfinished, or what should the next session focus on?

> [!WARNING]
> Keep the summary highly compressed. Avoid dumping raw code or verbose explanations. Use semantic markdown.

## STEP 3: UPDATE LOCAL CONTEXT
- Prepend the compressed summary to `./.ai/active-context.md` under a new timestamped header (e.g., `## [YYYY-MM-DD HH:MM] - Brief Title`).
- If the file grows beyond 200 lines, move the oldest entries to `./.ai/memory-archive.md` to protect the AI context window.
