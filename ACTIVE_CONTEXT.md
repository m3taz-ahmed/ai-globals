# aiZee — Active Context / Handoff

**Repo:** `ai-globals` (branch `main`) — version 6.4.0
**Last checkpoint:** 2026-10-15 — Second maintenance cycle DONE + external-research integration pass (ECC/agent-reach/auth-for-laravel).
**Next:** commit (pending user approval), then `update_aizee.bat` sync to deployment mirror.
**Gates (maintenance cycle):** all green — ruff ✓, mypy 599 files ✓, `aizee test --full` 7060 passed / 3 env-skips / 100% cov ✓, `eval/harness.py` all_pass=true ✓, `validate-globals` 0 errors ✓.
**Gates (research pass):** ruff ✓, mypy (touched files) ✓, focused pytest ✓ — FULL suite + harness pending.

## External-research integration (this session)

Selective adoption from `affaan-m/ecc`, `Panniantong/agent-reach`,
`roundly-consulting/auth-for-laravel` — ideas only, no vendored code:

- **`security mcp` deepened** — secrets in `args`, more token prefixes
  (`github_pat_`, `xox*`, `AIza`, `pk_live`…), unpinned pkg + writable-path
  detectors, no duplicate flag/value findings.
- **Prompt-defense baseline** — every emitted harness rules file now
  carries a fixed anti-injection section (identity lock, secrets,
  untrusted external content, unicode tricks). Not counted in
  `rules_emitted`.
- **`fact_force` guardrail** — recoverable destructive ops (force-push…)
  require explicit facts {target, rollback}; catastrophic commands still
  hard-blocked.
- **Memory handoffs `aizee.handoff.v1`** — `memory handoff/handoffs`;
  scoped vaults (project=`brain/` fail-closed gitignored, user=`~/.aizee`).
- **Instincts `aizee.instinct.v1`** — `instinct-add/-reinforce/instincts`;
  confidence 0.3→0.9, auto-promote project→user at ≥2 projects; via
  `MemoryStore.update_meta` (re-signs row).
- **Docs** — `tech-stack/auth-for-laravel.md`, `docs/INSTALL_CONTRACT.md`
  (agent-readable `aizee.install.v1` boundaries).
- **Rejected** (Ponytail): Plan Canvas/Control Pane UI, GitHub App layer,
  311-skill bulk import, npm dependency.

⚠️ Gotcha found this pass: `--project`/`--root` must point at the working
repo for dev writes — a default `AIZEE_ROOT` aimed at the deployment
mirror routes handoff/store writes into it. Mirror artifact was cleaned.

---

## ✅ Done this cycle (Unreleased)

- **Version drift fixed** — `pyproject.toml`/config fallback → 6.3.0; CHANGELOG `[6.3.0]` section.
- **Manifest lock hardened** — fingerprints now cover `description + inputSchema` (rug-pull via schema drift detected; re-baseline: delete `state/mcp_locks/aizee.json`).
- **`aizee security mcp`** — `McpAuditor` (14 detectors) wired to CLI; JSONC-tolerant config parsing; `--lock` persists rug-pull baselines.
- **Supply-chain stage in `security scan`** — `SupplyChainGuard` runs on .py/.ts/.js/.php/.go/.rs; first-party/alias/sibling-aware (`sys.stdlib_module_names`, import↔dist map, go.mod module, composer psr-4); honors `aizee-scan: ignore[-file]` markers; also surfaced pre-write via `lint_python` advisory (`scan_source`).
- **MCP tool annotations** — 31 tools carry `readOnlyHint`/`idempotentHint`/`destructiveHint` via `_annotate_tools()` post-registration.
- **22 orphan runtime modules deleted** (129→107 canonical) — `budget_escalation`/`service_catalog` were mislabeled (real callers) and stay; `ORPHAN_MODULES` now empty; `manifest.json` module map cleaned.
- **Scanner dedup** — same (rule,file,line) collapsed; bandit/ruff same-line sinks report once.
- **Deps refreshed within pins** — mcp 2.3.0, pydantic 2.14.1, cryptography 50.0.2, turbovec 1.1.2, graphifyy 0.9.91, ruff 0.17.1, mypy 2.4.0.
- Counts: runtime 107 / skills 140 / numbered wf 63 / stack 265 / tests ~7.0k.

### Gate status
- ruff ✅ mypy (599 files, strict) ✅ targeted pytest ✅ security scan PASS (0 blockers, 6 honest mediums) ✅
- Pending: FULL suite + `python eval/harness.py` before declaring done.

---

## ⚠️ Gotchas
- `aizee` PATH shim hardcodes `AIZEE_ROOT` to the deployment mirror — for working-repo runs use `python aizee_cli.py` or set `AIZEE_ROOT` explicitly.
- Scoped writes (`memory handoff`, `instinct-*`, `add`) resolve the *project* vault from `--project`/`AGENT_PROJECT_ROOT` — when `AIZEE_ROOT` points at the mirror, dev writes land there. Always pass `--root`/`--project` at the working repo for tests.
- Mirror `D:\server\aizee` is read-only; sync via `update_aizee.bat` only.
- validate-globals requires `[RULES]` marker in SKILL bodies; generated-artifact refs go in `IGNORED_FILE_REFS`.
- Never text-rewrite UTF-8 files via PowerShell (BOM/mojibake risk) — use Python.

> هذا الملف هو نقطة التوقف للاستمرار من اللابتوب. لا تبدأ أي مهمة جديدة قبل قراءته.
