[SKILL] docs-guard
[OBJ] Verify documentation accuracy against source code.
[RULES]
1. [REQ] Verify Everything: Every referenced function/endpoint/flag MUST exist in code. Do not hallucinate.
2. [REQ] Working Samples: Code samples must have correct signatures.
3. [REQ] Code is Truth: Document actual behavior. If docs conflict with code, flag the code.
4. [PROHIBIT] Unverifiable Claims: No "Fast" or "Production-ready" without repo benchmarks.
5. [REQ] Sync: Function name changes require doc updates.
6. [PROHIBIT] Filler: Delete docstrings that just paraphrase the signature.
7. [REQ] Failure Paths: Document error states, not just happy paths.
