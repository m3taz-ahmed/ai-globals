# Feature Specification: {{TITLE}}

**Feature Branch**: `{{FEATURE_BRANCH}}`
**Spec ID**: `{{SPEC_ID}}`
**Created**: {{DATE}}
**Status**: Draft
**Phase**: specify

## User Scenarios & Testing *(mandatory)*

<!--
  User stories PRIORITIZED as user journeys ordered by importance.
  Each story INDEPENDENTLY TESTABLE — implementing ONE yields viable MVP.
  P1 = most critical. Each story = standalone slice: develop/test/deploy/demo independently.
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe user journey in plain language]

**Why this priority**: [Value + priority rationale]

**Independent Test**: [How to test independently — e.g., "Tested by [action], delivers [value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe user journey in plain language]

**Why this priority**: [rationale]

**Independent Test**: [how]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed]

### Edge Cases

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST [specific capability]
- **FR-002**: System MUST [specific capability]
- **FR-003**: Users MUST be able to [key interaction]

*Mark unclear requirements:*

- **FR-00X**: System MUST [NEEDS CLARIFICATION: specific question]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships]

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: [Measurable metric — e.g., "Users complete task in under 2 minutes"]
- **SC-002**: [Measurable metric — e.g., "System handles 1000 concurrent users"]
- **SC-003**: [User satisfaction metric]

## Assumptions

- [Assumption about target users]
- [Assumption about scope boundaries]
- [Assumption about data/environment]
- [Dependency on existing system/service]

<!--
  QUALITY GATES (aiZee):
  - No implementation details (languages, frameworks, APIs)
  - Focused on user value and business needs
  - All mandatory sections completed
  - No [NEEDS CLARIFICATION] markers remain before advancing to Plan
  - Success criteria measurable + technology-agnostic
  - Max 3 [NEEDS CLARIFICATION] markers — prioritize: scope > security > UX > technical
-->
