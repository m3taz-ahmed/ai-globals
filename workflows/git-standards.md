# Version Control & Git Standards
> [!NOTE]
> Trigger: Commit, branching, or PR prep.

## Commit Messages (Conventional Commits) `[GIT-01]`
- Standard format: `type(scope): description`.
- **Types:** `feat` (new feature), `fix` (bug fix), `refactor` (code structure), `chore` (maintenance), `docs`, `test`, `perf`, `security`.
- Commits must be atomic (one logical change per commit).

## Branching Strategy `[GIT-02]`
- `main` — Production-ready, always deployable.
- `develop` — Integration branch.
- `feature/[id]-[desc]` — e.g. `feature/FS-42-invoice-pdf`.
- `hotfix/[desc]` — Branch from `main`, merge to both `main` & `develop`.
- `release/[version]` — Release prep (freeze features).

## Pull Requests (PR) `[GIT-03]`
- ✓ Minimum 1 approval before merge. All CI checks (tests, lints, analysis) must pass.
- PR size: Max ~400 lines. Split large features.
- Protect `main` & `develop` (no force-push, PR required). Tag releases via SemVer (`v1.2.3`).
