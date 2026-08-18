# Tasks: {{TITLE}}

**Spec ID**: `{{SPEC_ID}}` | **Phase**: tasks
**Prerequisites**: plan.md (required), spec.md (required)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3...)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase completes

- [ ] T004 Setup database schema and migrations framework
- [ ] T005 [P] Implement authentication/authorization framework
- [ ] T006 [P] Setup API routing and middleware structure
- [ ] T007 Create base models/entities that all stories depend on
- [ ] T008 Configure error handling and logging infrastructure

**Checkpoint**: Foundation ready — user story implementation can begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description]
**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 ⚠️

> **Write tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T011 [P] [US1] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 1

- [ ] T012 [P] [US1] Create [Entity1] model in src/models/[entity1].py
- [ ] T013 [US1] Implement [Service] in src/services/[service].py (depends on T012)
- [ ] T014 [US1] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T015 [US1] Add validation and error handling

**Checkpoint**: User Story 1 fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description]
**Independent Test**: [How to verify]

### Tests for User Story 2

- [ ] T018 [P] [US2] Contract test for [endpoint] in tests/contract/test_[name].py

### Implementation for User Story 2

- [ ] T020 [P] [US2] Create [Entity] model in src/models/[entity].py
- [ ] T021 [US2] Implement [Service] in src/services/[service].py
- [ ] T022 [US2] Implement [endpoint/feature] in src/[location]/[file].py

**Checkpoint**: User Stories 1 AND 2 work independently

---

[Add more user story phases as needed]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories

- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX Security hardening
- [ ] TXXX Run quickstart.md validation (see quickstart-template.md)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational — proceed in parallel or P1→P2→P3
- **Polish (Final)**: Depends on all desired user stories complete

### Parallel Opportunities

- All Setup tasks marked [P] run in parallel
- All Foundational tasks marked [P] run in parallel
- Once Foundational completes, all user stories start in parallel
- Different user stories worked on by different team members

<!--
  aiZee TEST GATES [TEST-07]:
  - FAST tier during iteration: targeted tests only (~5s)
  - FULL tier before done: complete suite + coverage
  - Tests written FIRST, fail before implementation
  - Mark slow tests with framework skip mechanism
-->
