[TECH] nodejs-23
[OBJ] Node.js 23 Standards.
[RULES]
1. [REQ] Testing: Strictly use native `node:test`. Built-in coverage (`--experimental-test-coverage`).
2. [REQ] Modules: `import` preferred. `import.meta.glob` for dynamic. (`require(esm)` supported).
3. [REQ] Networking: Native `WebSocket` global.
4. [REQ] Performance: V8 Maglev (write monomorphic code). `--snapshot-blob` for fast startups.
