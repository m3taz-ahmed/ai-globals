# Phase 0: Prompt Architecting (Trigger: /prompt)

## 1. INTENT ANALYSIS
- **Action:** Immediately halt any code generation or architectural planning.
- **Goal:** Analyze the user's brief input to identify the "Core Objective".
- **Rule:** If the input is ambiguous or underspecified, transition to **Active Discovery**.

## 2. ACTIVE DISCOVERY (THE INTERROGATION LAYER)
- **Action:** Generate a maximum of 5 targeted questions to narrow down the requirements.
- **Focus Areas:**
    - **Domain Context:** (e.g., Target audience, industry, or specific use case).
    - **Data & Entities:** Key data points, relationships, or necessary inputs/outputs.
    - **Constraints:** Specific rules, limitations, or "No-Go" zones (e.g., "Must run on low-end hardware", "No external APIs").
    - **Tone & Style:** Desired persona or output format for the final prompt.

## 3. PROMPT SYNTHESIS (THE MASTER PROMPT)
- **Action:** Once the requirements are clear, construct the "Master Prompt".
- **Language Rule:** The final Master Prompt MUST be delivered in **English**, regardless of the language used during the discovery phase.
- **Structure of Master Prompt:**
    - **Role:** High-level persona (e.g., Principal Architect, Senior DevOps, Expert Copywriter).
    - **Context:** Detailed background gathered during discovery.
    - **Objectives:** Clearly defined goals for the AI.
    - **Technical Stack/Constraints:** Explicit mention of technologies and limitations.
    - **Output Format:** Precise definition of what the successful output looks like.

## 4. TRANSITION & APPROVAL
- **Action:** Present the Master Prompt to the user and ask: 
    - "Should I proceed with Phase 1 (Architecture & Planning) using this Master Prompt?"
    - "Or would you like to copy this prompt for use elsewhere?"
