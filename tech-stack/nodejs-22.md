# Node.js 22 LTS Standards

## 1. EXECUTION & SCRIPTS
- **Script Runner:** Utilize `node --run` for executing package.json scripts (faster than `npm run`, no npm overhead).
- **Watch Mode:** Use `node --watch` for development instead of `nodemon`. Native, zero-dependency.

## 2. SECURITY & PERMISSIONS
- **Permission Model:** Use `--experimental-permission` flags to lock down file system and network access for secure APIs.
- **Policy Files:** Define security policies via `--experimental-policy` for production deployments to restrict module loading.

## 3. BUILT-IN APIS
- **Native Fetch:** Use the stable global `fetch()` API. Do not install `node-fetch` or `axios` for simple HTTP requests.
- **WebStreams:** Leverage the Web Streams API (`ReadableStream`, `WritableStream`) for efficient data processing pipelines.
- **Structured Clone:** Use `structuredClone()` for deep copying objects instead of `JSON.parse(JSON.stringify())`.

## 4. TESTING
- **Native Test Runner:** Use `node:test` with `node --test` for new projects. Stable and built-in.
- **Assertions:** Use `node:assert/strict` for test assertions. Prefer `assert.deepStrictEqual()` over `assert.deepEqual()`.
- **Mocking:** Use the built-in `mock` from `node:test` for function and timer mocking. No need for `sinon` in most cases.

## 5. MODULE SYSTEM
- **ESM Preferred:** Default to ES Modules (`import/export`). Use CommonJS only for legacy compatibility.
- **Package Type:** Set `"type": "module"` in `package.json` for ESM-first projects.