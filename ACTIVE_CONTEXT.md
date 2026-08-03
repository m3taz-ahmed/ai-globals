# AI Global OS — Active Context / Handoff

**Session type:** Stop-and-continue (PC → laptop)  
**Repo:** `https://github.com/m3taz-ahmed/ai-globals.git` (branch `main`)  
**Last checkpoint:** P0.4 ✅ + P0.3 ✅ + P0.2 ✅ + P0.1 ✅  
**Next:** UI/UX research done; ready for next milestone.

---

## ✅ تم الانتهاء منه (Completed)

### P0.4 — Approval Caching + Rollout Budget
- `runtime/approval_cache.py`: كاش جديد للموافقات بناءً على مفتاح SHA-256.
- `runtime/budget.py`: إضافة `rollout_max_tokens`, `rollout_reminder_threshold`, `token_weight_input/output`, و `threading.RLock` لأمان الترابط.
- `runtime/kernel.py`: ربط كاش الموافقات وفحوصات الميزانية.
- `runtime/schemas.py`: إضافة حقول الميزانية.
- `runtime/tests/test_budget.py`, `runtime/tests/test_kernel.py`: تحديث الاختبارات.

### P0.3 — Hybrid Memory Scoring
- `memory/hybrid.py`: محرك بحث هجين يجمع `FTS5` + vector similarity + entity boosting.
- `memory/store.py`: طريقة `search_hybrid(...)` مع fallback إلى `search` عند غيوب الفهرس المتجه.
- `cli.py`: أمر `query` يستخدم `search_hybrid` مع `--explain`.
- `memory/tests/test_hybrid.py`: اختبارات تغطي الفرز والكيانات والـ fallback.

**الفحوصات تمر:**
```
ruff check .        ✅
mypy memory runtime ✅
pytest memory/tests runtime/tests -q  ✅ 217 passed
```

---

## ✅ تم الانتهاء منه (Completed)

### P0.2 — Conditional Rules with YAML Frontmatter
- `runtime/rule_frontmatter.py`: integrated into `SkillResolver`/`PersonaDetector`/`aios_mcp`.
  - `SkillResolver`: `resolve_with_frontmatter`, `load_with_frontmatter`, `list_active_skills`.
  - `PersonaDetector`: filters primary/lord skill lists by context.
  - `aios_mcp/aios_server.py::query_rules`: accepts `context` and returns active rules.
  - Tests added in `runtime/tests/test_rule_frontmatter.py` (34 tests).
- Quality gates green: `ruff`, `mypy`, `pytest -q` 349 passed, `python eval/harness.py` all_pass true.
- `graphify update .` and `ai-os memory ingest` run.

### P0.1 — Fresh-Context Boundary in `runtime/kernel.py`
- Implemented `fresh_context` parameter in `Kernel.act`, `run_workflow`, `chat_message`, `run_saga`.
- Resets per-session budget via explicit `session_id` in `BudgetManager`.
- Deep-copies and re-derives auto-injected persona/skill/lord keys in workflow/saga contexts.
- Tests added in `runtime/tests/test_kernel.py`.
- Quality gates green.

### UI/UX/Responsive Design Repo Research
- Updated `tech-stack/useful-repos.md` with verified top repositories:
  - `saadeghi/daisyui`, `shadcn-ui/ui`, `carbon-design-system/carbon`, `DouyinFE/semi-design`, `facebook/astryx`.
- `graphify update .` and `ai-os memory ingest` re-run; `python eval/harness.py` all_pass true.

## 🚧 قيد التنفيذ (In Progress)
- No active in-progress task. Ready for next milestone.

---

## 📁 ملفات تم تعديلها / إنشاؤها في هذه الجلسة

### تم تعديلها (Modified)
- `cli.py`
- `memory/store.py`
- `runtime/budget.py`
- `runtime/kernel.py`
- `runtime/schemas.py`
- `runtime/tests/test_budget.py`
- `runtime/tests/test_kernel.py`

### جديدة (Added)
- `memory/hybrid.py`
- `memory/tests/test_hybrid.py`
- `runtime/approval_cache.py`
- `runtime/rule_frontmatter.py`
- `ACTIVE_CONTEXT.md` (هذا الملف)

---

## 🚀 Prompt للاستمرار (انسخه في الجلسة الجديدة)

```
You are continuing AI Global OS implementation from a handoff.

COMPLETED:
- P0.4 Approval Caching + Rollout Budget in runtime/*
- P0.3 Hybrid Memory Scoring in memory/* + cli.py

CURRENT TASK (start here):
- P0.2 Conditional Rules with YAML Frontmatter:
  1. Integrate runtime/rule_frontmatter.py into runtime/skill_resolver.py
     (load_with_frontmatter, list_active_skills, resolve_with_frontmatter).
  2. Filter skill lists in runtime/persona.py using the context.
  3. Update aios_mcp/aios_server.py::query_rules to accept context and return only active rules.
  4. Add tests in runtime/tests/test_rule_frontmatter.py.

NEXT AFTER P0.2:
- P0.1 Fresh-Context Boundary in runtime/kernel.py.
- Run graphify update . and ai-os memory ingest.
- Research top UI/UX/Responsive Design GitHub repos.

GATES:
Run ruff check ., mypy memory runtime, and python -m pytest memory/tests runtime/tests -q before committing.
Start by reading ACTIVE_CONTEXT.md and runtime/rule_frontmatter.py.
```

---

> هذا الملف هو نقطة التوقف للاستمرار من اللابتوب. لا تبدأ أي مهمة جديدة قبل قراءته.
