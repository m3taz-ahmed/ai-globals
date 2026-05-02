# Version Control & Git Standards

## 1. COMMIT MESSAGES (CONVENTIONAL COMMITS)
- Always format commit messages according to Conventional Commits:
  - `feat: [description]` (New feature)
  - `fix: [description]` (Bug fix)
  - `refactor: [description]` (Code change that neither fixes a bug nor adds a feature)
  - `chore: [description]` (Updating build tasks, package manager configs, etc.)
  - `docs: [description]` (Documentation only changes)
  - `test: [description]` (Adding or updating tests)
  - `perf: [description]` (Performance improvements)
  - `security: [description]` (Security fixes or hardening)

## 2. COMMIT SCOPE
- Keep commits atomic. One commit = one logical change.
- The commit description must explain the "Why" if the change is complex, not just the "What".
- Use scopes for clarity: `feat(booking): add automatic invoice generation`.

## 3. BRANCHING STRATEGY
- **`main`** â€” Production-ready code only. Always deployable.
- **`develop`** â€” Integration branch. All feature branches merge here first.
- **`feature/[ticket-id]-[description]`** â€” New features (e.g., `feature/FS-42-invoice-pdf`).
- **`hotfix/[description]`** â€” Critical production fixes. Branch from `main`, merge to both `main` and `develop`.
- **`release/[version]`** â€” Release preparation. Freeze features, fix bugs, update version numbers.

## 4. PULL REQUEST REQUIREMENTS
- **Minimum 1 approval** before merging to `develop` or `main`.
- **All CI checks must pass** â€” tests, linting, static analysis.
- **PR Description:** Must include: What changed, Why, How to test, and any Breaking Changes.
- **Size Limit:** PRs should not exceed ~400 lines of changes. Split large features into incremental PRs.

## 5. PROTECTED BRANCHES
- **`main`:** Force push disabled. Require PR reviews. Require status checks to pass. Require linear history (squash merge preferred).
- **`develop`:** Force push disabled. Require PR reviews.
- **Tags:** Use semantic versioning (`v1.2.3`) for releases. Annotated tags with release notes.