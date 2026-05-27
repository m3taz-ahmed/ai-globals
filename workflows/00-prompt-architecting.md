# Phase 0: Prompt Architecting (Trigger: Proactively whenever the user asks for a prompt, or explicitly via /prompt)

## 1. INTENT EXTRACTION
- **Action:** Immediately halt code generation or architectural planning.
- **Goal:** Analyze the user's brief input to extract the following 9 dimensions before writing any prompt.
- **Critical Dimensions:**
  - **Task**: Specific action — convert vague verbs to precise operations.
  - **Target tool**: Which AI system receives this prompt (e.g., Cursor, Claude Code, Midjourney, generic LLM).
  - **Output format**: Shape, length, structure, filetype of the result.
- **Conditional Dimensions:**
  - **Constraints**: What MUST and MUST NOT happen, scope boundaries.
  - **Input**: What the user is providing alongside the prompt.
  - **Context**: Domain, project state, prior decisions from this session.
  - **Audience**: Who reads the output, their technical level.
  - **Success criteria**: How to know the prompt worked — binary where possible.
  - **Examples**: Desired input/output pairs for pattern lock.

## 2. ACTIVE DISCOVERY (THE INTERROGATION LAYER)
- **Action:** If any critical dimension is missing or ambiguous, ask a maximum of 3 targeted questions to narrow down the requirements. This acts as a strict "Spec Teasing" quality gate.
- **Rule:** You MUST NOT generate the prompt if critical dimensions (Task, Target Tool, Output Format) are unconfirmed. Stop and ask the user to lock in the specification first. Do NOT ask more than 3 clarifying questions before producing a prompt.

## 3. TOOL ROUTING & TEMPLATE SELECTION
- **Action:** Identify the target AI tool and apply the appropriate template and constraints.
- **Reference:** Use `d:\server\.ai\rules\prompt-master-templates.md` to select the right template (e.g., Template A to M) and apply tool-specific best practices (e.g., strict XML for Claude, no Chain of Thought for o3/o4-mini/R1, specific parameters for Midjourney, explicit file scope and stop conditions for Agentic tools).

## 4. PROMPT SYNTHESIS & SAFE TECHNIQUES
- **Action:** Construct the Master Prompt.
- **Language Rule:** The final Master Prompt MUST be delivered in **English**, regardless of the language used during the discovery phase.
- **Techniques to Apply:**
  - Use Role assignment for specialized tasks.
  - Use Few-shot examples if format is hard to describe.
  - Include a Memory Block if the user references prior session history.
- **Techniques to Avoid (Fabrication Risk):** Do not use Mixture of Experts, Tree of Thought, Graph of Thought, or long prompt chains in a single prompt unless explicitly requested.
- **Credential Safety:** Strip all API keys, secrets, or auth credentials. Replace with "assumes [service] is authenticated".

## 5. DIAGNOSTIC AUDIT
- **Action:** Before delivering, scan the prompt against `d:\server\.ai\rules\prompt-master-patterns.md`.
- **Check:** Ensure there are no vague verbs, two tasks in one prompt, missing success criteria, missing output formats, or over-permissive agent instructions. Validate that the prompt explicitly forces "Spec Teasing" and chunked outputs for complex tasks.
- **Audit:** Ensure every word is load-bearing and token-efficient.

## 6. DELIVERY & APPROVAL
- **Action:** Deliver the output in this strict format:
  1. A single copyable prompt block ready to paste into the target tool.
  2. `🎯 Target: [tool name] · 💡 Strategy: [One sentence explaining what was optimized and why]`
  3. Short plain-English instruction note below ONLY if setup steps are needed (e.g., "Attach your reference image first").
- **Agentic Warning:** If targeting an agentic tool (Claude Code, Cursor, Devin, etc.), append: "This prompt is for an agentic tool with real system access. Review the scope locks, forbidden actions, and stop conditions before pasting."
