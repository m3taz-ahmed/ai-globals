# Version Control & Git Standards

## 1. COMMIT MESSAGES (CONVENTIONAL COMMITS)
- Always format commit messages according to Conventional Commits:
  - `feat: [description]` (New feature)
  - `fix: [description]` (Bug fix)
  - `refactor: [description]` (Code change that neither fixes a bug nor adds a feature)
  - `chore: [description]` (Updating build tasks, package manager configs, etc.)
  - `docs: [description]` (Documentation only changes)

## 2. COMMIT SCOPE
- Keep commits atomic. One commit = one logical change.
- The commit description must explain the "Why" if the change is complex, not just the "What".