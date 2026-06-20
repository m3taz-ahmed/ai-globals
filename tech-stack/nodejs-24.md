[TECH] nodejs-24
[OBJ] Node.js 24 LTS Strict Standards.
[RULES]
1. [REQ] TS/ESM: `node --experimental-strip-types` (NO `ts-node`/`tsx`). 100% ESM. `Temporal` API > `Date`. `"target": "ES2024"`.
2. [REQ] SQLite: `node:sqlite` for local caching/fixtures. `journal_mode = WAL`. ⛔ NO prod multi-user DB.
3. [REQ] Security: OpenSSL 3.5. `--allow-fs-read` etc. `URLPattern` > regex.
4. [REQ] Diagnostics: `node:diagnostics_channel`. `node:perf_hooks`.
