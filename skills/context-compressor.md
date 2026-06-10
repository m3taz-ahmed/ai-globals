---
name: context-compressor
description: A specialized AI skill that converts human-readable markdown rules into Telegraphic Pseudo-Code for the min/ shadow DOM.
---

# Context Compressor Skill

**Trigger:** When the user asks you to compress a file, or when the JIT script (`get-uncompiled.ps1`) identifies uncompiled files.

**Instructions:**
1. Read the original markdown file from the source directory.
2. Analyze the core logic, hard constraints, and architecture rules.
3. Convert the English text into highly dense **Telegraphic Pseudo-Code**.
   - Remove all grammar, stop words, markdown formatting, and conversational text.
   - Use symbols like `=`, `>`, `<`, `|`, `&`, `!`, `+`, `->` to represent logic.
   - Use abbreviations (e.g., `Req` for required, `DB` for database).
   - Format example: `[CategoryName] RuleName:Condition=Action;`
4. Save the resulting dense string to the identical relative path inside the `min/` directory, changing the extension to `.min` (e.g., `tech-stack/new.md` -> `min/tech-stack/new.min`).
5. Confirm completion to the user.
