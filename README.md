# AI Globals: Centralized Master Architecture & AI Protocols

> The definitive source of truth for AI agents â€” ensuring absolute consistency, performance, and security across all projects.

## Table of Contents

- [Core Directive](#-the-core-directive)
- [Key Features](#-key-features)
- [Repository Structure](#-repository-structure)
- [Configuration](#-configuration)
- [Quick Reference](#-quick-reference)
- [How to Use](#%EF%B8%8F-how-to-use)
- [Contributing](#-contributing-guidelines)
- [Changelog](#-changelog)

## âš ï¸ Important: Configuration

> [!IMPORTANT]
> This repository uses **absolute paths** to ensure AI agents can always find the global rules regardless of the current working directory.
>
> If you are using this repository, you **MUST** update all occurrences of `D:\server\.ai\` to match the actual path on your machine where you cloned this repository.
>
> **Recommended Action:**
> Perform a global "Find and Replace" in your editor:
> - **Find:** `D:\server\.ai\`
> - **Replace with:** `[YOUR_ABSOLUTE_PATH]\` (e.g., `C:\Users\Name\Documents\ai-globals\`)

## ðŸ§  The Core Directive

Every interaction with an AI agent in this ecosystem starts with a single, non-negotiable rule:
**Operate as a "Principal 10x Engineer & Chief Architect" at the highest global standards.**

## ðŸš€ Key Features

### 1. Global Rule Enforcement
All agents are instructed to bypass default assumptions and read their operating protocols directly from this centralized directory. This ensures that every line of code written follows the same elite standards.

### 2. Dynamic Tech-Stack Sync (Global RAG)
The system automatically detects the framework and library versions in any local workspace (`composer.json`, `package.json`) and pulls the matching architectural rules from the `tech-stack/` directory.

### 3. Self-Learning & Auto-Discovery
If a technology is detected that doesn't yet have a rule file, the AI architect will:
- Analyze the latest industry standards (v2024/2025).
- Generate a new, compacted `.md` rule file.
- Save it to the global `tech-stack/` folder for future use.
- Log the event in `CHANGELOG.md`.

### 4. Recursive System Audits
Includes specialized prompts for full-system deep scans, security hardening, and performance optimization.

## ðŸ“‚ Repository Structure

```
D:\server\.ai\
â”œâ”€â”€ rules/                          # Hard constraints & behavioral guidelines
â”‚   â”œâ”€â”€ principal-architect.md      #   AI persona & architectural patterns
â”‚   â”œâ”€â”€ security-standards.md       #   OWASP Top 10 & cyber resilience
â”‚   â”œâ”€â”€ code-quality.md             #   Clean Code, SOLID, naming conventions
â”‚   â”œâ”€â”€ performance-standards.md    #   Query budgets, caching, queues
â”‚   â”œâ”€â”€ git-standards.md            #   Commits, branching, PR requirements
â”‚   â”œâ”€â”€ environment-windows.md      #   OS context, PowerShell, WSL
â”‚   â”œâ”€â”€ anti-patterns.md            #   Negative constraints & forbidden patterns
â”‚   â”œâ”€â”€ api-integration-standards.md#   External API integration resilience
â”‚   â””â”€â”€ observability-standards.md  #   Logging, monitoring, alerting, health checks
â”œâ”€â”€ tech-stack/                     # Version-specific architectural rules
â”‚   â”œâ”€â”€ laravel-{11,12,13}.md       #   Laravel framework standards
â”‚   â”œâ”€â”€ filament-{3,4,5}.md         #   Filament admin panel standards
â”‚   â”œâ”€â”€ php-8-{3,4,5}.md            #   PHP language version standards
â”‚   â”œâ”€â”€ mysql-8-{3,4}.md            #   MySQL database standards
â”‚   â”œâ”€â”€ nodejs-{22,23,24}.md        #   Node.js runtime standards
â”‚   â”œâ”€â”€ tailwind-{3,4,4-1}.md       #   Tailwind CSS standards
â”‚   â”œâ”€â”€ livewire-3.md               #   Livewire component standards
â”‚   â”œâ”€â”€ vite-6.md                   #   Vite build tool standards
â”‚   â”œâ”€â”€ frontend-{modern,ui}.md     #   Frontend & UI standards
â”‚   â””â”€â”€ laravel-boost.md            #   Laravel Boosts package protocol
â”œâ”€â”€ workflows/                      # Standard operating procedures
â”‚   â”œâ”€â”€ 01-planning.md              #   Planning & architecture workflow
â”‚   â”œâ”€â”€ 02-execution.md             #   Execution & development workflow
â”‚   â”œâ”€â”€ 03-debugging.md             #   Debugging & RCA workflow
â”‚   â”œâ”€â”€ 04-deployment.md            #   Deployment & release workflow
â”‚   â””â”€â”€ 05-code-review.md           #   Code review protocol
â”œâ”€â”€ global-roles.md                 # AI identity & core directives
â”œâ”€â”€ global-workflow.md              # Master workflow for all cycles
â”œâ”€â”€ update-me.md                    # System maintenance prompt
â”œâ”€â”€ monthly-maintenance-prompt.md   # Monthly audit protocol
â”œâ”€â”€ MEMORY.md                       # Audit log & architectural decisions
â”œâ”€â”€ CHANGELOG.md                    # Change history
â””â”€â”€ README.md                       # This file
```

## âš¡ Quick Reference

### Initialize the AI Architect
```
Start immediately by reading the operating protocols from the absolute path
D:\server\.ai\. Do not rely on any prior assumptions. Operate as the
Principal 10x Engineer & Chief Architect.
```

### Monthly Maintenance Audit
```
You are now in Master Architect & Chief Engineer mode. Perform a Full System
Deep-Scan & Global Optimization. Read protocols from D:\server\.ai\ and
execute the maintenance checklist.
```

### Emergency Debugging
```
Act as the Principal Chief Architect. Follow the debugging protocol in
D:\server\.ai\workflows\03-debugging.md. Perform Root Cause Analysis on
the following error: [paste error + code + logs]
```

## ðŸ› ï¸ How to Use

To initialize the AI Architect in any project, use the following prompt command:

> "Start immediately by reading the operating protocols from the absolute path **D:\server\.ai\\**. Do not rely on any prior assumptions. Operate as the Principal 10x Engineer & Chief Architect."

## ðŸ“ Contributing Guidelines

When adding or modifying rule files:
1. **Format:** Use markdown with clear `## Section` hierarchy. Start every file with a `# Title`.
2. **Conciseness:** Rules should be actionable, not theoretical. Each bullet point must be implementable.
3. **Versioning:** Add a `[SPECULATIVE]` header for technologies not yet in general release.
4. **Naming:** Tech-stack files follow `[tech]-[version].md` pattern (e.g., `laravel-12.md`).
5. **Changelog:** Log every addition/modification in `CHANGELOG.md`.
6. **Line Endings:** All files MUST use LF line endings (not CRLF).

## ðŸ“‹ Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full change history.

---
*Created and maintained by [m3taz-ahmed](https://github.com/m3taz-ahmed).*
