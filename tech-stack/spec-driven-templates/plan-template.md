# Implementation Plan: {{TITLE}}

**Branch**: `{{FEATURE_BRANCH}}` | **Date**: {{DATE}} | **Spec ID**: `{{SPEC_ID}}`
**Phase**: plan

## Summary

[Extract from feature spec: primary requirement + technical approach]

## Technical Context

**Language/Version**: [e.g., Python 3.11, PHP 8.4 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, Laravel 12 or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, files or N/A]

**Testing**: [e.g., pytest, Pest 4 or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+ or NEEDS CLARIFICATION]

**Project Type**: [library/cli/web-service/mobile-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific or NEEDS CLARIFICATION]

**Constraints**: [domain-specific or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Constitution principles loaded from project — check each MUST principle]

## Project Structure

### Documentation (this feature)

```text
specs/{{SPEC_ID}}/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output (see research-template.md)
├── data-model.md        # Phase 1 output (see data-model-template.md)
├── quickstart.md        # Phase 1 output (see quickstart-template.md)
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: [Document selected structure + real directories]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |

<!--
  aiZee GATES:
  - Read lockfile before declaring stack versions [VER-01]
  - Query Context7 MCP for external libs before implementation
  - Use graphify for codebase exploration
  - Constitution MUST principles = non-negotiable
-->
