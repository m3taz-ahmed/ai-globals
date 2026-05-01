# Phase 1: Planning & Architecture

1. **Ask First Protocol (The Golden Rule):** NEVER generate large blocks of code for a new feature without clarifying all dimensions first. If requirements are vague, STOP and ask.
2. **Context & Constraints Mapping:** Establish the exact operating environment, hardware limits, expected data scale, and deployment targets before designing.
3. **The Devil's Advocate:** Before settling on an architecture, briefly outline the most modern, resource-efficient alternative. (e.g., "We could use standard Eloquent here, but a raw SQL CTE will be 10x faster for this report").
4. **Data Modeling & Stress Testing:** 
   - Ensure the database schema passes a mental stress test.
   - Design with relationships, strict constraints (Foreign Keys), and precise indexing.
   - Define clear Roles & Permissions upfront.
5. **Architectural Output:** Produce an implementation plan, logic flow, and necessary Migration/Schema definitions BEFORE logic coding begins.