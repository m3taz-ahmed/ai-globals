# Phase 6: System Maintenance & Global Optimization

> [!IMPORTANT]
> This protocol is triggered when the user requests a "Full System Deep-Scan", "Maintenance Audit", or "Global Optimization".

## 1. PRE-AUDIT SYNC
- **Rule Compliance:** Reload ALL foundational rules from `D:\server\.ai\rules\*`.
- **Tech Sync:** Analyze `composer.json` and `package.json`. If rule files are missing for detected tech, generate them immediately using v2024/2025 standards.

## 2. RECURSIVE AUDIT PROTOCOL
Navigate through every folder in the workspace and audit against:
- **Clean Code:** SOLID, DRY, KISS, and Naming Conventions.
- **Security Hardening:** OWASP Top 10, XSS/SQLi prevention, and dependency audits.
- **Performance:** N+1 query detection, caching strategies, and asset optimization.
- **Documentation:** PHPDoc, README completeness, and inline comments.

## 3. OPTIMIZATION GATES
For every identified issue:
1. **Low-Risk/Refactor:** Legacy syntax, formatting, or documentation gaps. Update immediately.
2. **Medium-Risk:** Logic restructuring or minor performance bottlenecks. Propose in plan.
3. **High-Risk:** Architectural changes or major performance gaps. Flag to user with Risk Matrix.

## 4. GAP FILLING
Identify and add missing essential files:
- **Workflows:** Are there task types not covered by existing SOPs?
- **Configs:** Are there missing `.editorconfig`, `.gitignore`, or env templates?
- **Tests:** Is there a lack of coverage for critical paths?

## 5. REPORTING & PERSISTENCE
- **MEMORY.md:** Update the audit log with findings, resolutions, and architectural decisions.
- **CHANGELOG.md:** Log any modifications to global protocols or tech-stacks.
- **Handoff:** Summarize the 'World-Class' improvements made and identify remaining debt.
