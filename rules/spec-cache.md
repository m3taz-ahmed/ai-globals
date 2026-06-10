# AI Context Cache (spec.md)

## Objective
To eliminate hallucinations regarding framework/package versions (e.g., assuming Filament v3 instead of v5) and to conserve context tokens by maintaining an AI-optimized, hidden tech stack manifest.

## Trigger
Execute this rule immediately upon entering ANY project or beginning a new conversation related to a specific project.

## Instructions
1. **Search for Cache:** Check if a file named `spec.md` exists in the root of the active project.
2. **Cache Hit (File Exists):** 
   - Read the contents of `spec.md`.
   - Strictly adhere to the versions specified in this file for all subsequent code generation and advice. Do not default to older versions.
3. **Cache Miss (File Does Not Exist):**
   - Quickly analyze the project's package managers (e.g., read `composer.json`, `package.json`, or equivalent).
   - Create `spec.md` in the project root.
   - The content of `spec.md` MUST be an extremely dense, single-line or minimal-line format optimized solely for AI consumption (No human-friendly formatting or markdown tables).
     *Example Format:* `php:8.2|laravel:11|filament:5|livewire:3|alpine:3|tailwind:3`
   - Immediately append `spec.md` to the project's `.gitignore` file (create `.gitignore` if it doesn't exist) to ensure the AI cache is never committed to version control.
   - Use the newly gathered information for the current session.
