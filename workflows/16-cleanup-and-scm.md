[WORKFLOW] 16-cleanup-and-scm
[OBJ] Remove temporary and scratch files, review source control, and stage only relevant changes. No commits or pushes.
[TRIGGER] cleanup
[TRIGGERS]
- end of task
- end of session
- pre-handoff
[RULES]
1. [REQ] Delete: Remove any temporary, scratch, test-only, or one-off files created during the session (e.g., `tmp/`, `scratch/`, `test_*.py` harness scripts, `*.log`, `.coverage` unless intentionally kept).
2. [CMD] Status: Run `git status --short` and review the output.
3. [REQ] Prune: Remove untracked files that are no longer needed. If a file's purpose has ended, delete it.
4. [REQ] Stage: Stage only files you intentionally modified in this session using `git add <file>`. Never `git add .` or `git add -A`.
5. [PROHIBIT] Never `git commit` or `git push` without explicit user approval. These are user-only actions.
6. [CMD] Report: Summarize the final `git status` and any files that were cleaned or staged.
