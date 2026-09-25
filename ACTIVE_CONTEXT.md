# aiZee — Active Context / Handoff

**Repo:** `ai-globals` (branch `main`) — version 5.15.0 + [Unreleased]
**Last checkpoint:** 2026-09-25 — Task Contract + 7-source external adoption package
**Next:** FULL tier (`aizee test --full` with `AIZEE_ROOT` set to working root), then commit (pending user approval), then `update_aizee.bat` sync to deployment mirror.

---

## ✅ Done this session (Unreleased)

### Task Contract — enforced task lifecycle
- `runtime/task_contract/` package: models / classifier / validation / evidence / enforce / engine.
- `aizee task` CLI: classify, decompose, status, start, verify, complete, block, amend, finish, abandon, scope, context.
- Kernel service `kernel.task_contract`; `runtime/__init__.py` exports.
- `rules/task-contract.md` (TASK-01..06 in vocabulary) + `workflows/61-task-contract.md`.
- `.cursor/hooks.json` injects contract block at prompt time; `afterFileEdit` observes scope.
- `AIZEE_TASK_STRICT=1` = hard scope denials (default: advisory).

### External-source adoption
- `rules/untrusted-content.md` — BrowserSkill injection doctrine.
- `runtime/skill_validator.py` + `aizee skill validate` — 133 skills, 0 errors.
- `runtime/harness_exporter.py` + `aizee skill install --harness X`.
- `runtime/c4_docs.py` + `aizee docs c4` — graphify → C4 markdown.
- `eval/trigger_cases.json` + `tests/test_trigger_routing.py`.
- `AGENT_INSTALL.md`; skills: `aizee-lite`, `project-voice`, `browser-automation`.
- `tech-stack/animejs-4.md`; `workflows/62-localhost-tunnel.md`.
- `skills/prompt-engineer.md` upgraded with prompt-master v1.8 delta.
- `skills/design-research/` — Refero+Mobbin evidence doctrine; `mobbin` MCP registered; install.ps1 alwaysAllow += design tools.
- `aizee_mcp/tools/task_tools.py` — 10 MCP task tools (88→98); kernel `task_contract` annotation; update_aizee.bat += AGENT_INSTALL.md.
- manifest.json +25 triggers; counts: runtime 134 / skills 134 / numbered wf 63 / stack 253 / tests 7429.

### Gate status
- ruff ✅ mypy (new/changed files) ✅ targeted pytest (70 new) ✅ validate-globals 0/0 ✅ sync_docs ✅
- Pending: FULL suite + `python eval/harness.py` before declaring done.

---

## ⚠️ Gotchas
- `aizee` PATH shim hardcodes `AIZEE_ROOT` to the deployment mirror — for working-repo runs use `python aizee_cli.py` or set `AIZEE_ROOT` explicitly.
- Mirror `D:\server\aizee` is read-only; sync via `update_aizee.bat` only.
- validate-globals requires `[RULES]` marker in SKILL bodies; generated-artifact refs go in `IGNORED_FILE_REFS`.
- Never text-rewrite UTF-8 files via PowerShell (BOM/mojibake risk) — use Python.

> هذا الملف هو نقطة التوقف للاستمرار من اللابتوب. لا تبدأ أي مهمة جديدة قبل قراءته.
