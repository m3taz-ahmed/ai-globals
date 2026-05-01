# Phase 2: Execution & Development

## 1. ITERATIVE DELIVERY
Build and detail one module at a time. Do not attempt to deliver an entire Monolith in one prompt.

## 2. SURGICAL EDITS (DIFF DRIVEN)
When modifying files, apply incremental diffs. Do NOT rewrite the entire file unless explicitly requested. Show exactly where code is added/removed.

## 3. DESIGN PATTERNS
Favor Service Classes for business logic, Form Requests for validation, and Repositories/Actions where applicable to keep Controllers thin.

## 4. INLINE DOCUMENTATION
Complex logic MUST include concise, professional inline comments to aid future integration and maintenance. Document the "Why" in the comments.

## 5. TEST-ALONGSIDE WORKFLOW
- Write tests concurrently with implementation, not as an afterthought.
- For each feature, deliver: Migration → Model → Service → Controller → Test.
- Run the test suite after every logical unit is complete. Fix failures before proceeding.

## 6. CODE REVIEW SELF-CHECK
Before delivering code, verify against this checklist:
- [ ] **Types:** All parameters and return types are explicitly declared.
- [ ] **Validation:** All inputs are validated via FormRequest or equivalent.
- [ ] **Security:** No raw queries, no mass assignment vulnerabilities, no exposed secrets.
- [ ] **Performance:** No N+1 queries, eager loading applied, no unnecessary loops.
- [ ] **Error Handling:** Proper try/catch, custom exceptions, no silent failures.
- [ ] **Tests:** Unit/Feature tests exist for the new code.
- [ ] **Documentation:** Inline comments explain "why", not "what".

## 7. CHECKPOINTING
After completing a milestone, pause. Output a brief summary of what was achieved and await approval before moving to the next task.