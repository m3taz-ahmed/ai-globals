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
> This lazy-loading pattern is what allows 60+ tech-stack files to coexist without overwhelming the AI's context window on any single task.

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
| `postgresql-19.md` | 🔮 Speculative — Beta 3, GA expected Sep/Oct 2026 |
| `swift-6-4.md` | 🔮 Speculative — Beta, WWDC 2026 |

## Formerly Speculative — Now Stable (2026)

These files were previously marked speculative but are now stable releases:

| File | Stable Since | Latest Version |
|---|---|---|
| `php-8-5.md` | Nov 20, 2025 | 8.5.10 (Aug 2026) |
| `laravel-13.md` | Mar 17, 2026 | 13.30.1 (Sep 2026) |
| `filament-5.md` | Jan 16, 2026 | 5.7.8 (Sep 2026) |
| `mysql-9-7.md` | Apr 21, 2026 | 9.7.3 (Aug 2026) LTS |
| `typescript-6.md` | Mar 23, 2026 | 6.0.3 |
| `typescript-7.md` | Jul 2026 | 7.0.2 (Aug 2026) |
| `nestjs-12.md` | Aug 27, 2026 | 12.0.0 |
| `tailwind-4-3.md` | Jul 2026 | 4.3.3 |
| `pest-5.md` | Jul 28, 2026 | 5.1.3 |
| `livewire-4.md` | Jan 14, 2026 | 4.4.3 |
| `go-1-27.md` | Aug 2026 | 1.27.0 |
| `kubernetes-1-36.md` | Apr 22, 2026 | 1.36.4 |
| `django-6.md` | Dec 3, 2025 | 6.1.1 (Sep 2026) |
| `helm-4.md` | 2026 | 4.2.4 |
| `argocd-3.md` | Aug 2026 | 3.5.2 |
| `flutter-3-47.md` | Aug 2026 | 3.47.1 |
| `kotlin-2-4-20.md` | Sep 2026 | 2.4.20 |
| `redis-8-10.md` | Jul 2026 | 8.10.1 |
| `laravel-ai-sdk.md` | Aug 2026 | 0.11.0 |

## Current Coverage (252 files)

| Category | Files |
|---|---|
| **PHP / Laravel** | `php-8-3.md`, `php-8-4.md`, `php-8-5.md`, `laravel-11.md`, `laravel-12.md`, `laravel-13.md`, `laravel-boost.md`, `laravel-octane.md`, `laravel-horizon.md`, `laravel-reverb.md`, `laravel-ai-sdk.md`, `livewire-4.md`, `pest-5.md` |
| **Admin / UI** | `filament-3.md`, `filament-4.md`, `filament-5.md`, `filament-shield.md`, `livewire-3.md`, `alpine-3.md`, `shadcn-ui.md` |
| **Frontend** | `react-ecosystem.md`, `frontend-modern.md`, `frontend-ui.md`, `frontend-design.md`, `frontend-state-standards.md`, `tailwind-3.md`, `tailwind-4.md`, `tailwind-4-1.md`, `tailwind-4-3.md`, `vite-6.md`, `vite-7.md`, `vite-8.md`, `postcss-8.md`, `nextjs-15.md`, `typescript-5.md`, `typescript-6.md`, `typescript-7.md`, `framer-motion.md`, `zustand-state.md`, `tanstack-query.md`, `zod-validation.md`, `openui-generative.md`, `nestjs-12.md`, `nuxt-4.md`, `svelte-5.md`, `angular-22.md` |
| **Database** | `mysql-8-3.md`, `mysql-8-4.md`, `mysql-9-7.md`, `postgresql-17.md`, `postgresql-18.md`, `postgresql-19.md`, `redis-7.md`, `redis-8.md`, `redis-8-10.md`, `clickhouse-analytics.md`, `meilisearch.md`, `qdrant-rag.md`, `database-scaling.md` |
| **Node.js** | `nodejs-22.md`, `nodejs-23.md`, `nodejs-24.md`, `nodejs-26.md` |
| **Mobile** | `flutter.md`, `flutter-3-47.md`, `expo-sdk-57.md`, `kotlin-2-4.md`, `kotlin-2-4-20.md`, `swift-6-3.md`, `swift-6-4.md` |
| **Systems** | `go-1-26.md`, `go-1-27.md`, `rust-1-98.md`, `python-3-14.md` |
| **AI/ML** | `transformers.md`, `langgraph-1.md`, `openai-agents-sdk.md`, `google-adk.md` |
| **Backend** | `django-6.md`, `fastapi.md`, `flask.md` |
| **Cloud/DevOps** | `kubernetes-1-36.md`, `helm-4.md`, `argocd-3.md`, `docker-29.md`, `terraform-iac.md` |
| **Auth / Security** | `clerk-auth.md` |
| **Payments** | `stripe-integration.md` |
| **Infrastructure** | `aws-infrastructure.md`, `docker-containers.md`, `cloudflare-edge.md`, `github-actions-ci.md`, `environment-windows.md` |
| **Observability** | `sentry-tracking.md` |
| **Testing** | `pest-4.md` |
| **Spatie** | `spatie-permission.md`, `spatie-activitylog.md` |
| **SaaS** | `saas-tenancy.md`, `saas-billing.md`, `saas-standards.md` |
| **Design / UX** | `design-foundations.md`, `responsive-ui.md`, `accessibility-standards.md`, `bilingual-mastery.md`, `ui-ux-enforcement.md` |
| **API / Standards** | `api-design-standards.md`, `api-integration-standards.md`, `caching-standards.md` |
| **AI / Vector** | `turbovec-standards.md` |

## Adding a New Tech-Stack File

See [CONTRIBUTING.md](../CONTRIBUTING.md#adding-a-tech-stack-rule-file-tech-stack) for the detailed process and required file structure.
