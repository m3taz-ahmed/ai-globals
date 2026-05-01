# Node.js 24 LTS Strict Standards
- **TypeScript Native:** Run TypeScript natively without external bundlers (ts-node/esbuild) where supported.
- **Built-in SQLite:** Use the stable `node:sqlite` for fast, local data caching or microservices instead of Redis when appropriate.
- **Module System:** 100% ESM (`import/export`). Zero tolerance for CommonJS (`require`).