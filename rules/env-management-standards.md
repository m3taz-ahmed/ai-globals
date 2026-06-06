# Environment Management Standards (`.env` Synchronization)

This standard defines how the AI agent must handle environment variables across multiple deployment stages, particularly for Laravel projects or any framework relying on `.env` files.

## Core Directives

### 1. Mandatory Files & Git Tracking
Every project MUST maintain the following environment file structure:
- `.env.example` (Tracked in Git) -> The single source of truth for all required keys. Contains dummy or placeholder values.
- `.env` (Ignored) -> The local development environment.
- `.env.staging` (Ignored) -> The staging environment.
- `.env.production` (Ignored) -> The production environment.

**Rule**: The AI MUST actively ensure that `.env`, `.env.staging`, and `.env.production` are present in `.gitignore`. NEVER commit these files.

### 2. The Auto-Sync Protocol
When the AI (or user) adds, removes, or modifies an environment variable **Key** in any `.env` file, the AI MUST execute the following synchronization protocol immediately:

- **Key Addition**: If a new key is added (e.g., `NEW_API_KEY=123`), the AI MUST add `NEW_API_KEY=` to `.env.example`, `.env.staging`, and `.env.production`.
- **Key Deletion**: If a key is deprecated and removed, it MUST be removed from all `.env*` files.
- **Values**: Values are strictly environment-specific. Do NOT copy the value of `NEW_API_KEY` from local to staging/production unless explicitly instructed. Leave it blank or provide a safe default.

### 3. Anti-Patterns
❌ **BAD**: Adding `STRIPE_KEY=sk_test_123` to `.env` and forgetting to update `.env.example` and the other environments, causing the app to crash in staging due to missing variables.
✅ **GOOD**: Adding `STRIPE_KEY=sk_test_123` to `.env`, then immediately adding `STRIPE_KEY=` to `.env.staging`, `.env.production`, and `.env.example`.

### 4. Application
This rule applies universally to all web projects but is specifically triggered when interacting with Laravel, Next.js, or Node.js applications that use `.env` files. Whenever you modify an `.env` file, remember to run this sync routine as part of your core workflow.

### 5. Automation (Git Hook)
To ensure this sync happens automatically even when users edit files manually, the project MUST utilize the global AI sync script.
To install it in any project, create `.git/hooks/pre-commit` in the project with the following content:
```sh
#!/bin/sh
php "D:/server/.ai/scripts/sync-env.php" "$PWD"
```
This guarantees keys are synced locally and `.env.example` is staged automatically before every commit.
