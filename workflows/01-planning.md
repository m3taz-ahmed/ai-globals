# Phase 1: Planning & Architecture

## 1. ASK FIRST PROTOCOL (THE GOLDEN RULE)
NEVER generate large blocks of code for a new feature without clarifying all dimensions first. If requirements are vague, STOP and ask.

## 2. CONTEXT & CONSTRAINTS MAPPING
Establish the exact operating environment, hardware limits, expected data scale, and deployment targets before designing.

## 3. THE DEVIL'S ADVOCATE
Before settling on an architecture, briefly outline the most modern, resource-efficient alternative. (e.g., "We could use standard Eloquent here, but a raw SQL CTE will be 10x faster for this report").

## 4. RISK ASSESSMENT MATRIX
Before implementation, evaluate:
- **Complexity Risk:** How many systems/files does this change touch? (Low: 1-3, Medium: 4-8, High: 9+)
- **Data Risk:** Does this affect existing data? Could it cause data loss or corruption?
- **Rollback Risk:** Can this change be easily reverted? What's the rollback procedure?
- **Performance Risk:** Will this impact response times, memory usage, or database load?
Flag anything rated HIGH to the user before proceeding.

## 5. DEPENDENCY ANALYSIS
Before adding or upgrading any dependency:
- Run `composer outdated` / `npm outdated` to assess the current dependency landscape.
- Check the new dependency's maintenance status (last commit, open issues, security advisories).
- Evaluate the dependency's transitive dependency tree — avoid packages that pull in heavy, unnecessary sub-dependencies.
- Document the justification for adding any new dependency.

## 6. DATA MODELING & STRESS TESTING
- Ensure the database schema passes a mental stress test.
- Design with relationships, strict constraints (Foreign Keys), and precise indexing.
- Define clear Roles & Permissions upfront.
- Estimate row counts at 1x, 10x, and 100x projected scale. Verify indexes hold at each tier.

## 7. ARCHITECTURAL OUTPUT
Produce an implementation plan, logic flow, and necessary Migration/Schema definitions BEFORE logic coding begins.