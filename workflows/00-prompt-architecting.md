[WORKFLOW] 00-prompt-architecting
[OBJ] Prompt generation protocol.
[RULES]
1. [REQ] Trigger: User asks for a prompt, or via `/prompt`.
2. [REQ] Extraction: Extract Task, Target Tool, Output Format.
3. [PROHIBIT] Hard Gate: Stop and ask (max 3 questions) if critical dimensions are missing. NO prompt generation until spec is locked.
4. [REQ] Routing: Use `prompt-master-templates.md`. Apply tool-specific rules (e.g. XML for Claude).
5. [REQ] Synthesis: Final prompt MUST be English. Strip API keys. Do not use Tree/Graph of Thought unless requested.
6. [REQ] Audit: Check against `prompt-master-patterns.md`. Ensure no vague verbs or dual-tasks.
7. [REQ] Delivery: Output raw prompt block + strategy sentence + agentic warning if applicable.
