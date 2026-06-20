[TECH] nodejs-22
[OBJ] Node.js 22 LTS Standards.
[RULES]
1. [REQ] Execution: `node --run` (scripts). `node --watch` (dev).
2. [REQ] Security: `--experimental-permission`, `--experimental-policy`.
3. [REQ] APIs: Native `fetch()`. WebStreams. `structuredClone()`.
4. [REQ] Testing: Native runner (`node:test`, `node --test`). `node:assert/strict`. Native `mock`.
5. [REQ] Modules: ESM default (`"type": "module"`).
