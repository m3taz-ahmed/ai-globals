[WORKFLOW] git-standards
[OBJ] Version Control & Git Standards.
[RULES]
1. [REQ] Commits `[GIT-01]`: `type(scope): desc`. Atomic commits.
2. [REQ] Branches `[GIT-02]`: `main` (prod), `develop` (staging), `feature/`, `hotfix/`, `release/`.
3. [REQ] PRs `[GIT-03]`: Minimum 1 approval. All CI passes. Max ~400 lines. Protect `main`/`develop`. Tag SemVer releases.
