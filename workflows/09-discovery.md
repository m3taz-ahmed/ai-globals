# Phase 9: AI Discovery Workflow (v4.9.0)

This protocol governs how the AI handles unknown tech stacks, unreleased versions, or technologies not currently documented in the system's `./tech-stack/`.

## Step 1: Detection
Scan project manifests (`package.json`, `composer.json`, `go.mod`, etc.) for technologies or versions that do not have a corresponding file in `./tech-stack/`.
- **Action:** If a mismatch is found, pause implementation and trigger the discovery protocol.
- **Context Drift Prevention:** Do not assume defaults for unknown versions.

## Step 2: Research
Conduct a high-fidelity research phase into the specific version's architectural standards.
- **Security:** Check for new OWASP recommendations or deprecated security patterns.
- **Performance:** Identify native optimizations (e.g., Next.js 15 `"use cache"`, PHP 8.4 property hooks).
- **Hard Constraints:** Identify non-negotiable patterns required for enterprise-grade stability.

## Step 3: Drafting
Generate a new `.md` file in `./tech-stack/` following the system's strict architectural template.
- **Trigger Header:** Include `[!TECH-DISCOVERY]` and `[!SPECULATIVE]` if the version is in preview.
- **Compliance Gates:** Explicitly map the technology to SOLID, DRY, and OWASP standards.
- **Hard Constraints:** Define the "Laws of the Stack" that the AI must never break.
- **Surgical Patterns:** Include at least three ❌ (Common AI Hallucination) vs ✅ (Sovereign Standard) examples.

## Step 4: Integration
Finalize the discovery by updating the system's memory and integrity manifests.
1. **Save:** Write the file to `./tech-stack/{technology}-{version}.md`.
2. **Log:** Add a surgical entry to `CHANGELOG.md` under the current system version.
3. **Persist:** Update `MEMORY.md` with the newly acquired domain knowledge.
4. **Validate:** Run `scripts/validate-globals.ps1` to verify cross-references and regenerate the `integrity.manifest`.

---

> [!IMPORTANT]
> The Discovery Workflow is a "Self-Expanding" protocol. It ensures the AI Global OS remains at the bleeding edge without manual intervention.
