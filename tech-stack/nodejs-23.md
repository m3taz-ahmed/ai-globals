# Node.js 23 Standards

## 1. TESTING
- **Native Runner:** Strictly use the native `node:test` runner. Do not install Jest or Mocha unless required by legacy modules.
- **Coverage:** Use `node --test --experimental-test-coverage` for built-in coverage reports without external tooling.

## 2. MODULE SYSTEM
- **ESM Default:** `require()` of ES modules is supported (unflagged). However, prefer `import` for new code.
- **Glob Imports:** Use `import.meta.glob` patterns where supported for dynamic module loading.

## 3. NETWORKING
- **WebSocket:** The native `WebSocket` global is stable. Do not install `ws` for client-side WebSocket connections.
- **Fetch Improvements:** `fetch()` supports enhanced redirect handling and streaming responses.

## 4. PERFORMANCE
- **V8 Maglev:** Leverage the Maglev optimizing compiler improvements. Write consistent, monomorphic code for optimal JIT performance.
- **Startup:** Use `--snapshot-blob` for custom startup snapshots to reduce cold start time in serverless deployments.