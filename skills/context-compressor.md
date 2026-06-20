[SKILL] context-compressor
[OBJ] Convert human-readable markdown to Telegraphic Pseudo-Code.
[RULES]
1. [REQ] Trigger: User request or uncompiled file detection.
2. [REQ] Logic Extraction: Analyze core constraints and architecture rules.
3. [REQ] Telegraphic Conversion: Remove grammar, stop words, and conversational prose. Use symbols (`=`, `>`, `&`, `->`) and abbreviations (`Req`, `DB`).
4. [REQ] Output Format: `[CategoryName] RuleName:Condition=Action;`
5. [REQ] Save: Overwrite file directly in its original path.
