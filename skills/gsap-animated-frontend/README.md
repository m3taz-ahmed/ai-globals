# GSAP Animated Frontend

<p align="center">
  <img src="https://raw.githubusercontent.com/yousefabdallah171/gsap-animated-frontend/main/assets/gsap-skill-banner.svg" alt="GSAP Animated Frontend" width="800" />
</p>

<p align="center">
  <b>A persistent, recoverable GSAP workflow for coding agents.</b><br/>
  <sub>Two user-facing commands. Internal helpers. Persistent phased artifacts as the source of truth.</sub>
</p>

---

## What This Repo Is

This repo is a GSAP animation skill/workflow package designed to work across coding agents, not only one model.

It is built to work well with:

- Claude Code
- Codex CLI
- Cursor
- Gemini CLI
- any agent that can follow `SKILL.md`-style instructions

The core design goal is simple:

- only **2 user-facing commands**
- persistent workflow state in `.gsap/`
- recoverable progress after interruption
- internal Python helpers for scanning, artifact generation, interview generation, and phased workflow orchestration

---

## The 2 Commands

These are the only primary commands the user should see:

### `gsap-new`

Use for:

- new pages
- new sections
- greenfield animation work

What it does:

1. Creates or updates `.gsap` artifacts
2. Discovers framework, packages, structure, brand signals, and motion opportunities
3. Interviews only when required
4. Generates animation specifications
5. Generates a phased implementation plan
6. Prepares one-section-at-a-time task files

### `gsap-refactor`

Use for:

- existing pages/components
- improving current motion systems
- cleanup, accessibility, and performance hardening

What it does:

1. Reads existing code
2. Reads existing `.gsap` artifacts
3. Audits the current motion system
4. Generates a phased refactor plan
5. Applies safe improvements section by section
6. Updates artifacts

---

## Persistent State

The workflow state lives in the project being animated, not in chat history.

```text
your-project/
└── .gsap/
    ├── animation-spec.md
    ├── animation-plan.md
    ├── audit-report.md
    ├── tasks/
    │   └── homepage.tasks.md
    ├── phases/
    │   └── homepage/
    │       ├── p01-hero.md
    │       └── p02-feature-grid.md
    └── pages/
        ├── homepage.animation.md
        ├── schools.animation.md
        └── dashboard.animation.md
```

This means a fresh agent session can resume by reading `.gsap` files without needing prior conversation context.

---

## Architecture

```text
gsap-animated-frontend/
├── SKILL.md
├── gsap_cli.py
├── requirements.txt
├── scripts/
│   ├── gsap_workflow.py
│   ├── brand_extractor.py
│   ├── structure_search.py
│   ├── interview_generator.py
│   └── phase_planner.py
├── subskills/
│   ├── gsap-new/
│   │   └── SKILL.md
│   └── gsap-refactor/
│       └── SKILL.md
├── templates/
│   ├── animation-spec.md
│   ├── animation-plan.md
│   ├── audit-report.md
│   ├── animation-tasks.md
│   ├── page-animation.md
│   └── phase.md
├── references/
│   ├── animation-recipes.md
│   ├── gsap-core-patterns.md
│   ├── performance-guide.md
│   └── scroll-trigger-patterns.md
└── assets/
    └── gsap-skill-banner.svg
```

### Design Rules

- `SKILL.md` is the root router
- `subskills/gsap-new` and `subskills/gsap-refactor` are the only public workflows
- `scripts/gsap_workflow.py` orchestrates the workflow
- dedicated helper scripts extract brand signals, discover structure, generate interview questions, and build phases
- `templates/` creates persistent `.gsap` state for spec-driven execution
- `references/` holds optional detailed guidance

---

## Internal Helpers

The system may use internal script commands such as:

- artifact bootstrap
- brand extraction
- structure search
- interview question generation
- phase planning
- workflow state updates
- code inspection
- motion audit prep
- refactor plan preparation

These are internal implementation helpers, not part of the intended public UX.

The public UX stays centered on:

- `gsap-new`
- `gsap-refactor`

## Spec-Driven Workflow

This package is now designed to behave more like spec-driven development than a one-shot animation prompt.

The engine should:

1. discover the real project structure and visual language
2. write findings into `.gsap` artifacts
3. generate a phased plan
4. generate per-page task files
5. generate one phase file per section
6. implement one major section at a time

This prevents agents from trying to rebuild an entire page in one pass and usually leads to cleaner motion hierarchy, better reduced-motion coverage, and better final quality.

---

## Installation

Install from your project root with:

```bash
npx skills add yousefabdallah171/gsap-animated-frontend
```

This is the only documented install path for:

- Claude Code
- Codex
- Gemini
- Cursor
- other agents that support repo-scoped `SKILL.md` discovery

After installation, start a new agent session in that project so the skill files are picked up.

---

## Usage

After install, restart your agent session in the project.

Use only these two public workflows:

- `gsap-new`
- `gsap-refactor`

### `gsap-new`

Use for:

- new pages
- new sections
- greenfield animation systems

Workflow behavior:

1. reads existing `.gsap` artifacts if they exist
2. discovers framework, routes, page files, motion stack, and brand signals
3. asks only the missing questions
4. writes `.gsap/animation-spec.md`
5. writes `.gsap/animation-plan.md`
6. writes `.gsap/tasks/<page>.tasks.md`
7. writes `.gsap/phases/<page>/phase-files`
8. moves implementation one section phase at a time

### `gsap-refactor`

Use for:

- existing pages
- existing components
- motion cleanup and upgrades

Workflow behavior:

1. reads current code first
2. reads existing `.gsap` artifacts
3. audits the motion system
4. generates a phased refactor plan
5. updates `.gsap/audit-report.md`
6. writes or refreshes tasks and phase files
7. improves one section phase at a time

### Resulting Project State

```text
your-project/
└── .gsap/
    ├── animation-spec.md
    ├── animation-plan.md
    ├── audit-report.md
    ├── tasks/
    │   └── homepage.tasks.md
    ├── phases/
    │   └── homepage/
    │       ├── p01-hero.md
    │       ├── p02-feature-grid.md
    │       └── p03-stats.md
    └── pages/
        └── homepage.animation.md
```

These files are the workflow memory. A fresh agent session should resume from them instead of relying on chat history.

---

## Philosophy

This repo is optimized around:

- purposeful motion, not random effects
- recoverable workflows, not chat-only memory
- simple UX, not command overload
- cross-agent compatibility, not one-tool lock-in
- persistent artifacts, not fragile context

---

## License

MIT
