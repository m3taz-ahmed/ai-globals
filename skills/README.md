# `skills/` — Persona & Lord Skills

This directory contains **80 skills** (38 directory-based `SKILL.md` + 42 flat `.md` = 80 logical skills; `glob skills/**/*.md` returns ~115 files because directory skills have `references/` and `templates/`). Each skill is a compact rule set loaded lazily — only matching skills enter the AI's context window.

## New Skills (2026-08-28) — Imported from Claude Code Ecosystem

| Skill | Type | Persona | Description |
|-------|------|---------|-------------|
| `web-design-guidelines` | flat | UX | 100+ rules from Vercel (a11y, forms, dark mode, typography, animation, images, performance, navigation, touch, i18n) |
| `design-taste` | flat | UX | Design DNA extractor — reverse-engineer any website's design taste via Playwright |
| `image-to-code` | flat | UX | Image-first design-to-code workflow (generate → analyze → implement) |
| `accessibility-auditor` | flat | UX | 11 WCAG 2.2 AA specialist agents |
| `web-quality` | flat | UX | Lighthouse + Core Web Vitals optimization |
| `motion-design` | flat | UX | Animation audit from 3 designer perspectives + severity rankings |
| `backend-design` | flat | DEV | 13 senior backend engineer reflexes |
| `qa-automation` | flat | QA | 6 Playwright QA agents + 5-step workflow |

## How It Works

```
Task description → PersonaDetector → primary persona + secondary personas
                → SkillResolver   → matching skills + lord skills
```

Skills are loaded via `runtime/skill_resolver.py::SkillResolver` which scans both
flat `.md` files and directory-based `SKILL.md` files.

## Skill Formats

### Flat Skills (`skills/<name>.md`)
Single-file skills with YAML frontmatter:
```yaml
---
name: my-skill
description: What this skill does.
triggers: [keyword1, keyword2]
personas: [ARCH, SEC]
---
[SKILL] my-skill
[OBJ] Objective.
[RULES]
1. [REQ] First rule.
```

### Directory Skills (`skills/<name>/SKILL.md`)
Multi-file skills with references and templates:
```
skills/seo-lord/
├── SKILL.md              # Main skill definition
├── references/           # Supporting reference docs
└── templates/            # Output templates
```

## Current Skills (72 total = 38 dir + 34 flat)

| Skill | Type | Domain |
|-------|------|--------|
| accessibility-auditor | flat | UX/A11y |
| agent-governance-lord | dir | Governance |
| ai-agents-architect | flat | Architecture |
| ai-ml-lord | dir | AI/ML |
| api-architect | flat | API design |
| api-versioning | flat | API versioning |
| arabic-dialect-lord | dir | Localization |
| backend-api-expert | flat | Backend |
| backend-frameworks-lord | dir | Backend frameworks |
| brainstorming | flat | Ideation |
| browser-extension-builder | flat | Browser extensions |
| clean-code-guard | flat | Code quality |
| cloud-platforms-lord | dir | Cloud/DevOps |
| code-reviewer | flat | Code review |
| compliance-lord | dir | Legal/compliance |
| content-quality-lord | dir | Content |
| context-compressor | flat | Context management |
| cv-writer | flat | Career |
| data-engineer | flat | Data engineering |
| database-lord | flat | Database design |
| devops-engineer | flat | DevOps |
| devops-lord | dir | DevOps |
| docs-guard | flat | Documentation |
| eval-reliability-lord | dir | Eval/reliability |
| flutter-architect | dir | Flutter architecture |
| flutter-design | flat | Flutter design |
| flutter-developer | flat | Flutter development |
| freelance-platforms | flat | Freelancing |
| frontend-frameworks-lord | dir | Frontend frameworks |
| frontend-ui-expert | flat | Frontend UI |
| fullstack-optimizer | flat | Full-stack |
| game-architect | flat | Game architecture |
| google-play-warlord | dir | Google Play |
| graphify | flat | Knowledge graph |
| gsap-animated-frontend | dir | GSAP animation |
| incident-commander | flat | Incident response |
| language-lord | flat | Programming languages |
| legal-compliance | flat | Legal |
| linkedin-platform | flat | LinkedIn |
| linux-systems-lord | flat | Linux systems |
| mariadb-lord | flat | MariaDB |
| messaging-streaming-lord | dir | Messaging |
| migration-specialist | flat | Migrations |
| ml-engineer | flat | ML engineering |
| mobile-architect | flat | Mobile architecture |
| mobile-game-producer | flat | Mobile games |
| page-sections-lord | dir | Page sections |
| performance-engineer | flat | Performance |
| ponytail | dir | Ponytail framework |
| ponytail-audit | dir | Ponytail audit |
| ponytail-debt | dir | Ponytail debt |
| ponytail-gain | dir | Ponytail gain |
| ponytail-help | dir | Ponytail help |
| ponytail-review | dir | Ponytail review |
| product-manager | flat | Product |
| prompt-engineer | flat | Prompt engineering |
| prompt-master-patterns | dir | Prompt patterns |
| prompt-master-templates | dir | Prompt templates |
| proposal-writer | flat | Proposals |
| qa-debugger | flat | QA/debugging |
| search-vector-lord | dir | Search/vector |
| security-auditor | flat | Security audit |
| security-lord | dir | Security |
| seo-lord | dir | SEO |
| sre | flat | SRE |
| subagent-driven-development | flat | Subagents |
| supply-chain-lord | dir | Supply chain |
| technical-writer | flat | Tech writing |
| test-driven-development | flat | TDD |
| test-guard | flat | Testing |
| wordpress-expert | flat | WordPress |
| writing-plans | flat | Planning |

## Adding a New Skill

1. Create `skills/<name>.md` (flat) or `skills/<name>/SKILL.md` (directory).
2. Add YAML frontmatter with `triggers`, `personas`, `tech_stack`.
3. Register in `PERSONA_SKILLS` mapping in `runtime/persona.py` if persona-linked.
4. Test: `aizee persona detect --multi "<task description>"`.
5. Run `aizee memory ingest` to refresh indexes.
6. Run `python scripts/sync_docs.py` to update count in docs.

> **Note:** `skills/seo-content-generator.md` was removed (superseded by `skills/seo-lord/`).
