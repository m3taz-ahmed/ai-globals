# `tech-stack/` — Domain-Specific RAG (Retrieval-Augmented Generation)

This directory is the **AI's knowledge base** for specific frameworks, libraries, and tools. Each file is a compact, expert-level rule set for one technology version.

## How It Works

The AI agent **lazily loads** only the files matching the detected project stack:

```
Project scan: composer.json → "laravel/framework": "^12.0"
               package.json  → "react": "^19.0"

Files loaded:  tech-stack/laravel-12.md
               tech-stack/react-ecosystem.md
               
Files skipped: Everything else (not wasting context window)
```

> [!NOTE]
> This lazy-loading pattern is what allows 37+ tech-stack files to coexist without overwhelming the AI's context window on any single task.

## Naming Convention

```
{technology}-{major-version}.md

Examples:
  laravel-12.md
  php-8-4.md
  react-ecosystem.md    (ecosystem file — covers React, Next.js, Vite)
  tailwind-4-1.md       (minor version when breaking changes exist)
```

## Speculative Files

Files for **unreleased or preview versions** are marked with `[!SPECULATIVE]` at the top and should only be loaded when explicitly working with pre-release software:

| File | Status |
|---|---|
| `laravel-13.md` | 🔮 Speculative — skip by default |
| `php-8-5.md` | 🔮 Speculative — skip by default |
| `filament-5.md` | 🔮 Speculative — skip by default |
| `mysql-9-7.md` | 🔮 Speculative — skip by default |

## Current Coverage (37 files)

| Category | Files |
|---|---|
| **PHP / Laravel** | `php-8-3.md`, `php-8-4.md`, `php-8-5.md`, `laravel-11.md`, `laravel-12.md`, `laravel-13.md`, `laravel-boost.md` |
| **Admin / UI** | `filament-3.md`, `filament-4.md`, `filament-5.md`, `filament-shield.md`, `livewire-3.md`, `alpine-3.md` |
| **Frontend** | `react-ecosystem.md`, `frontend-modern.md`, `frontend-ui.md`, `tailwind-3.md`, `tailwind-4.md`, `tailwind-4-1.md`, `vite-6.md`, `vite-7.md`, `postcss-8.md` |
| **Database** | `mysql-8-3.md`, `mysql-8-4.md`, `mysql-9-7.md` |
| **Node.js** | `nodejs-22.md`, `nodejs-23.md`, `nodejs-24.md` |
| **Testing** | `pest-4.md` |
| **Spatie** | `spatie-permission.md`, `spatie-activitylog.md` |
| **SaaS** | `saas-tenancy.md`, `saas-billing.md` |
| **Design** | `design-foundations.md`, `responsive-ui.md`, `accessibility-standards.md`, `bilingual-mastery.md` |

## Adding a New Tech-Stack File

See [CONTRIBUTING.md](../CONTRIBUTING.md#adding-a-tech-stack-rule-file-tech-stack) for the detailed process and required file structure.
